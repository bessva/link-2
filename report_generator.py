# -*- coding: utf-8 -*-
"""
report_generator.py — Генерация отчёта по результатам расчёта нормативов

Содержит:
  - build_report_text()      — полный текстовый отчёт (протокол расчёта)
  - build_report_markdown()  — то же самое в Markdown для отображения в интерфейсе
  - build_gigachat_context() — компактный контекст для передачи в GigaChat
  - results_to_dataframe()   — таблица 12 месяцев в формате pandas DataFrame
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional


MONTHS_RU = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

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
}


# ============================================================
# ПОЛНЫЙ ТЕКСТОВЫЙ ОТЧЁТ (ПРОТОКОЛ РАСЧЁТА)
# ============================================================

def build_report_text(profile: dict, results: dict) -> str:
    """
    Возвращает полный текстовый протокол расчёта нормативов запасов топлива.
    Подходит для сохранения в .txt / .docx.
    """
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    category = profile.get("category", "large")
    units    = results.get("единицы", "т.н.т.")
    lines    = []

    # ── Шапка ─────────────────────────────────────────────
    lines += [
        "=" * 70,
        "ПРОТОКОЛ РАСЧЁТА НОРМАТИВОВ ЗАПАСОВ ТОПЛИВА",
        "Приказ Минэнерго России от 27.11.2020 №1062 (ред. от 25.06.2024)",
        "=" * 70,
        f"Дата расчёта : {now}",
        f"Станция      : {profile.get('name', '—')}",
        f"Категория    : {'ТЭС ≥ 25 МВт (Раздел III)' if category == 'large' else 'ТЭС < 25 МВт (Раздел II)'}",
        f"Мощность     : {profile.get('power_mw', '—')} МВт",
        f"Основное топливо : {FUEL_NAMES.get(profile.get('main_fuel', ''), '—')}",
        f"Способ доставки  : {DELIVERY_NAMES.get(profile.get('delivery_type', ''), '—')}",
        f"Теплота сгорания (Qнр): {profile.get('Q_nr', '—')} ккал/кг",
        "-" * 70,
    ]

    # ── Bусл ──────────────────────────────────────────────
    lines += [
        "1. РАСЧЁТ УСЛОВНОГО ТОПЛИВА В РЕЖИМЕ ВЫЖИВАНИЯ",
        f"   bээ = {profile.get('b_ee', '—')} г/кВт·ч",
        f"   bтэ = {profile.get('b_te', '—')} кг/Гкал",
        f"   Bусл = {results.get('b_usl_survival', '—')} т.у.т./сут",
        "",
    ]

    # ── ННЗТ ──────────────────────────────────────────────
    n_sut = 3 if profile.get("delivery_type") in ("pipeline", "gas_pipeline") else 7
    nnzt  = results.get("ННЗТ_тыс_т", results.get("ННЗТ_т", "—"))
    lines += [
        "2. ННЗТ — НЕСНИЖАЕМЫЙ НОРМАТИВНЫЙ ЗАПАС ТОПЛИВА",
        f"   Формула: ННЗТ = nсут × Bусл × 7000 / Qнр",
        f"   nсут = {n_sut} сут",
        f"   ННЗТ = {nnzt} {units}",
        "",
    ]

    # ── НЭЗТ ──────────────────────────────────────────────
    lines.append("3. НЭЗТ — НОРМАТИВНЫЙ ЭКСПЛУАТАЦИОННЫЙ ЗАПАС ТОПЛИВА")
    nezt_formula = results.get("formula_НЭЗТ", "")
    if nezt_formula:
        lines.append(f"   Применяемая формула: {nezt_formula}")

    if category == "large":
        lines += [
            f"   НЭЗТб.в. = {results.get('НЭЗТ_бв_т', '—')} т",
            f"   Bмакс    = {results.get('b_maks', '—')} т.у.т./сут",
        ]
        if "R_ТЭС" in results:
            lines += [
                f"   R_ТЭС    = {results.get('R_ТЭС', '—')}",
                f"   НЭЗТср   = {results.get('НЭЗТ_ср_т', '—')} т",
            ]
        if "K_пост" in results:
            lines += [
                f"   Кпост    = {results.get('K_пост', '—')}",
                f"   Кср      = {results.get('K_ср', '—')}",
            ]
        lines.append(f"   НЭЗТ = {results.get('НЭЗТ_т', '—')} {units}")
    else:
        lines += [
            f"   Кср        = {results.get('K_sr', '—')}",
            f"   НЭЗТ январь = {results.get('НЭЗТ_янв_тыс_т', '—')} {units}",
            f"   НЭЗТ апрель = {results.get('НЭЗТ_апр_тыс_т', '—')} {units}",
            f"   НЭЗТ октябрь= {results.get('НЭЗТ_окт_тыс_т', '—')} {units}",
        ]
    lines.append("")

    # ── НАЗТ ──────────────────────────────────────────────
    nazt = results.get("НАЗТ_тыс_т", results.get("НАЗТ_т"))
    if nazt is not None:
        lines += [
            "4. НАЗТ — НОРМАТИВНЫЙ АВАРИЙНЫЙ ЗАПАС ТОПЛИВА (ПГУ/ГТУ)",
        ]
        if "НАЗТ_бв_т" in results:
            lines.append(f"   НАЗТб.в. = {results.get('НАЗТ_бв_т', '—')} т")
        lines += [
            f"   НАЗТ = {nazt} {units}",
            "",
        ]

    # ── НВЗТ ──────────────────────────────────────────────
    nvzt = results.get("НВЗТ_тыс_т", results.get("НВЗТ_т"))
    if nvzt is not None:
        lines += [
            "5. НВЗТ — НОРМАТИВНЫЙ ВСПОМОГАТЕЛЬНЫЙ ЗАПАС ТОПЛИВА",
            f"   НВЗТ = {nvzt} {units}",
            "",
        ]

    # ── Таблица 12 месяцев ────────────────────────────────
    lines += [
        "─" * 70,
        "ТАБЛИЦА НОРМАТИВОВ ПО МЕСЯЦАМ",
        "─" * 70,
    ]

    table = results.get("таблица_12_месяцев", [])
    if table:
        # Шапка таблицы
        headers = list(table[0].keys())
        col_w   = [max(len(str(h)), max(len(str(row.get(h, ""))) for row in table))
                   for h in headers]
        header_line = " | ".join(str(h).ljust(w) for h, w in zip(headers, col_w))
        lines.append(header_line)
        lines.append("-" * len(header_line))
        for row in table:
            lines.append(" | ".join(str(row.get(h, "—")).ljust(w) for h, w in zip(headers, col_w)))
    else:
        lines.append("Таблица не сформирована.")

    lines += [
        "─" * 70,
        "Расчёт выполнен программой ЛИНК (Приказ №1062, ред. 25.06.2024)",
        "=" * 70,
    ]

    return "\n".join(lines)


# ============================================================
# ОТЧЁТ В ФОРМАТЕ MARKDOWN
# ============================================================

def build_report_markdown(profile: dict, results: dict) -> str:
    """
    Возвращает отчёт в Markdown — для отображения в Streamlit/чате.
    """
    now      = datetime.now().strftime("%d.%m.%Y %H:%M")
    category = profile.get("category", "large")
    units    = results.get("единицы", "т.н.т.")
    md       = []

    md.append(f"## 📊 Нормативы запасов топлива — {profile.get('name', '—')}")
    md.append(f"*Расчёт по Приказу Минэнерго №1062 (ред. 25.06.2024) | {now}*")
    md.append("")

    # Параметры станции
    md.append("### ⚙️ Параметры станции")
    md.append(f"- **Мощность:** {profile.get('power_mw', '—')} МВт "
              f"({'≥25 МВт' if category == 'large' else '<25 МВт'})")
    md.append(f"- **Топливо:** {FUEL_NAMES.get(profile.get('main_fuel', ''), '—')}")
    md.append(f"- **Доставка:** {DELIVERY_NAMES.get(profile.get('delivery_type', ''), '—')}")
    md.append(f"- **Qнр:** {profile.get('Q_nr', '—')} ккал/кг")
    md.append(f"- **ПГУ/ГТУ:** {'Да' if profile.get('has_pgu_gtu') else 'Нет'}")
    md.append("")

    # Результаты
    md.append("### 📐 Результаты расчёта")

    nnzt = results.get("ННЗТ_тыс_т", results.get("ННЗТ_т", "—"))
    nezt = results.get("НЭЗТ_т", results.get("НЭЗТ_янв_тыс_т", "—"))
    onzt = results.get("ОНЗТ_т", results.get("ОНЗТ_янв_тыс_т", "—"))
    nazt = results.get("НАЗТ_т", results.get("НАЗТ_тыс_т"))
    nvzt = results.get("НВЗТ_т", results.get("НВЗТ_тыс_т"))

    md.append(f"| Норматив | Значение | Единицы |")
    md.append(f"|----------|----------|---------|")
    md.append(f"| **ННЗТ** (неснижаемый) | {nnzt} | {units} |")
    md.append(f"| **НЭЗТ** (эксплуатационный) | {nezt} | {units} |")
    md.append(f"| **ОНЗТ** (общий) | {onzt} | {units} |")
    if nazt is not None:
        md.append(f"| **НАЗТ** (аварийный, ПГУ/ГТУ) | {nazt} | {units} |")
    if nvzt is not None:
        md.append(f"| **НВЗТ** (вспомогательный) | {nvzt} | {units} |")

    if category == "large":
        md.append("")
        md.append(f"*Применённая формула НЭЗТ: {results.get('formula_НЭЗТ', '—')}*")
        if "R_ТЭС" in results:
            md.append(f"*RТЭС = {results.get('R_ТЭС')} | НЭЗТср = {results.get('НЭЗТ_ср_т', '—')} т*")
        if "K_пост" in results:
            md.append(f"*Кпост = {results.get('K_пост')} | Кср = {results.get('K_ср')}*")

    md.append("")

    # Таблица 12 месяцев
    md.append("### 📅 Нормативы по месяцам")
    table = results.get("таблица_12_месяцев", [])
    if table:
        headers = list(table[0].keys())
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in table:
            md.append("| " + " | ".join(str(row.get(h, "—")) for h in headers) + " |")
    else:
        md.append("*Таблица не сформирована.*")

    return "\n".join(md)


# ============================================================
# КОНТЕКСТ ДЛЯ GIGACHAT
# ============================================================

def build_gigachat_context(profile: dict, results: dict) -> str:
    """
    Компактный контекст о станции и нормативах для GigaChat.
    Передаётся как часть system_prompt или user_message.
    Ограничен по объёму чтобы не переполнять контекстное окно.
    """
    category = profile.get("category", "large")
    units    = results.get("единицы", "т.н.т.")

    nnzt = results.get("ННЗТ_тыс_т", results.get("ННЗТ_т", "—"))
    nezt = results.get("НЭЗТ_т", results.get("НЭЗТ_янв_тыс_т", "—"))
    onzt = results.get("ОНЗТ_т", results.get("ОНЗТ_янв_тыс_т", "—"))
    nazt = results.get("НАЗТ_т", results.get("НАЗТ_тыс_т", "—"))
    nvzt = results.get("НВЗТ_т", results.get("НВЗТ_тыс_т", "—"))

    ctx = f"""=== ПРОФИЛЬ СТАНЦИИ (расчётные данные) ===
