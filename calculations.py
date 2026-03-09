# -*- coding: utf-8 -*-
"""
calculations.py — Все расчётные формулы по Приказу Минэнерго №1062 (ред. 25.06.2024)
«Порядок создания и использования тепловыми электростанциями запасов топлива»

Структура:
  Раздел 1 — Вспомогательные и общие функции
  Раздел 2 — ТЭС менее 25 МВт (Формулы 1–18)
  Раздел 3 — ТЭС 25 МВт и более (Формулы 19–38)
  Раздел 4 — Оценка риска недовыработки (Формулы 39–43)
  Раздел 5 — Полный расчёт по профилю станции (12 месяцев)
"""

from __future__ import annotations
from typing import Optional


# ============================================================
# РАЗДЕЛ 1. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

# Количество дней неснижаемого запаса в зависимости от типа доставки
def get_n_sut_nnzt(delivery_type: str) -> int:
    """
    Ф.4 / Ф.20: nсут для расчёта ННЗТ
    - 3 сут: трубопровод или газ
    - 7 сут: уголь, торф, дизель, мазут не по трубопроводу
    """
    if delivery_type in ("pipeline", "gas_pipeline"):
        return 3
    return 7


def calc_b_usl_ee(b_ee: float, E_ot: float) -> float:
    """
    Ф.6 / Ф.22: Bусл(ээ) = bээ × Эот
    b_ee  — удельный расход условного топлива на выработку э/э, г/кВт·ч
    E_ot  — отпуск электроэнергии, млн кВт·ч/сут (= Эвыр − Эсн)
    Возвращает т.у.т./сут
    """
    return b_ee * E_ot / 1000.0  # г → кг → т


def calc_E_ot(E_vyr: float, E_sn: float) -> float:
    """
    Ф.7 / Ф.23: Эот = Эвыр − Эсн
    E_vyr — выработка э/э, млн кВт·ч/сут
    E_sn  — расход на собственные нужды, млн кВт·ч/сут
    """
    return max(E_vyr - E_sn, 0.0)


def calc_b_usl_te(b_te: float, Q_ot: float) -> float:
    """
    Ф.8 / Ф.24: Bусл(тэ) = bтэ × Qот
    b_te  — удельный расход условного топлива на тепловую энергию, кг/Гкал
    Q_ot  — отпуск тепловой энергии, Гкал/сут
    Возвращает т.у.т./сут
    """
    return b_te * Q_ot / 1000.0  # кг → т


def calc_b_usl(b_usl_ee: float, b_usl_te: float) -> float:
    """
    Ф.5 / Ф.21: Bусл = Bусл(ээ) + Bусл(тэ), т.у.т./сут
    """
    return b_usl_ee + b_usl_te


# ============================================================
# РАЗДЕЛ 2. ТЭС МЕНЕЕ 25 МВт
# ============================================================

def calc_nnzt_small(
    b_usl: float,
    Q_nr: float,
    delivery_type: str = "rail"
) -> float:
    """
    Ф.4: ННЗТ = nсут × Bусл × 7000 / Qнр
    b_usl         — суточный расход условного топлива в режиме выживания, т.у.т./сут
    Q_nr          — низшая теплота сгорания натурального топлива, ккал/кг
    delivery_type — тип доставки (pipeline → 3 сут, иначе → 7 сут)
    Возвращает тыс.т.н.т.
    """
    n_sut = get_n_sut_nnzt(delivery_type)
    return n_sut * b_usl * 7000.0 / Q_nr  # тыс.т.н.т.


def calc_t_psr(T_list: list[float], V_list: list[float]) -> float:
    """
    Ф.11: Тпср = Σ(Ti×Vi) / Σ(Vi)
    Средневзвешенное время поставки по источникам, сутки.
    T_list — список времён поставки по каждому источнику, сут
    V_list — объёмы поставки по каждому источнику, т
    """
    if not T_list or not V_list or sum(V_list) == 0:
        return 0.0
    return sum(t * v for t, v in zip(T_list, V_list)) / sum(V_list)


