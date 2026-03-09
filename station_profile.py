# -*- coding: utf-8 -*-
"""
station_profile.py — Профиль станции и диалоговый сбор параметров

Содержит:
  - STATION_PROFILE_TEMPLATE  — пустой шаблон профиля со всеми полями
  - DIALOG_STEPS              — последовательность вопросов для сбора профиля
  - parse_user_answer()       — разбор ответа пользователя (число / выбор / да/нет)
  - get_next_question()       — следующий вопрос с учётом уже собранных данных
  - is_profile_complete()     — проверка минимальной достаточности для расчёта
  - profile_summary_text()    — текстовое резюме профиля для отображения
"""

from __future__ import annotations
import re
from typing import Optional, Any


# ============================================================
# ШАБЛОН ПРОФИЛЯ СТАНЦИИ
# ============================================================

STATION_PROFILE_TEMPLATE: dict = {
    # — Идентификация —
    "name":          None,   # Название станции
    "category":      None,   # "small" (<25 МВт) | "large" (≥25 МВт)
    "power_mw":      None,   # Установленная мощность, МВт

    # — Топливо и доставка —
    "main_fuel":     None,   # "gas" | "coal" | "mazut" | "peat" | "diesel"
    "delivery_type": None,   # "pipeline" | "gas_pipeline" | "rail" | "road" |
                             # "water" | "conveyor" | "pipeline_refinery"
    "has_pgu_gtu":   False,  # Наличие ПГУ/ГТУ → нужен НАЗТ

    # — Теплотехника (для всех) —
    "Q_nr":          None,   # Теплота сгорания топлива, ккал/кг
    "b_ee":          None,   # Уд. расход условного топлива на э/э, г/кВт·ч
    "b_te":          None,   # Уд. расход условного топлива на теплоэнергию, кг/Гкал

    # — Режим выживания —
    "P_min":         None,   # Минимальная рабочая мощность (≥25 МВт), МВт
    "E_sn_day":      None,   # Расход на СН при минимальной нагрузке, млн кВт·ч/сут
    "Q_ot_min":      None,   # Минимальный отпуск тепла при режиме выживания, Гкал/сут

    # — Максимальные параметры (≥25 МВт) —
    "P_rab":         None,   # Макс. рабочая мощность по Правилам технол. функционирования, МВт
    "E_sn_maks":     None,   # Расход на СН при максимальной нагрузке, млн кВт·ч/сут
    "Q_t_max_5y":    None,   # Макс. среднесуточный отпуск тепла за 5 лет, Гкал/сут

    # — Параметры для малых ТЭС (<25 МВт) —
    "E_vyr_min":     None,   # Выработка э/э при минимальной нагрузке, млн кВт·ч/сут
    "E_sn_min":      None,   # Расход на СН при минимальной нагрузке, млн кВт·ч/сут
    "B_r_sr_jan":    None,   # Среднерасч. суточный расход — январь, т/сут
    "B_r_sr_apr":    None,   # Среднерасч. суточный расход — апрель, т/сут
    "T_psr":         None,   # Среднее время поставки, сут
    "supply_failures_5y": None,  # Срывов поставки за 5 лет (малые)
    "own_rolling_stock": False,  # Собственный подвижной состав
    "K_int":         0.7,    # Коэффициент интенсивности накопления (0.5–0.9)

    # — Надёжность поставки (≥25 МВт) —
    "delivery_time_days": None,  # Время поставки, сут
    "supply_failures_3y": None,  # Случаев снижения <75% НЭЗТ за 3 года (≥25 МВт)
    "B_sr_fact_1y":  None,  # Факт. среднесут. расход год -1, т/сут
    "B_sr_fact_2y":  None,  # Факт. среднесут. расход год -2, т/сут
    "B_sr_fact_3y":  None,  # Факт. среднесут. расход год -3, т/сут

    # — Риск (≥25 МВт) —
    "risk_level":    "auto", # "auto" | "very_high" | "high" | "medium" | "low" | "very_low"
    "KIUM_t_pct":    None,   # КИУМт, %
    "P_min_dop_ratio_pct": None,  # Pмин.доп / Рраб, %

    # — НАЗТ (только если has_pgu_gtu=True) —
    "B_sut_emergency": None, # Суточный расход аварийного топлива, т/сут
    "N_nazt_days":    3.0,   # Дней работы на аварийном топливе (по проектной документации)

    # — НВЗТ (только для угля/торфа) —
    "V_vsp_3y":      None,   # Расход вспом. топлива за 3 года, т
    "V_osn_3y":      None,   # Расход основного топлива за 3 года, т
    "V_ro_t":        None,   # Объём запаса для растопок и обдувок, т
    "V_av_t":        None,   # Макс. расход при авариях топливоподачи за 3 года, т

    # — НВЗТ для малых ТЭС —
    "fuel_lighting_t":         None,
    "fuel_kindling_per_start_t": None,
    "num_starts_year":         None,
    "max_accident_fuel_5y_t":  None,
}