Станция: {profile.get('name', '—')}
Категория: {'≥25 МВт' if category == 'large' else '<25 МВт'} | Мощность: {profile.get('power_mw', '—')} МВт
Топливо: {FUEL_NAMES.get(profile.get('main_fuel', ''), '—')} | Доставка: {DELIVERY_NAMES.get(profile.get('delivery_type', ''), '—')}
Qнр: {profile.get('Q_nr', '—')} ккал/кг | ПГУ/ГТУ: {'да' if profile.get('has_pgu_gtu') else 'нет'}

=== НОРМАТИВЫ ({units}) ===
ННЗТ (неснижаемый):        {nnzt}
НЭЗТ (эксплуатационный):   {nezt}
ОНЗТ (общий):              {onzt}
НАЗТ (аварийный, ПГУ/ГТУ): {nazt}
НВЗТ (вспомогательный):    {nvzt}
"""

    if category == "large" and "R_ТЭС" in results:
        ctx += f"RТЭС (коэффициент риска): {results.get('R_ТЭС')}\n"
    if category == "large" and "K_пост" in results:
        ctx += f"Кпост: {results.get('K_пост')} | Кср: {results.get('K_ср')}\n"

    # Добавляем помесячную таблицу кратко
    table = results.get("таблица_12_месяцев", [])
    if table:
        ctx += "\n=== НОРМАТИВЫ ПО МЕСЯЦАМ ===\n"
        for row in table:
            vals = " | ".join(f"{k}: {v}" for k, v in row.items() if k != "Месяц")
            ctx += f"{row.get('Месяц')}: {vals}\n"

    ctx += "=== КОНЕЦ ДАННЫХ ПО СТАНЦИИ ==="
    return ctx


# ============================================================
# PANDAS DATAFRAME (для st.dataframe / экспорта)
# ============================================================

def results_to_dataframe(results: dict):
    """
    Конвертирует таблицу 12 месяцев в pandas DataFrame.
    Возвращает None если pandas недоступен.
    """
    try:
        import pandas as pd
        table = results.get("таблица_12_месяцев", [])
        if not table:
            return None
        return pd.DataFrame(table)
    except ImportError:
        return None


def results_to_excel_bytes(profile: dict, results: dict) -> Optional[bytes]:
    """
    Генерирует Excel-файл с отчётом (bytes) для скачивания через st.download_button.
    Возвращает None если openpyxl/pandas недоступны.
    """
    try:
        import pandas as pd
        from io import BytesIO
        import openpyxl
        from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

        buf = BytesIO()

        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            # Лист 1: Таблица нормативов
            df = results_to_dataframe(results)
            if df is not None:
                df.to_excel(writer, sheet_name="Нормативы", index=False)

            # Лист 2: Параметры расчёта
            params = {
                "Параметр": [
                    "Станция", "Категория", "Топливо", "Доставка",
                    "Qнр (ккал/кг)", "bее (г/кВт·ч)", "bтэ (кг/Гкал)",
                    "ПГУ/ГТУ",
                    "ННЗТ", "НЭЗТ", "ОНЗТ", "НАЗТ", "НВЗТ",
                ],
                "Значение": [
                    profile.get("name", "—"),
                    "≥25 МВт" if profile.get("category") == "large" else "<25 МВт",
                    FUEL_NAMES.get(profile.get("main_fuel", ""), "—"),
                    DELIVERY_NAMES.get(profile.get("delivery_type", ""), "—"),
                    profile.get("Q_nr", "—"),
                    profile.get("b_ee", "—"),
                    profile.get("b_te", "—"),
                    "Да" if profile.get("has_pgu_gtu") else "Нет",
                    results.get("ННЗТ_тыс_т", results.get("ННЗТ_т", "—")),
                    results.get("НЭЗТ_т", results.get("НЭЗТ_янв_тыс_т", "—")),
                    results.get("ОНЗТ_т", results.get("ОНЗТ_янв_тыс_т", "—")),
                    results.get("НАЗТ_т", results.get("НАЗТ_тыс_т", "—")),
                    results.get("НВЗТ_т", results.get("НВЗТ_тыс_т", "—")),
                ],
            }
            pd.DataFrame(params).to_excel(writer, sheet_name="Параметры", index=False)

        buf.seek(0)
        return buf.read()

    except Exception:
        return None


# ============================================================
# БЫСТРАЯ ПРОВЕРКА
# ============================================================

if __name__ == "__main__":
    from calculations import run_full_calculation

    test_profile = {
        "name": "Тестовая ТЭЦ-1",
        "category": "large",
        "main_fuel": "gas",
        "delivery_type": "pipeline",
        "power_mw": 420,
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
    print(build_report_text(test_profile, res))
    print("\n\n--- MARKDOWN ---\n")
    print(build_report_markdown(test_profile, res))