def get_k_sr_small(failures_5y: int, delivery_type: str = "rail",
                   t_psr: float = 3.0, own_rolling_stock: bool = False) -> float:
    """
    Коэффициент срыва поставки Кср для ТЭС менее 25 МВт (Ф.9).
    failures_5y       — число срывов за 5 лет
    delivery_type     — тип доставки
    t_psr             — среднее время поставки, сут
    own_rolling_stock — собственный подвижной состав (уголь, доставка ≤1 сут)
    """
    # Специальные случаи
    if delivery_type == "pipeline_refinery":
        return 1.2  # мазут по трубопроводу с НПЗ
    if own_rolling_stock and delivery_type in ("rail", "road") and t_psr <= 1:
        return 1.5
    if t_psr <= 1:
        return 3.5

    # Основная шкала
    if failures_5y == 0:
        return 1.5
    elif failures_5y <= 1:
        return 2.0
    elif failures_5y <= 4:
        return 2.5
    elif failures_5y <= 7:
        return 3.0
    else:
        return 3.5


def calc_b_sr_small(
    B_sr_jan: float, B1_jan: float, B2_jan: float, B3_jan: float
) -> float:
    """
    Ф.10: Bрсрянв = (Bср.янв + B1янв + B2янв + B3янв) / 4
    Bср.янв — среднесуточный расход за текущий январь
    B1, B2, B3 — за предыдущие три января
    Аналогично для апреля.
    """
    return (B_sr_jan + B1_jan + B2_jan + B3_jan) / 4.0


def calc_nezt_jan_small(B_r_sr_jan: float, T_psr: float, K_sr: float) -> float:
    """
    Ф.9: НЭЗТянв = Bрсрянв × Тпср × Kср
    B_r_sr_jan — среднерасчётный суточный расход на январь, т/сут
    T_psr      — среднее время поставки, сут
    K_sr       — коэффициент срыва поставки
    Возвращает тыс.т.н.т.
    """
    return B_r_sr_jan * T_psr * K_sr / 1000.0


def calc_nezt_apr_small(B_r_sr_apr: float, T_psr: float, K_sr: float) -> float:
    """Ф.9: НЭЗТапр (аналогично январю)"""
    return B_r_sr_apr * T_psr * K_sr / 1000.0


def calc_nezt_oct_small(NEZT_jan: float, NEZT_apr: float) -> float:
    """
    Ф.12: НЭЗТокт = НЭЗТянв + (НЭЗТянв − НЭЗТапр)
    Если НЭЗТапр > НЭЗТянв → НЭЗТокт = НЭЗТянв
    """
    if NEZT_apr > NEZT_jan:
        return NEZT_jan
    return NEZT_jan + (NEZT_jan - NEZT_apr)


def calc_nezt_july_small(
    NEZT_oct: float, NEZT_apr: float, K_int: float = 0.7
) -> float:
    """
    Ф.15: НЭЗТиюль = [(НЭЗТокт − НЭЗТапр)/2 + НЭЗТапр] × Kинт
    K_int — коэффициент интенсивности накопления (0.5–0.9), обычно 0.7
    """
    return ((NEZT_oct - NEZT_apr) / 2.0 + NEZT_apr) * K_int


def calc_nezt_month_small(
    month: int,
    NEZT_oct_utv: float,
    NEZT_apr_utv: float,
    NEZT_july: float,
    NEZT_oct_plan: float
) -> float:
    """
    Ф.14–17: НЭЗТрасч.мес для каждого месяца (малые ТЭС)
    month — номер месяца 1–12 (1=январь)

    Ф.14 ноябрь–апрель (11,12,1,2,3,4): линейный спад от окт к апр
    Ф.16 май–июнь (5,6):                линейный рост от апр к июлю
    Ф.17 август–сентябрь (8,9):         линейный рост от июля к окт.план
    Ф.15 июль (7):                       НЭЗТиюль (уже вычислен)
    """
    if month == 10:
        return NEZT_oct_utv

    # Ф.14: ноябрь(11)–апрель(4) — n = порядковый шаг спада
    month_to_n_f14 = {11: 1, 12: 2, 1: 3, 2: 4, 3: 5, 4: 6}
    if month in month_to_n_f14:
        n = month_to_n_f14[month]
        step = (NEZT_oct_utv - NEZT_apr_utv) / 6.0
        return NEZT_oct_utv - step * n

    # Ф.16: май(5)=n1, июнь(6)=n2
    if month == 5:
        return NEZT_apr_utv + (NEZT_july - NEZT_apr_utv) / 3.0 * 1
    if month == 6:
        return NEZT_apr_utv + (NEZT_july - NEZT_apr_utv) / 3.0 * 2

    # Ф.15: июль
    if month == 7:
        return NEZT_july

    # Ф.17: август(8)=n1, сентябрь(9)=n2
    if month == 8:
        return NEZT_july + (NEZT_oct_plan - NEZT_july) / 3.0 * 1
    if month == 9:
        return NEZT_july + (NEZT_oct_plan - NEZT_july) / 3.0 * 2

    return NEZT_oct_utv