# ============================================================
# ДИАЛОГОВЫЕ ШАГИ — СБОР ДАННЫХ
# ============================================================
# Каждый шаг: {
#   "key":       ключ в профиле,
#   "question":  текст вопроса пользователю,
#   "type":      "text" | "float" | "int" | "choice" | "bool",
#   "choices":   {ключ: описание} (только для type="choice"),
#   "default":   значение по умолчанию (если пользователь пропустит),
#   "condition": callable(profile) → bool (показывать ли этот вопрос),
#   "hint":      подсказка (необязательно),
# }

DIALOG_STEPS: list[dict] = [

    # ── 1. Базовая информация ─────────────────────────────
    {
        "key":      "name",
        "question": "Как называется станция? (например: Казанская ТЭЦ-3)",
        "type":     "text",
    },
    {
        "key":      "power_mw",
        "question": "Какая установленная электрическая мощность станции? (МВт, число)",
        "type":     "float",
        "hint":     "Пример: 540",
    },
    {
        "key":      "category",
        "question": "Категория станции по мощности:",
        "type":     "choice",
        "choices": {
            "small": "Менее 25 МВт",
            "large": "25 МВт и более",
        },
        "auto_from": ("power_mw", lambda mw: "small" if (mw or 0) < 25 else "large"),
    },

    # ── 2. Вид топлива ────────────────────────────────────
    {
        "key":      "main_fuel",
        "question": "Основной вид топлива:",
        "type":     "choice",
        "choices": {
            "gas":    "Природный газ",
            "coal":   "Уголь",
            "mazut":  "Мазут",
            "peat":   "Торф",
            "diesel": "Дизельное топливо",
        },
    },
    {
        "key":      "delivery_type",
        "question": "Способ доставки топлива:",
        "type":     "choice",
        "choices": {
            "gas_pipeline":      "Газопровод",
            "pipeline":          "Трубопровод (мазут)",
            "pipeline_refinery": "Трубопровод с НПЗ (мазут)",
            "rail":              "Железная дорога",
            "road":              "Автотранспорт",
            "water":             "Водный транспорт",
            "conveyor":          "Конвейер",
        },
    },
    {
        "key":      "has_pgu_gtu",
        "question": "Есть ли на станции ПГУ или ГТУ? (да / нет)",
        "type":     "bool",
        "hint":     "От этого зависит, нужно ли рассчитывать НАЗТ",
    },

    # ── 3. Теплотехника ───────────────────────────────────
    {
        "key":      "Q_nr",
        "question": "Низшая теплота сгорания топлива (ккал/кг)?",
        "type":     "float",
        "hint":     "Уголь ≈ 5000–7000 | Мазут ≈ 9500 | Газ ≈ 8000 | Дизель ≈ 10200",
        "default":  7000.0,
    },
    {
        "key":      "b_ee",
        "question": "Удельный расход условного топлива на выработку электроэнергии (г/кВт·ч)?",
        "type":     "float",
        "hint":     "Это показатель из энергетического паспорта станции или из статотчётности. Обычно 280–360 г/кВт·ч. ПГУ — около 220–250, паровые турбины — 300–360",
        "default":  320.0,
    },
    {
        "key":      "b_te",
        "question": "Удельный расход условного топлива на тепловую энергию (кг/Гкал)?",
        "type":     "float",
        "hint":     "Типичное значение: 155–175 кг/Гкал",
        "default":  165.0,
    },

    # ── 4а. Режим выживания — только для ≥25 МВт ─────────
    {
        "key":      "P_min",
        "question": "Минимальная рабочая мощность в режиме выживания (МВт)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "large",

    },
    {
        "key":      "E_sn_day",
        "question": "Расход на собственные нужды при минимальной нагрузке (млн кВт·ч/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "large",
        "default":  0.3,
    },
    {
        "key":      "Q_ot_min",
        "question": "Минимальный отпуск тепла при минимальной нагрузке (Гкал/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "large",
        "hint":     "При минимальной среднемесячной температуре за 3 года",
        "default":  0.0,
    },

    # ── 4б. Режим выживания — только для <25 МВт ─────────
    {
        "key":      "E_vyr_min",
        "question": "Выработка электроэнергии при минимальной нагрузке (млн кВт·ч/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "small",
    },
    {
        "key":      "E_sn_min",
        "question": "Расход на собственные нужды при минимальной нагрузке (млн кВт·ч/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "small",
        "default":  0.0,
    },
    {
        "key":      "Q_ot_min",
        "question": "Минимальный отпуск тепла (Гкал/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "small",
        "default":  0.0,
    },

    # ── 5. Максимальные параметры (≥25 МВт) ──────────────
    {
        "key":      "P_rab",
        "question": "Максимальная рабочая мощность по графику (МВт)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "large",
        "hint":     "Обычно совпадает с установленной или чуть ниже. Берется из графика нагрузки. Если не знаете точно — ставьте установленную мощность",
    },
    {
        "key":      "E_sn_maks",
        "question": "Расход на СН при максимальной нагрузке (млн кВт·ч/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "large",
        "default":  0.5,
    },
    {
        "key":      "Q_t_max_5y",
        "question": "Максимальный среднесуточный отпуск тепла за последние 5 лет (Гкал/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "large",
        "default":  0.0,
    },

    # ── 6а. Надёжность поставки (≥25 МВт, не трубопровод) ─
    {
        "key":      "delivery_time_days",
        "question": "Средневзвешенное время поставки от поставщика до станции (сут)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("category") == "large" and
            p.get("delivery_type") not in ("pipeline", "gas_pipeline", "pipeline_refinery")
        ),
        "hint":     "Сколько дней от отгрузки у поставщика до поступления на склад станции. Если поставки идут из разных мест — берите среднее с учётом объёмов. Пример: 60% объёма едет 3 дня, 40% — 5 дней → T = (3×60 + 5×40)/100 = 3.8 сут",
    },
    {
        "key":      "supply_failures_3y",
        "question": "Сколько раз за последние 3 года запас опускался ниже 75% от НЭЗТ?",
        "type":     "int",
        "condition": lambda p: p.get("category") == "large",
        "default":  0,
        "hint":     "Смотреть в журналах учёта запасов. Если таких случаев не было — введите 0"
    },
    {
        "key":      "B_sr_fact_1y",
        "question": "Фактический среднесуточный расход топлива за прошлый год (т/сут)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("category") == "large" and
            p.get("delivery_type") in ("pipeline", "gas_pipeline")
        ),
    },
    {
        "key":      "B_sr_fact_2y",
        "question": "Фактический среднесуточный расход топлива 2 года назад (т/сут)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("category") == "large" and
            p.get("delivery_type") in ("pipeline", "gas_pipeline")
        ),
    },
    {
        "key":      "B_sr_fact_3y",
        "question": "Фактический среднесуточный расход топлива 3 года назад (т/сут)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("category") == "large" and
            p.get("delivery_type") in ("pipeline", "gas_pipeline")
        ),
    },

    # ── 6б. Надёжность поставки (<25 МВт) ────────────────
    {
        "key":      "B_r_sr_jan",
        "question": "Среднерасчётный суточный расход топлива в январе (т/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "small",
        "hint":     "Среднее из: текущий январь + три предыдущих",
    },
    {
        "key":      "B_r_sr_apr",
        "question": "Среднерасчётный суточный расход топлива в апреле (т/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "small",
    },
    {
        "key":      "T_psr",
        "question": "Среднее время поставки (сут)?",
        "type":     "float",
        "condition": lambda p: p.get("category") == "small",
    },
    {
        "key":      "supply_failures_5y",
        "question": "Сколько срывов поставки было за последние 5 лет?",
        "type":     "int",
        "condition": lambda p: p.get("category") == "small",
        "default":  0,
    },

    # ── 7. Уровень риска (≥25 МВт) ───────────────────────
    {
        "key":      "risk_level",
        "question": "Как определить уровень риска недовыработки?",
        "type":     "choice",
        "choices": {
            "auto":      "Рассчитать автоматически (введу КИУМт и Pмин.доп)",
            "very_high": "Очень высокий (RТЭС = 1,0)",
            "high":      "Высокий (RТЭС = 0,8)",
            "medium":    "Средний (RТЭС = 0,5)",
            "low":       "Низкий (RТЭС = 0,2)",
            "very_low":  "Очень низкий (RТЭС = 0)",
        },
        "condition": lambda p: p.get("category") == "large",
        "default": "medium",
    },
    {
        "key":      "KIUM_t_pct",
        "question": "КИУМт — коэффициент использования установленной тепловой мощности (%)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("category") == "large" and
            p.get("risk_level") == "auto"
        ),
        "hint":     "Если знаете готовое значение — введите его. Если нет: возьмите плановый годовой отпуск тепла (Гкал) и разделите на (установленную тепловую мощность в Гкал/ч × 8760 часов). Результат умножьте на 100. Пример: 500 000 Гкал / (150 Гкал/ч × 8760 ч) × 100 = 38%",
    },
    {
        "key":      "P_min_dop_ratio_pct",
        "question": "Отношение Pмин.доп к максимальной рабочей мощности (%)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("category") == "large" and
            p.get("risk_level") == "auto"
        ),
        "hint":     "минимально допустимая мощность по условиям энергосистемы. Берётся из актов зимнего контрольного замера от Системного оператора (СО ЕЭС). Если документа нет под рукой — уточните или введите 30% как приближенное",
    },

    # ── 8. НАЗТ (если есть ПГУ/ГТУ) ──────────────────────
    {
        "key":      "B_sut_emergency",
        "question": "Суточный расход аварийного топлива (т/сут)?",
        "type":     "float",
        "condition": lambda p: p.get("has_pgu_gtu", False),
        "hint":     "Расход при переводе ПГУ/ГТУ на резервное топливо. Берётся из проектной документации"
    },
    {
        "key":      "N_nazt_days",
        "question": "Количество суток работы на аварийном топливе (по проектной документации)?",
        "type":     "float",
        "condition": lambda p: p.get("has_pgu_gtu", False) and p.get("category") == "small",
        "default":  3.0,
        "hint":     "Обычно 3–5 суток",
    },

    # ── 9. НВЗТ (только для угля/торфа) ──────────────────
    {
        "key":      "V_vsp_3y",
        "question": "Суммарный расход вспомогательного топлива за 3 года (т)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "large"
        ),
    },
    {
        "key":      "V_osn_3y",
        "question": "Суммарный расход основного топлива за 3 года (т)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "large"
        ),
    },
    {
        "key":      "V_ro_t",
        "question": "Объём запаса для растопок и обдувок (т)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "large"
        ),
        "default":  0.0,
    },
    {
        "key":      "V_av_t",
        "question": "Максимальный расход при авариях топливоподачи за 3 года (т)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "large"
        ),
        "default":  0.0,
        "hint": "Сколько топлива потратили в самый тяжёлый месяц аварии на топливоподаче за последние 3 года. Если аварий не было — введите 0"
    },

    # ── НВЗТ малые ────────────────────────────────────────
    {
        "key":      "fuel_lighting_t",
        "question": "Объём топлива на подсветку (по проектной документации, т)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "small"
        ),
        "default":  0.0,
    },
    {
        "key":      "fuel_kindling_per_start_t",
        "question": "Расход топлива на одну растопку (т)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "small"
        ),
        "default":  0.0,
    },
    {
        "key":      "num_starts_year",
        "question": "Плановое количество растопок в год?",
        "type":     "int",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "small"
        ),
        "default":  0,
    },
    {
        "key":      "max_accident_fuel_5y_t",
        "question": "Максимальный расход топлива при авариях в топливоподаче за 5 лет (т)?",
        "type":     "float",
        "condition": lambda p: (
            p.get("main_fuel") in ("coal", "peat") and
            p.get("category") == "small"
        ),
        "default":  0.0,
    },
]