def calc_nazt_small(B_sut: float, N: float, k: float = 24.0) -> float:
    """
    Ф.18: НАЗТ = Bсут × N × k / 24
    B_sut — суточный расход аварийного топлива, т/сут
    N     — количество суток работы на аварийном топливе (3–5 по проектной документации)
    k     — часов в сутки (обычно 24)
    Возвращает тыс.т.н.т.
    """
    return B_sut * N * k / 24.0 / 1000.0


def calc_nvzt_small(
    fuel_lighting: float,
    fuel_kindling_per_start: float,
    num_starts: int,
    max_accident_fuel_5y: float
) -> float:
    """
    НВЗТ для малых ТЭС (текстовое описание в документе):
    = топливо на подсветки (по проектной документации)
    + топливо на растопки (по проектной документации × количество растопок)
    + максимальный фактический расход при авариях в топливоподаче за 5 лет
    Все в тыс.т.н.т.
    """
    return (fuel_lighting + fuel_kindling_per_start * num_starts + max_accident_fuel_5y) / 1000.0


def calc_onzt_small(NNZT: float, NEZT: float) -> float:
    """Ф.3: ОНЗТрасч.мес = НЭЗТрасч.мес + ННЗТрасч.мес"""
    return NNZT + NEZT


# ============================================================
# РАЗДЕЛ 3. ТЭС 25 МВт И БОЛЕЕ
# ============================================================

def calc_nnzt_large(
    b_usl: float,
    Q_nr: float,
    delivery_type: str = "pipeline"
) -> float:
    """
    Ф.20: ННЗТ = nсут × Bусл × 7000 / Qнр, т
    Для режима выживания (минимальные нагрузки по Правилам технол. функционирования).
    Возвращает т.н.т.
    """
    n_sut = get_n_sut_nnzt(delivery_type)
    return n_sut * b_usl * 7000.0 / Q_nr


def calc_b_maks_ee(b_ee: float, P_rab: float, E_sn_maks: float) -> float:
    """
    Ф.27: Bмакс(ээ) = bээ × (Рраб×24/1000 − Эснмах)
    P_rab     — максимальная рабочая мощность, МВт
    E_sn_maks — максимальный расход на СН, млн кВт·ч/сут
    Возвращает т.у.т./сут
    """
    E_out = P_rab * 24.0 / 1000.0 - E_sn_maks  # млн кВт·ч
    return b_ee * max(E_out, 0.0) / 1000.0


def calc_b_maks_te(b_te: float, Q_t_max: float) -> float:
    """
    Ф.28: Bмакс(тэ) = bтэ × Qтmax
    Q_t_max — максимальный среднесуточный отпуск тепла за 5 лет, Гкал/сут
    Возвращает т.у.т./сут
    """
    return b_te * Q_t_max / 1000.0


def calc_nezt_bv_large(
    b_maks: float,
    Q_n: float,
    delivery_type: str = "pipeline"
) -> float:
    """
    Ф.25: НЭЗТб.в. = Bмакс × nсут × 7000 / Qн, т
    nсут для НЭЗТб.в. = 3 (трубопровод/газ) или 7 (уголь и т.д.)
    Возвращает т.н.т.
    """
    n_sut = get_n_sut_nnzt(delivery_type)
    return b_maks * n_sut * 7000.0 / Q_n


def calc_nezt_sr_large(
    B_sr_1: float, B_sr_2: float, B_sr_3: float,
    Q_n: float,
    delivery_type: str = "pipeline"
) -> float:
    """
    Ф.29(1): НЭЗТср = [(Bср.факт.1+Bср.факт.2+Bср.факт.3)/3] × nсут(=3) × 7000/Qн
    Нижняя граница для НЭЗТ по газу/трубопроводу.
    B_sr_1,2,3 — факт. среднесуточный расход за три предыдущих года, т/сут
    """
    n_sut = 3
    B_sr_avg = (B_sr_1 + B_sr_2 + B_sr_3) / 3.0
    return B_sr_avg * n_sut * 7000.0 / Q_n


def get_r_tes(risk_level: str) -> float:
    """
    Матрица рисков (Рисунок 1 / Таблица 12):
    risk_level: 'very_high'|'high'|'medium'|'low'|'very_low'
    Возвращает RТЭС.
    """
    mapping = {
        "very_high": 1.0,
        "high":      0.8,
        "medium":    0.5,
        "low":       0.2,
        "very_low":  0.0,
    }
    return mapping.get(risk_level, 0.5)


def get_k_risk(risk_level: str) -> float:
    """
    Krisk для ограничений газа (Ф.30 / Таблица 12)
    """
    mapping = {
        "very_high": 1.0,
        "high":      0.8,
        "medium":    0.6,
        "low":       0.4,
        "very_low":  0.2,
    }
    return mapping.get(risk_level, 0.6)


def calc_nezt_large_pipeline(
    NEZT_bv: float,
    R_tes: float,
    NEZT_sr: float
) -> float:
    """
    Ф.29 + Ф.29(2): НЭЗТ для газа и мазута по трубопроводу
    НЭЗТ = НЭЗТб.в. × RТЭС, но не менее 50% от НЭЗТср
    """
    nezt = NEZT_bv * R_tes
    lower_bound = 0.5 * NEZT_sr
    if nezt < lower_bound:
        return lower_bound
    return nezt


def get_k_post_large(T_days: float) -> float:
    """
    Кпост по Т (Ф.43 / Ф.29(3)): коэффициент времени поставки для ≥25 МВт.
    T_days — средневзвешенное время поставки, сут.
    """
    if T_days <= 1:   return 0.3
    if T_days <= 2:   return 0.4
    if T_days <= 3:   return 0.5
    if T_days <= 4:   return 0.7
    if T_days <= 5:   return 0.9
    if T_days <= 6:   return 1.0
    if T_days <= 7:   return 1.1
    if T_days <= 8:   return 1.3
    if T_days <= 9:   return 1.4
    if T_days <= 10:  return 1.5
    return 1.8


def get_k_sr_large(supply_failures_3y: int) -> float:
    """
    Кср для ≥25 МВт — по числу случаев снижения запасов ниже 75% НЭЗТ за 3 года.
    supply_failures_3y — число случаев снижения <75% НЭЗТ за 3 года.
    """
    if supply_failures_3y == 0:   return 1.0
    if supply_failures_3y <= 1:   return 1.1
    if supply_failures_3y <= 4:   return 1.5
    if supply_failures_3y <= 7:   return 2.0
    return 2.5


def calc_nezt_large_solid(
    NEZT_bv: float,
    K_post: float,
    K_sr: float
) -> float:
    """
    Ф.29(3): НЭЗТ = НЭЗТб.в. × Кпост × Кср
    Для угля, торфа, дизеля, мазута не по трубопроводу.
    """
    return NEZT_bv * K_post * K_sr


def calc_nazt_large_bv(B_sut: float) -> float:
    """Ф.37: НАЗТб.в. = 3 × Bсут (т.н.т.)"""
    return 3.0 * B_sut


def calc_nazt_large(
    NAZT_bv: float,
    R_tes: float
) -> float:
    """
    Ф.36: НАЗТ = НАЗТб.в. × RТЭС
    Если НАЗТ < 2/3 НАЗТб.в. → НАЗТ = 2/3 НАЗТб.в.
    """
    nazt = NAZT_bv * R_tes
    lower_bound = (2.0 / 3.0) * NAZT_bv
    if nazt < lower_bound:
        return lower_bound
    return nazt


def calc_nvzt_large(
    NNZT: float,
    NEZT: float,
    V_vsp: float,
    V_osn: float,
    V_ro: float,
    V_av: float
) -> float:
    """
    Ф.38: НВЗТ = (ННЗТ+НЭЗТ) × Bвсп/Bосн + Vр/о + Vав
    V_vsp — расход вспомогательного топлива (за сопоставимый период), т
    V_osn — расход основного топлива (за тот же период), т
    V_ro  — объём запаса для растопок и обдувок, т
    V_av  — макс. месячный расход при авариях топливоподачи за 3 года, т
    """
    if V_osn == 0:
        return V_ro + V_av
    return (NNZT + NEZT) * (V_vsp / V_osn) + V_ro + V_av