# ============================================================
# ФУНКЦИИ РАБОТЫ С ДИАЛОГОМ
# ============================================================

def get_next_question(profile: dict) -> Optional[dict]:
    """
    Возвращает следующий шаг диалога (dict из DIALOG_STEPS),
    у которого значение в профиле ещё не заполнено и условие выполнено.
    Возвращает None если все нужные данные собраны.
    """
    for step in DIALOG_STEPS:
        key = step["key"]

        # Проверяем условие показа
        condition = step.get("condition")
        if condition is not None:
            try:
                if not condition(profile):
                    continue
            except Exception:
                continue

        # Если значение ещё не задано — это следующий вопрос
        val = profile.get(key)
        if val is None:
            return step

    return None


def parse_user_answer(step: dict, raw_answer: str) -> tuple[Any, Optional[str]]:
    """
    Разбирает ответ пользователя для шага диалога.
    Возвращает (parsed_value, error_message).
    error_message = None если всё ок.
    """
    raw = raw_answer.strip()
    q_type = step.get("type", "text")

    if q_type == "text":
        if not raw:
            return None, "Введите название."
        return raw, None

    if q_type == "bool":
        low = raw.lower()
        if low in ("да", "yes", "y", "1", "true", "+"):
            return True, None
        if low in ("нет", "no", "n", "0", "false", "-"):
            return False, None
        return None, "Ответьте 'да' или 'нет'."

    if q_type in ("float", "int"):
        nums = re.findall(r"[-+]?\d+[\.,]?\d*", raw.replace(",", "."))
        if not nums:
            return None, "Введите числовое значение."
        val = float(nums[0].replace(",", "."))
        return (int(val) if q_type == "int" else val), None

    if q_type == "choice":
        choices: dict = step.get("choices", {})
        # Пробуем найти по ключу
        if raw.lower() in choices:
            return raw.lower(), None
        # Пробуем найти по номеру
        nums = re.findall(r"\d+", raw)
        if nums:
            idx = int(nums[0]) - 1
            keys = list(choices.keys())
            if 0 <= idx < len(keys):
                return keys[idx], None
        # Пробуем найти по частичному совпадению с описанием
        for key, desc in choices.items():
            if raw.lower() in desc.lower() or desc.lower() in raw.lower():
                return key, None
        choices_list = "\n".join(f"  {i+1}. {desc}" for i, (k, desc) in enumerate(choices.items()))
        return None, f"Не понял ответ. Варианты:\n{choices_list}"

    return raw, None