def calc_onzt_large(NNZT: float, NEZT: float, NVZT: float = 0.0) -> float:
    """
    Ф.19: ОНЗТ = ННЗТ + НЭЗТ (+ НВЗТ для угля/торфа)
    """
    return NNZT + NEZT + NVZT


# ============================================================
# РАЗДЕЛ 4. ОЦЕНКА РИСКА НЕДОВЫРАБОТКИ (ТЭС ≥ 25 МВт)
# ============================================================

def calc_kium_t(Q_ts_plan: float, Q_ts_ust: float, n_mes: int = 1) -> float:
    """
    Ф.40: КИУМт = Qтс_план / (Qтс_уст × nмес) × 100%
    Q_ts_plan — плановый отпуск тепла, Гкал
    Q_ts_ust  — установленная тепловая мощность × число часов в месяце, Гкал
    n_mes     — число месяцев (обычно 1)
    """
    if Q_ts_ust == 0:
        return 0.0
    return (Q_ts_plan / (Q_ts_ust * n_mes)) * 100.0


def get_score_kium_t(kium_t_pct: float) -> int:
    """Балл КИУМт (0–5) из Ф.40"""
    if kium_t_pct == 0:   return 0
    if kium_t_pct <= 5:   return 1
    if kium_t_pct <= 10:  return 2
    if kium_t_pct <= 25:  return 3
    if kium_t_pct <= 40:  return 4
    return 5


def get_score_p_min(p_min_ratio_pct: float) -> int:
    """
    Балл Pмин.доп/РрабТЭС (0–5)
    p_min_ratio_pct — Pмин.доп / Рраб × 100%
    """
    if p_min_ratio_pct <= 10:  return 0
    if p_min_ratio_pct <= 20:  return 1
    if p_min_ratio_pct <= 30:  return 2
    if p_min_ratio_pct <= 35:  return 3
    if p_min_ratio_pct <= 40:  return 4
    return 5


def calc_y_kr_tes(
    score_kium_t: int,
    score_p_min: int,
    weight_heat: float = 0.5,
    weight_power: float = 0.5
) -> float:
    """
    Ф.39 (упрощённо): Yкр_ТЭС = Σ[Весi × Σ(Весn × Баллn/5)] × 100%
    Группа теплоснабжения (вес 0.5): балл КИУМт
    Группа энергорежима (вес 0.5):   балл Pмин.доп
    Возвращает % (0–100)
    """
    y_heat  = weight_heat  * (score_kium_t / 5.0)
    y_power = weight_power * (score_p_min  / 5.0)
    return (y_heat + y_power) * 100.0


def get_risk_level_from_y_kr(y_kr_pct: float) -> str:
    """
    Уровни критичности по Yкр:
    ≥80% → очень высокая; 60–80 → высокая; 40–60 → средняя;
    20–40 → низкая; <20 → очень низкая
    """
    if y_kr_pct >= 80: return "very_high"
    if y_kr_pct >= 60: return "high"
    if y_kr_pct >= 40: return "medium"
    if y_kr_pct >= 20: return "low"
    return "very_low"


def calc_t_weighted_large(T_list: list[float], V_list: list[float]) -> float:
    """
    Ф.43: Т = Σ(Tn×Vn)/Σ(Vn)
    Средневзвешенное время поставки для ТЭС ≥ 25 МВт.
    """
    if not T_list or not V_list or sum(V_list) == 0:
        return 0.0
    return sum(t * v for t, v in zip(T_list, V_list)) / sum(V_list)


# ============================================================
# РАЗДЕЛ 5. ПОЛНЫЙ РАСЧЁТ ПО ПРОФИЛЮ СТАНЦИИ (12 МЕСЯЦЕВ)
# ============================================================