def format_question(step: dict) -> str:
    """
    Форматирует текст вопроса с подсказками и вариантами ответов.
    """
    q_type = step.get("type", "text")
    lines  = [f"📝 **{step['question']}**"]

    if hint := step.get("hint"):
        lines.append(f"*Подсказка: {hint}*")

    if q_type == "choice":
        for i, (key, desc) in enumerate(step["choices"].items(), 1):
            lines.append(f"  {i}. {desc}")
        lines.append("*(введите номер или ключевое слово)*")

    if q_type == "bool":
        lines.append("*(да / нет)*")

    if (default := step.get("default")) is not None:
        lines.append(f"*По умолчанию: {default} — нажмите Enter чтобы пропустить*")

    return "\n\n".join(lines)


def is_profile_complete(profile: dict) -> bool:
    """
    Проверяет, достаточно ли данных для запуска расчёта.
    Возвращает True если следующего обязательного вопроса нет.
    """
    return get_next_question(profile) is None


def apply_auto_fields(profile: dict) -> dict:
    """
    Применяет автоматические вычисления для полей с auto_from.
    (Например: определить category из power_mw)
    """
    for step in DIALOG_STEPS:
        auto_from = step.get("auto_from")
        if auto_from is None:
            continue
        src_key, func = auto_from
        if profile.get(step["key"]) is None and profile.get(src_key) is not None:
            profile[step["key"]] = func(profile[src_key])
    return profile