def run_full_calculation(profile: dict) -> dict:
    """
    Главная функция расчёта.
    Принимает профиль станции (dict), возвращает dict с результатами по всем нормативам
    и таблицей на 12 месяцев.

    Ветвление логики:
      - category == "small" (<25 МВт): Раздел II приказа
      - category == "large" (≥25 МВт): Раздел III приказа
      - main_fuel и delivery_type определяют формулу НЭЗТ

    Структура profile — см. station_profile.py
    """
    results = {
        "station_name": profile.get("name", "Неизвестная ТЭЦ"),
        "category": profile.get("category"),
        "main_fuel": profile.get("main_fuel"),
        "delivery_type": profile.get("delivery_type"),
        "errors": [],
        "warnings": [],
    }

    category      = profile.get("category", "large")
    main_fuel     = profile.get("main_fuel", "coal")
    delivery_type = profile.get("delivery_type", "rail")
    Q_nr          = profile.get("Q_nr", 7000.0)

    # ── Режим выживания: Bусл ────────────────────────────
    b_ee     = profile.get("b_ee", 320.0)
    b_te     = profile.get("b_te", 165.0)

    if category == "small":
        E_vyr_min = profile.get("E_vyr_min", 0.0)
        E_sn_min  = profile.get("E_sn_min",  0.0)
        Q_ot_min  = profile.get("Q_ot_min",  0.0)
    else:
        P_min     = profile.get("P_min",     50.0)
        E_sn_min  = profile.get("E_sn_day",  0.0)
        E_vyr_min = P_min * 24.0 / 1000.0          # млн кВт·ч/сут
        Q_ot_min  = profile.get("Q_ot_min",  0.0)

    E_ot_min   = calc_E_ot(E_vyr_min, E_sn_min)
    b_usl_ee   = calc_b_usl_ee(b_ee, E_ot_min)
    b_usl_te   = calc_b_usl_te(b_te, Q_ot_min)
    b_usl      = calc_b_usl(b_usl_ee, b_usl_te)
    results["b_usl_survival"] = round(b_usl, 4)

    # ── ННЗТ ─────────────────────────────────────────────
    if category == "small":
        NNZT = calc_nnzt_small(b_usl, Q_nr, delivery_type)
        results["ННЗТ_тыс_т"] = round(NNZT, 3)
    else:
        NNZT = calc_nnzt_large(b_usl, Q_nr, delivery_type)
        results["ННЗТ_т"] = round(NNZT, 1)

    # ── НЭЗТ ─────────────────────────────────────────────
    if category == "small":
        # Формулы 9–17
        B_r_sr_jan = profile.get("B_r_sr_jan", 0.0)
        B_r_sr_apr = profile.get("B_r_sr_apr", 0.0)
        T_psr      = profile.get("T_psr", 3.0)
        failures_5y = profile.get("supply_failures_5y", 0)
        own_stock   = profile.get("own_rolling_stock", False)
        K_sr        = get_k_sr_small(failures_5y, delivery_type, T_psr, own_stock)
        K_int       = profile.get("K_int", 0.7)

        NEZT_jan  = calc_nezt_jan_small(B_r_sr_jan, T_psr, K_sr)
        NEZT_apr  = calc_nezt_apr_small(B_r_sr_apr, T_psr, K_sr)
        NEZT_oct  = calc_nezt_oct_small(NEZT_jan, NEZT_apr)
        NEZT_july = calc_nezt_july_small(NEZT_oct, NEZT_apr, K_int)

        results["K_sr"] = K_sr
        results["НЭЗТ_янв_тыс_т"] = round(NEZT_jan, 3)
        results["НЭЗТ_апр_тыс_т"] = round(NEZT_apr, 3)
        results["НЭЗТ_окт_тыс_т"] = round(NEZT_oct, 3)

        monthly_nezt = {}
        for m in range(1, 13):
            val = calc_nezt_month_small(m, NEZT_oct, NEZT_apr, NEZT_july, NEZT_oct)
            monthly_nezt[MONTHS_RU[m - 1]] = round(val, 3)
        results["НЭЗТ_по_месяцам_тыс_т"] = monthly_nezt

    else:
        # Формулы 25–29(3) — ветвление по типу топлива
        P_rab     = profile.get("P_rab",      profile.get("P_min", 50.0))
        E_sn_maks = profile.get("E_sn_maks",  0.0)
        Q_t_max   = profile.get("Q_t_max_5y", 0.0)

        b_maks_ee = calc_b_maks_ee(b_ee, P_rab, E_sn_maks)
        b_maks_te = calc_b_maks_te(b_te, Q_t_max)
        b_maks    = b_maks_ee + b_maks_te
        results["b_maks"] = round(b_maks, 4)

        NEZT_bv = calc_nezt_bv_large(b_maks, Q_nr, delivery_type)
        results["НЭЗТ_бв_т"] = round(NEZT_bv, 1)

        is_pipeline_fuel = (
            delivery_type in ("pipeline", "gas_pipeline") or
            main_fuel in ("gas",)
        )

        if is_pipeline_fuel:
            # Риск → RТЭС
            risk_level = profile.get("risk_level", "medium")
            if risk_level == "auto":
                risk_level = _auto_risk_level(profile)
            R_tes = get_r_tes(risk_level)

            B_sr_1 = profile.get("B_sr_fact_1y", b_maks * 0.6)
            B_sr_2 = profile.get("B_sr_fact_2y", b_maks * 0.6)
            B_sr_3 = profile.get("B_sr_fact_3y", b_maks * 0.6)
            NEZT_sr = calc_nezt_sr_large(B_sr_1, B_sr_2, B_sr_3, Q_nr, delivery_type)

            NEZT = calc_nezt_large_pipeline(NEZT_bv, R_tes, NEZT_sr)
            results["R_ТЭС"]      = R_tes
            results["НЭЗТ_ср_т"]  = round(NEZT_sr, 1)
            results["НЭЗТ_т"]     = round(NEZT, 1)
            results["formula_НЭЗТ"] = "Ф.29: НЭЗТб.в. × RТЭС (не менее 50% НЭЗТср)"

        else:
            # Уголь, торф, дизель, мазут не по трубопроводу
            T_delivery = profile.get("delivery_time_days", 5.0)
            failures_3y = profile.get("supply_failures_3y", 0)
            K_post = get_k_post_large(T_delivery)
            K_sr   = get_k_sr_large(failures_3y)

            NEZT = calc_nezt_large_solid(NEZT_bv, K_post, K_sr)
            results["K_пост"]     = K_post
            results["K_ср"]       = K_sr
            results["НЭЗТ_т"]     = round(NEZT, 1)
            results["formula_НЭЗТ"] = "Ф.29(3): НЭЗТб.в. × Кпост × Кср"

        # НЭЗТ одинаков на все месяцы для ≥25 МВт (может уточняться по сезону)
        results["НЭЗТ_по_месяцам_т"] = {m: round(NEZT, 1) for m in MONTHS_RU}

    # ── НАЗТ (только если есть ПГУ/ГТУ) ─────────────────
    if profile.get("has_pgu_gtu", False):
        B_sut_emerg = profile.get("B_sut_emergency", 0.0)
        if category == "small":
            N_nazt = profile.get("N_nazt_days", 3.0)
            NAZT = calc_nazt_small(B_sut_emerg, N_nazt)
            results["НАЗТ_тыс_т"] = round(NAZT, 3)
        else:
            risk_level = profile.get("risk_level", "medium")
            NAZT_bv = calc_nazt_large_bv(B_sut_emerg)
            R_tes   = get_r_tes(risk_level)
            NAZT    = calc_nazt_large(NAZT_bv, R_tes)
            results["НАЗТ_т"]     = round(NAZT, 1)
            results["НАЗТ_бв_т"]  = round(NAZT_bv, 1)

    # ── НВЗТ (уголь, торф) ───────────────────────────────
    NVZT = 0.0
    if main_fuel in ("coal", "peat"):
        if category == "small":
            fuel_light = profile.get("fuel_lighting_t", 0.0)
            fuel_kind  = profile.get("fuel_kindling_per_start_t", 0.0)
            n_starts   = profile.get("num_starts_year", 0)
            max_acc    = profile.get("max_accident_fuel_5y_t", 0.0)
            NVZT = calc_nvzt_small(fuel_light, fuel_kind, n_starts, max_acc)
            results["НВЗТ_тыс_т"] = round(NVZT, 3)
        else:
            V_vsp = profile.get("V_vsp_3y", 0.0)
            V_osn = profile.get("V_osn_3y", 1.0)
            V_ro  = profile.get("V_ro_t", 0.0)
            V_av  = profile.get("V_av_t", 0.0)
            NVZT  = calc_nvzt_large(NNZT, NEZT, V_vsp, V_osn, V_ro, V_av)
            results["НВЗТ_т"] = round(NVZT, 1)

    # ── ОНЗТ ─────────────────────────────────────────────
    if category == "small":
        ONZT = calc_onzt_small(NNZT, NEZT_jan)  # базовый (январь)
        results["ОНЗТ_янв_тыс_т"] = round(ONZT, 3)
        monthly_onzt = {}
        for m_name, nezt_val in results["НЭЗТ_по_месяцам_тыс_т"].items():
            monthly_onzt[m_name] = round(NNZT + nezt_val, 3)
        results["ОНЗТ_по_месяцам_тыс_т"] = monthly_onzt
    else:
        ONZT = calc_onzt_large(NNZT, NEZT, NVZT)
        results["ОНЗТ_т"] = round(ONZT, 1)
        results["ОНЗТ_по_месяцам_т"] = {m: round(NNZT + v + NVZT, 1)
                                         for m, v in results["НЭЗТ_по_месяцам_т"].items()}

    # ── Итоговая таблица 12 месяцев ──────────────────────
    table = []
    month_key_nezt = "НЭЗТ_по_месяцам_тыс_т" if category == "small" else "НЭЗТ_по_месяцам_т"
    month_key_onzt = "ОНЗТ_по_месяцам_тыс_т" if category == "small" else "ОНЗТ_по_месяцам_т"
    units = "тыс.т.н.т." if category == "small" else "т.н.т."

    nnzt_val  = results.get("ННЗТ_тыс_т", results.get("ННЗТ_т", 0))
    nvzt_val  = results.get("НВЗТ_тыс_т", results.get("НВЗТ_т", 0))
    nazt_val  = results.get("НАЗТ_тыс_т", results.get("НАЗТ_т", None))

    for m_name in MONTHS_RU:
        nezt = results.get(month_key_nezt, {}).get(m_name, 0)
        onzt = results.get(month_key_onzt, {}).get(m_name, 0)
        row = {
            "Месяц":   m_name,
            f"ННЗТ ({units})": nnzt_val,
            f"НЭЗТ ({units})": nezt,
            f"ОНЗТ ({units})": onzt,
        }
        if nvzt_val:
            row[f"НВЗТ ({units})"] = nvzt_val
        if nazt_val is not None:
            row[f"НАЗТ ({units})"] = nazt_val
        table.append(row)

    results["таблица_12_месяцев"] = table
    results["единицы"] = units

    return results


def _auto_risk_level(profile: dict) -> str:
    """
    Автоматическое определение уровня риска на основе профиля станции
    (упрощённая версия формул 39–41).
    """
    kium_t     = profile.get("KIUM_t_pct", 0.0)
    p_min_r    = profile.get("P_min_dop_ratio_pct", 0.0)

    score_k = get_score_kium_t(kium_t)
    score_p = get_score_p_min(p_min_r)
    y_kr    = calc_y_kr_tes(score_k, score_p)

    return get_risk_level_from_y_kr(y_kr)


# ============================================================
# БЫСТРАЯ ПРОВЕРКА
# ============================================================

if __name__ == "__main__":
    test_profile = {
        "name": "Тестовая ТЭЦ-1",
        "category": "large",
        "main_fuel": "gas",
        "delivery_type": "pipeline",
        "Q_nr": 8500,
        "b_ee": 310.0,
        "b_te": 160.0,
        "P_min": 100.0,
        "E_sn_day": 0.5,
        "Q_ot_min": 300.0,
        "P_rab": 420.0,
        "E_sn_maks": 0.8,
        "Q_t_max_5y": 2500.0,
        "risk_level": "medium",
        "B_sr_fact_1y": 250.0,
        "B_sr_fact_2y": 240.0,
        "B_sr_fact_3y": 260.0,
        "has_pgu_gtu": True,
        "B_sut_emergency": 180.0,
    }
    res = run_full_calculation(test_profile)
    print(f"ННЗТ: {res.get('ННЗТ_т')} т.н.т.")
    print(f"НЭЗТ: {res.get('НЭЗТ_т')} т.н.т.")
    print(f"ОНЗТ: {res.get('ОНЗТ_т')} т.н.т.")
    print(f"НАЗТ: {res.get('НАЗТ_т')} т.н.т.")
    print("Таблица 12 месяцев:")
    for row in res["таблица_12_месяцев"]:
        print(" ", row)