def apply_defaults(profile: dict) -> dict:
    """
    Заполняет незаполненные поля значениями по умолчанию
    (только для шагов, условие которых выполнено).
    """
    for step in DIALOG_STEPS:
        key     = step["key"]
        default = step.get("default")
        if default is None:
            continue
        condition = step.get("condition")
        if condition is not None:
            try:
                if not condition(profile):
                    continue
            except Exception:
                continue
        if profile.get(key) is None:
            profile[key] = default
    return profile


def profile_summary_text(profile: dict) -> str:
    """
    Возвращает читаемое текстовое резюме профиля для отображения в чате.
    """
    FUEL_NAMES = {
        "gas":    "Природный газ",
        "coal":   "Уголь",
        "mazut":  "Мазут",
        "peat":   "Торф",
        "diesel": "Дизельное топливо",
    }
    DELIVERY_NAMES = {
        "gas_pipeline":      "Газопровод",
        "pipeline":          "Трубопровод",
        "pipeline_refinery": "Трубопровод с НПЗ",
        "rail":              "Железная дорога",
        "road":              "Автотранспорт",
        "water":             "Водный транспорт",
        "conveyor":          "Конвейер",
    }
    RISK_NAMES = {
        "very_high": "Очень высокий",
        "high":      "Высокий",
        "medium":    "Средний",
        "low":       "Низкий",
        "very_low":  "Очень низкий",
        "auto":      "Авторасчёт",
    }

    lines = [
        f"🏭 **{profile.get('name', '—')}**",
        f"Категория: {'≥25 МВт' if profile.get('category') == 'large' else '<25 МВт'} "
        f"({profile.get('power_mw', '—')} МВт)",
        f"Топливо: {FUEL_NAMES.get(profile.get('main_fuel', ''), '—')}",
        f"Доставка: {DELIVERY_NAMES.get(profile.get('delivery_type', ''), '—')}",
        f"ПГУ/ГТУ: {'Да' if profile.get('has_pgu_gtu') else 'Нет'}",
        f"Q_нр: {profile.get('Q_nr', '—')} ккал/кг",
        f"b_ее: {profile.get('b_ee', '—')} г/кВт·ч | b_тэ: {profile.get('b_te', '—')} кг/Гкал",
    ]
    if profile.get("category") == "large":
        lines += [
            f"Pмин: {profile.get('P_min', '—')} МВт | Pраб: {profile.get('P_rab', '—')} МВт",
            f"Уровень риска: {RISK_NAMES.get(profile.get('risk_level', ''), '—')}",
        ]
    return "\n".join(lines)


def new_profile() -> dict:
    """Возвращает чистый профиль (копию шаблона)."""
    return {k: v for k, v in STATION_PROFILE_TEMPLATE.items()}


# ============================================================
# БЫСТРАЯ ПРОВЕРКА
# ============================================================

if __name__ == "__main__":
    p = new_profile()
    p["name"] = "Тест ТЭЦ"
    p["power_mw"] = 350
    p = apply_auto_fields(p)
    print("Следующий вопрос:", get_next_question(p)["question"])
    print("Категория (авто):", p["category"])
