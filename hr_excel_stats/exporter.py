# Design Ref: §3.6 — 엑셀(.xlsx) / CSV / 이미지(PNG) 내보내기
"""
exporter.py — HR 통계 결과 내보내기 모듈

다국어 레이블로 Excel, CSV, 차트 PNG를 생성합니다.
모든 함수는 bytes 또는 BytesIO를 반환 → st.download_button에 직접 전달.

Plan SC: 엑셀/CSV 다운로드 정상 작동
Plan SC: 한국어·영어·프랑스어 보고서 내보내기
"""

from __future__ import annotations

import io
from datetime import date
from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from i18n import t


# ══════════════════════════════════════════════════════════════════════════════
# 엑셀 내보내기
# ══════════════════════════════════════════════════════════════════════════════

def to_excel(
    df_clean: pd.DataFrame,
    stats: dict,
    lang: str = "ko",
) -> bytes:
    """
    통계 결과를 다국어 레이블로 Excel 파일 생성.

    시트 구성:
      Sheet1: 인원 현황 요약
      Sheet2: 입퇴사/이직 요약
      Sheet3: 원본 데이터

    Args:
        df_clean:  parser.clean_data() 결과 DataFrame
        stats:     analytics.summary_kpis() 등 통계 결과 dict
        lang:      언어 코드 ("ko" | "en" | "fr")

    Returns:
        bytes (xlsxwriter 엔진)
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        wb = writer.book

        # ── 공통 포맷 ─────────────────────────────────────────────────────
        fmt_title = wb.add_format({
            "bold": True, "font_size": 14,
            "font_color": "#FFFFFF", "bg_color": "#2E86AB",
            "align": "center", "valign": "vcenter",
            "border": 1,
        })
        fmt_header = wb.add_format({
            "bold": True, "font_size": 11,
            "bg_color": "#D6E4F0", "border": 1,
            "align": "center",
        })
        fmt_cell = wb.add_format({"border": 1, "align": "center", "font_size": 11})
        fmt_number = wb.add_format({"border": 1, "align": "center", "num_format": "#,##0"})
        fmt_percent = wb.add_format({"border": 1, "align": "center", "num_format": "0.0%"})

        # ── Sheet 1: 인원 현황 요약 ────────────────────────────────────────
        sheet1 = writer.sheets.get(t("sheet_headcount", lang)) or _add_sheet(
            writer, t("sheet_headcount", lang)
        )
        _write_kpi_sheet(
            sheet1, stats, lang,
            fmt_title, fmt_header, fmt_cell, fmt_number, fmt_percent,
            df_clean
        )

        # ── Sheet 2: 입퇴사/이직 요약 ─────────────────────────────────────
        _write_attrition_sheet(writer, df_clean, stats, lang, fmt_title, fmt_header, fmt_cell, fmt_number)

        # ── Sheet 3: 추가 통계 (Design §6 — G2 fix) ───────────────────────
        _write_additional_sheet(writer, df_clean, lang, fmt_title, fmt_header, fmt_cell, fmt_number)

        # ── Sheet 4: 원본 데이터 ───────────────────────────────────────────
        export_cols = [c for c in df_clean.columns if not c.endswith("_bin")]
        df_export = df_clean[export_cols].copy()
        # 날짜 컬럼 문자열 변환
        for col in ("hire_date", "birth_date", "resign_date"):
            if col in df_export.columns:
                df_export[col] = df_export[col].dt.strftime("%Y-%m-%d")

        df_export.to_excel(writer, sheet_name=t("sheet_raw", lang), index=False)
        raw_sheet = writer.sheets[t("sheet_raw", lang)]
        raw_sheet.set_column(0, len(df_export.columns) - 1, 15)

    output.seek(0)
    return output.read()


def _add_sheet(writer: pd.ExcelWriter, name: str):
    """시트 추가 후 반환."""
    pd.DataFrame().to_excel(writer, sheet_name=name, index=False)
    return writer.sheets[name]


def _write_kpi_sheet(ws, stats: dict, lang: str, fmt_title, fmt_header, fmt_cell, fmt_number, fmt_percent, df_clean):
    """Sheet1: KPI + 부서별/직급별 인원 분포."""
    from analytics import (
        headcount_by_dept, headcount_by_position,
        headcount_by_gender, headcount_by_employment_type,
    )

    # KPI 헤더
    ws.merge_range("A1:D1", t("sheet_headcount", lang), fmt_title)
    ws.set_row(0, 28)

    ws.write("A2", t("total_employees", lang), fmt_header)
    ws.write("B2", t("new_hires", lang), fmt_header)
    ws.write("C2", t("resignations", lang), fmt_header)
    ws.write("D2", t("turnover_rate", lang), fmt_header)

    ws.write_number("A3", stats.get("total_employees", 0), fmt_number)
    ws.write_number("B3", stats.get("new_hires", 0), fmt_number)
    ws.write_number("C3", stats.get("resignations", 0), fmt_number)
    ws.write_number("D3", stats.get("turnover_rate", 0) / 100, fmt_percent)

    ws.set_column("A:D", 18)

    # 부서별 인원
    row = 5
    ws.write(row, 0, t("chart_dept_dist", lang), fmt_header)
    ws.write(row, 1, t("axis_count", lang), fmt_header)
    row += 1
    for dept, cnt in headcount_by_dept(df_clean).items():
        ws.write(row, 0, dept, fmt_cell)
        ws.write_number(row, 1, int(cnt), fmt_number)
        row += 1

    # 직급별 인원
    row += 1
    ws.write(row, 0, t("chart_position_dist", lang), fmt_header)
    ws.write(row, 1, t("axis_count", lang), fmt_header)
    row += 1
    for pos, cnt in headcount_by_position(df_clean).items():
        ws.write(row, 0, str(pos), fmt_cell)
        ws.write_number(row, 1, int(cnt), fmt_number)
        row += 1


def _write_attrition_sheet(writer, df_clean, stats, lang, fmt_title, fmt_header, fmt_cell, fmt_number):
    """Sheet2: 월별 입퇴사 + 부서별 이직률."""
    from analytics import monthly_hire_resign_combined, turnover_by_dept

    sheet_name = t("sheet_attrition", lang)
    pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
    ws = writer.sheets[sheet_name]

    ws.merge_range("A1:C1", t("sheet_attrition", lang), fmt_title)
    ws.set_row(0, 28)
    ws.set_column("A:C", 18)

    # 월별 입퇴사
    monthly = monthly_hire_resign_combined(df_clean)
    row = 1
    ws.write(row, 0, t("axis_year_month", lang), fmt_header)
    ws.write(row, 1, t("series_hire", lang), fmt_header)
    ws.write(row, 2, t("series_resign", lang), fmt_header)
    row += 1
    for _, r in monthly.iterrows():
        ws.write(row, 0, r["year_month"], fmt_cell)
        ws.write_number(row, 1, int(r.get("hire_count", 0)), fmt_number)
        ws.write_number(row, 2, int(r.get("resign_count", 0)), fmt_number)
        row += 1

    # 부서별 이직률
    row += 1
    ws.write(row, 0, t("chart_turnover_by_dept", lang), fmt_header)
    ws.write(row, 1, t("turnover_rate", lang), fmt_header)
    row += 1
    for dept, rate in turnover_by_dept(df_clean).items():
        ws.write(row, 0, dept, fmt_cell)
        ws.write_number(row, 1, float(rate), fmt_number)
        row += 1


def _write_additional_sheet(writer, df_clean, lang: str, fmt_title, fmt_header, fmt_cell, fmt_number):
    """Sheet3: 추가 통계 (조직 구조 + 근속연수/연령 분포). Design §6 G2 fix."""
    from analytics import org_structure_stats, tenure_distribution, headcount_by_age_group

    sheet_name = t("sheet_additional", lang)
    pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
    ws = writer.sheets[sheet_name]

    ws.merge_range("A1:B1", t("sheet_additional", lang), fmt_title)
    ws.set_row(0, 28)
    ws.set_column("A:B", 22)

    row = 1
    # 근속연수 분포
    ws.write(row, 0, t("chart_tenure_dist", lang), fmt_header)
    ws.write(row, 1, t("axis_count", lang), fmt_header)
    row += 1
    for label, cnt in tenure_distribution(df_clean, lang).items():
        ws.write(row, 0, str(label), fmt_cell)
        ws.write_number(row, 1, int(cnt), fmt_number)
        row += 1

    row += 1
    # 연령대 분포
    age_data = headcount_by_age_group(df_clean, lang)
    if not age_data.empty:
        ws.write(row, 0, t("chart_age_dist", lang), fmt_header)
        ws.write(row, 1, t("axis_count", lang), fmt_header)
        row += 1
        for label, cnt in age_data.items():
            ws.write(row, 0, str(label), fmt_cell)
            ws.write_number(row, 1, int(cnt), fmt_number)
            row += 1

    row += 1
    # 조직 구조
    org = org_structure_stats(df_clean)
    if org:
        ws.write(row, 0, t("section_org", lang), fmt_header)
        ws.write(row, 1, t("axis_count", lang), fmt_header)
        row += 1
        if "avg_team_size" in org:
            ws.write(row, 0, "평균 팀 규모" if lang == "ko" else "Avg Team Size", fmt_cell)
            ws.write_number(row, 1, float(org["avg_team_size"]), fmt_number)
            row += 1
        if "avg_span_of_control" in org:
            ws.write(row, 0, "스팬 오브 컨트롤" if lang == "ko" else "Span of Control", fmt_cell)
            ws.write_number(row, 1, float(org["avg_span_of_control"]), fmt_number)
            row += 1


# ══════════════════════════════════════════════════════════════════════════════
# CSV 내보내기
# ══════════════════════════════════════════════════════════════════════════════

def to_csv(df: pd.DataFrame, encoding: str = "utf-8-sig") -> bytes:
    """
    CSV 내보내기.
    utf-8-sig 인코딩으로 한국어 엑셀 호환.

    Args:
        df: 내보낼 DataFrame
        encoding: 기본 utf-8-sig (한국어 엑셀 깨짐 방지)

    Returns:
        bytes
    """
    # 날짜 컬럼 포맷
    df = df.copy()
    for col in ("hire_date", "birth_date", "resign_date"):
        if col in df.columns and pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")

    # _bin 파생 컬럼 제외
    drop_cols = [c for c in df.columns if c.endswith("_bin")]
    df = df.drop(columns=drop_cols, errors="ignore")

    return df.to_csv(index=False, encoding=encoding).encode(encoding)


# ══════════════════════════════════════════════════════════════════════════════
# 차트 HTML 내보내기 (외부 패키지 불필요 — 항상 동작)
# ══════════════════════════════════════════════════════════════════════════════

def charts_to_html(df, lang: str = "ko") -> bytes:
    """
    모든 HR 차트를 인터랙티브 HTML 보고서로 내보내기.

    kaleido 등 외부 패키지 불필요. Plotly.js를 자체 포함(self-contained)하여
    인터넷 연결 없이도 브라우저에서 바로 열 수 있음.

    Args:
        df:   정제된 DataFrame (parser.clean_data 결과)
        lang: 언어 코드 ("ko" | "en" | "fr")

    Returns:
        UTF-8 인코딩된 HTML bytes
    """
    from datetime import date as _date
    from charts import (
        bar_chart, pie_chart, category_bar, line_chart,
        turnover_rate_bar, avg_tenure_bar,
        pyramid_chart, dept_gender_stacked_bar,
    )
    from analytics import (
        headcount_by_dept, headcount_by_gender, headcount_by_age_group,
        tenure_distribution, monthly_hire_resign_combined,
        turnover_by_dept, avg_tenure_by_dept,
        age_gender_pyramid, dept_gender_ratio,
    )

    figs: list[tuple[str, go.Figure]] = []

    # ── 인원 현황 ─────────────────────────────────────────────────────────
    data = headcount_by_dept(df)
    if not data.empty:
        figs.append((t("chart_dept_dist", lang),
                     bar_chart(data, t("chart_dept_dist", lang),
                               y_label=t("axis_count", lang), horizontal=True)))

    data = headcount_by_gender(df, lang)
    if not data.empty:
        figs.append((t("chart_gender_ratio", lang),
                     pie_chart(data, t("chart_gender_ratio", lang))))

    data = headcount_by_age_group(df, lang)
    if not data.empty:
        figs.append((t("chart_age_dist", lang),
                     category_bar(data, t("chart_age_dist", lang),
                                  x_label=t("axis_age", lang), lang=lang)))

    data = tenure_distribution(df, lang)
    if not data.empty:
        figs.append((t("chart_tenure_dist", lang),
                     category_bar(data, t("chart_tenure_dist", lang), lang=lang)))

    # ── 피라미드 / 성비 ───────────────────────────────────────────────────
    pyr = age_gender_pyramid(df, lang)
    if not pyr.empty:
        figs.append((t("chart_age_pyramid", lang),
                     pyramid_chart(pyr, t("chart_age_pyramid", lang), lang=lang)))

    dg = dept_gender_ratio(df, lang)
    if not dg.empty:
        figs.append((t("chart_dept_gender", lang),
                     dept_gender_stacked_bar(dg, t("chart_dept_gender", lang), lang=lang)))

    # ── 입퇴사 ────────────────────────────────────────────────────────────
    monthly = monthly_hire_resign_combined(df)
    if not monthly.empty:
        figs.append((t("chart_monthly_hire", lang),
                     line_chart(monthly, "year_month", ["hire_count", "resign_count"],
                                t("chart_monthly_hire", lang),
                                labels={"hire_count": t("series_hire", lang),
                                        "resign_count": t("series_resign", lang)},
                                lang=lang)))

    tbd = turnover_by_dept(df)
    if not tbd.empty:
        figs.append((t("chart_turnover_by_dept", lang),
                     turnover_rate_bar(tbd, t("chart_turnover_by_dept", lang), lang=lang)))

    atd = avg_tenure_by_dept(df)
    if not atd.empty:
        figs.append((t("chart_avg_tenure_dept", lang),
                     avg_tenure_bar(atd, t("chart_avg_tenure_dept", lang), lang=lang)))

    # ── HTML 조립 ─────────────────────────────────────────────────────────
    today_str = _date.today().strftime("%Y-%m-%d")
    title = t("app_title", lang)

    chart_divs: list[str] = []
    for i, (_, fig) in enumerate(figs):
        # 첫 번째 차트에만 plotly.js 내장 (self-contained), 이후는 재사용
        div = fig.to_html(
            full_html=False,
            include_plotlyjs=(True if i == 0 else False),
            config={"displayModeBar": True, "toImageButtonOptions": {"format": "png", "scale": 2}},
        )
        chart_divs.append(f'<div class="chart-card">{div}</div>')

    grid_html = "\n".join(chart_divs)

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', Arial, sans-serif;
          background: #f0f2f6; padding: 28px; color: #333; }}
  h1   {{ color: #2E86AB; font-size: 22px; margin-bottom: 4px; }}
  .sub {{ color: #888; font-size: 13px; margin-bottom: 24px; }}
  .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }}
  .chart-card {{ background: #fff; border-radius: 10px; padding: 16px;
                 box-shadow: 0 2px 10px rgba(0,0,0,.08); overflow: hidden; }}
  .footer {{ margin-top: 28px; text-align: center; color: #aaa; font-size: 12px; }}
  @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>📊 {title}</h1>
<div class="sub">{today_str} 기준 &nbsp;|&nbsp; HR Excel Statistics Dashboard</div>
<div class="grid">
{grid_html}
</div>
<div class="footer">Generated by HR Excel Statistics Dashboard</div>
</body>
</html>"""

    return html.encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# 차트 PNG 내보내기 — matplotlib 기반 (외부 브라우저 불필요)
# ══════════════════════════════════════════════════════════════════════════════

def summary_png(df, stats: dict, lang: str = "ko") -> bytes:
    """
    KPI 요약 + 주요 차트 2종(부서별 인원 / 성별 비율)을 matplotlib으로 PNG 생성.

    브라우저·kaleido 불필요. matplotlib Agg 백엔드만 사용.

    Args:
        df:    정제된 DataFrame
        stats: summary_kpis() 결과 dict
        lang:  언어 코드

    Returns:
        PNG bytes (300 dpi)
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.gridspec as gridspec
    from analytics import headcount_by_dept, headcount_by_gender, avg_age_by_gender

    # ── 폰트 설정 (한국어 지원) ───────────────────────────────────────────
    import matplotlib.font_manager as fm
    _KO_FONTS = [
        "Malgun Gothic", "NanumGothic", "Apple SD Gothic Neo",
        "Noto Sans KR", "DejaVu Sans",
    ]
    font_found = None
    for fname in _KO_FONTS:
        try:
            fm.findfont(fm.FontProperties(family=fname), fallback_to_default=False)
            font_found = fname
            break
        except Exception:
            continue
    if font_found:
        plt.rcParams["font.family"] = font_found
    plt.rcParams["axes.unicode_minus"] = False

    BLUE  = "#2E86AB"
    PINK  = "#E85D9A"
    RED   = "#C73E1D"
    GRAY  = "#888888"
    BG    = "#F8F9FA"

    fig = plt.figure(figsize=(16, 11), facecolor=BG)
    fig.patch.set_facecolor(BG)

    gs = gridspec.GridSpec(
        3, 3,
        figure=fig,
        hspace=0.55,
        wspace=0.4,
        top=0.90, bottom=0.06, left=0.07, right=0.97,
    )

    # ── 상단: KPI 카드 5종 ────────────────────────────────────────────────
    kpi_items = [
        (t("total_employees", lang), f"{stats.get('total_employees', 0):,}", BLUE),
        (t("new_hires", lang),       f"{stats.get('new_hires', 0):,}",       "#44BBA4"),
        (t("resignations", lang),    f"{stats.get('resignations', 0):,}",    RED),
        (t("turnover_rate", lang),   f"{stats.get('turnover_rate', 0):.1f}%", "#F18F01"),
        (t("avg_tenure", lang),
         f"{stats.get('avg_tenure', 0):.1f} {t('avg_tenure_unit', lang)}", "#7B2D8B"),
    ]

    age_stats = avg_age_by_gender(df)
    if age_stats["all"] > 0:
        kpi_items.append((
            t("avg_age_all", lang),
            f"{age_stats['all']:.1f} {t('age_unit', lang)}", "#3B1F2B",
        ))

    kpi_ax = fig.add_subplot(gs[0, :])
    kpi_ax.set_facecolor(BG)
    kpi_ax.axis("off")

    n = len(kpi_items)
    box_w = 1.0 / n
    for i, (label, value, color) in enumerate(kpi_items):
        cx = (i + 0.5) * box_w
        rect = mpatches.FancyBboxPatch(
            (cx - box_w * 0.43, 0.08), box_w * 0.86, 0.82,
            boxstyle="round,pad=0.02", linewidth=0,
            facecolor=color, transform=kpi_ax.transAxes, zorder=2,
        )
        kpi_ax.add_patch(rect)
        kpi_ax.text(cx, 0.62, value, transform=kpi_ax.transAxes,
                    ha="center", va="center", fontsize=20, fontweight="bold",
                    color="white", zorder=3)
        kpi_ax.text(cx, 0.22, label, transform=kpi_ax.transAxes,
                    ha="center", va="center", fontsize=9.5,
                    color="white", alpha=0.92, zorder=3)

    # ── 중간 왼쪽: 부서별 인원 막대 ──────────────────────────────────────
    ax_dept = fig.add_subplot(gs[1:, :2])
    ax_dept.set_facecolor("white")
    dept = headcount_by_dept(df)
    if not dept.empty:
        dept_sorted = dept.sort_values()
        colors_dept = [BLUE if v == dept_sorted.max() else "#90C4D8" for v in dept_sorted]
        bars = ax_dept.barh(
            [str(d) for d in dept_sorted.index],
            dept_sorted.values,
            color=colors_dept, edgecolor="none", height=0.65,
        )
        for bar, val in zip(bars, dept_sorted.values):
            ax_dept.text(
                bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                str(int(val)), va="center", ha="left", fontsize=9, color=GRAY,
            )
        ax_dept.set_title(t("chart_dept_dist", lang), fontsize=12, fontweight="bold",
                          color="#333", pad=10)
        ax_dept.set_xlabel(t("axis_count", lang), fontsize=9, color=GRAY)
        ax_dept.spines[["top", "right", "left"]].set_visible(False)
        ax_dept.tick_params(axis="y", labelsize=8.5)
        ax_dept.set_facecolor("white")
        ax_dept.xaxis.set_tick_params(labelsize=8)
        ax_dept.set_xlim(0, dept_sorted.max() * 1.18)

    # ── 중간 오른쪽: 성별 파이 ────────────────────────────────────────────
    ax_gender = fig.add_subplot(gs[1, 2])
    ax_gender.set_facecolor(BG)
    gender = headcount_by_gender(df, lang)
    if not gender.empty:
        # headcount_by_gender already returns translated labels; map colours by label
        _male_label   = t("gender_male", lang)
        _female_label = t("gender_female", lang)
        labels_g = gender.index.tolist()
        clrs = [
            BLUE if g == _male_label else PINK if g == _female_label else "#AAAAAA"
            for g in labels_g
        ]
        wedges, texts, autotexts = ax_gender.pie(
            gender.values, labels=labels_g, colors=clrs,
            autopct="%1.1f%%", startangle=90,
            textprops={"fontsize": 9},
            pctdistance=0.75,
        )
        for at in autotexts:
            at.set_fontsize(8.5)
            at.set_color("white")
            at.set_fontweight("bold")
        ax_gender.set_title(t("chart_gender_ratio", lang), fontsize=11,
                            fontweight="bold", color="#333", pad=8)

    # ── 우하단: 근속연수 분포 ─────────────────────────────────────────────
    from analytics import tenure_distribution
    ax_tenure = fig.add_subplot(gs[2, 2])
    ax_tenure.set_facecolor(BG)
    tenure = tenure_distribution(df, lang)
    if not tenure.empty:
        t_colors = [BLUE if v == tenure.max() else "#90C4D8" for v in tenure]
        ax_tenure.bar(range(len(tenure)), tenure.values, color=t_colors, edgecolor="none")
        ax_tenure.set_xticks(range(len(tenure)))
        ax_tenure.set_xticklabels(tenure.index.tolist(), fontsize=7.5, rotation=15, ha="right")
        ax_tenure.set_title(t("chart_tenure_dist", lang), fontsize=11,
                            fontweight="bold", color="#333", pad=8)
        ax_tenure.set_ylabel(t("axis_count", lang), fontsize=8, color=GRAY)
        ax_tenure.spines[["top", "right"]].set_visible(False)
        ax_tenure.tick_params(axis="y", labelsize=8)

    # ── 제목 ──────────────────────────────────────────────────────────────
    from datetime import date as _date
    fig.suptitle(
        f"{t('app_title', lang)}  ·  {_date.today().strftime('%Y-%m-%d')}",
        fontsize=15, fontweight="bold", color="#2E86AB", y=0.97,
    )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def custom_report_html(
    df: pd.DataFrame,
    sections: list,
    lang: str = "ko",
    company_name: str = "",
) -> bytes:
    """
    사용자가 선택한 섹션만 포함하는 맞춤형 HTML 보고서 생성.

    Args:
        df:           정제된 DataFrame
        sections:     포함할 섹션 키 리스트
                      ['kpi','headcount','attrition','yoy','forecast','cohort','di','risk']
        lang:         언어 코드
        company_name: 보고서 헤더에 표시할 회사/팀명

    Returns:
        UTF-8 HTML bytes (self-contained, plotly.js 내장)
    """
    from datetime import date as _date
    from charts import (
        bar_chart, pie_chart, line_chart, category_bar,
        turnover_rate_bar, avg_tenure_bar,
        pyramid_chart, dept_gender_stacked_bar,
        risk_donut_chart, risk_by_dept_chart,
        yoy_bar_line_chart, yoy_turnover_chart, yoy_dept_trend_chart,
        forecast_chart, cohort_heatmap, cohort_survival_chart,
        di_gender_balance_chart, di_position_heatmap,
    )
    from analytics import (
        summary_kpis,
        headcount_by_dept, headcount_by_gender, headcount_by_age_group,
        tenure_distribution, monthly_hire_resign_combined,
        turnover_by_dept, avg_tenure_by_dept,
        age_gender_pyramid, dept_gender_ratio,
        attrition_risk_scores, risk_summary, risk_by_dept,
        yoy_summary, yoy_dept_headcount,
        headcount_forecast, cohort_retention,
        di_gender_balance, di_position_gender_matrix,
        avg_age_by_gender,
    )

    import html as _html
    today_str = _date.today().strftime("%Y-%m-%d")
    title = t("app_title", lang)
    company_str = f"  ·  {_html.escape(company_name)}" if company_name.strip() else ""

    # ── 섹션별 차트 수집 ─────────────────────────────────────────────────────
    # (section_key, section_title, [(chart_title, fig), ...])
    blocks: list[tuple[str, str, list]] = []
    plotlyjs_inserted = False

    def _fig_html(fig) -> str:
        nonlocal plotlyjs_inserted
        include_js = not plotlyjs_inserted
        plotlyjs_inserted = True
        return fig.to_html(
            full_html=False,
            include_plotlyjs=include_js,
            config={"displayModeBar": True,
                    "toImageButtonOptions": {"format": "png", "scale": 2}},
        )

    # KPI 섹션 (special: rendered as metric cards, not plotly)
    kpis = summary_kpis(df)

    if "kpi" in sections:
        age_s = avg_age_by_gender(df)
        kpi_items = [
            (t("total_employees", lang), f"{kpis.get('total_employees', 0):,}",    "#2E86AB"),
            (t("new_hires", lang),       f"{kpis.get('new_hires', 0):,}",          "#44BBA4"),
            (t("resignations", lang),    f"{kpis.get('resignations', 0):,}",       "#C73E1D"),
            (t("turnover_rate", lang),   f"{kpis.get('turnover_rate', 0):.1f}%",   "#F18F01"),
            (t("avg_tenure", lang),      f"{kpis.get('avg_tenure', 0):.1f} {t('avg_tenure_unit', lang)}", "#7B2D8B"),
        ]
        if age_s.get("all", 0) > 0:
            kpi_items.append((t("avg_age_all", lang), f"{age_s['all']:.1f} {t('age_unit', lang)}", "#3B1F2B"))

        kpi_cards_html = "".join(
            f'<div class="kpi-card" style="border-top:4px solid {c}">'
            f'<div class="kpi-val">{v}</div><div class="kpi-lbl">{lbl}</div></div>'
            for lbl, v, c in kpi_items
        )
        blocks.append(("kpi", t("tab_dashboard", lang),
                        [("__kpi__", kpi_cards_html)]))

    if "headcount" in sections:
        charts = []
        d = headcount_by_dept(df)
        if not d.empty:
            charts.append((t("chart_dept_dist", lang),
                           bar_chart(d, t("chart_dept_dist", lang),
                                     y_label=t("axis_count", lang), horizontal=True)))
        d = headcount_by_gender(df, lang)
        if not d.empty:
            charts.append((t("chart_gender_ratio", lang),
                           pie_chart(d, t("chart_gender_ratio", lang))))
        d = headcount_by_age_group(df, lang)
        if not d.empty:
            charts.append((t("chart_age_dist", lang),
                           category_bar(d, t("chart_age_dist", lang),
                                        x_label=t("axis_age", lang), lang=lang)))
        d = tenure_distribution(df, lang)
        if not d.empty:
            charts.append((t("chart_tenure_dist", lang),
                           category_bar(d, t("chart_tenure_dist", lang), lang=lang)))
        pyr = age_gender_pyramid(df, lang)
        if not pyr.empty:
            charts.append((t("chart_age_pyramid", lang),
                           pyramid_chart(pyr, t("chart_age_pyramid", lang), lang=lang)))
        if charts:
            blocks.append(("headcount", t("tab_headcount", lang), charts))

    if "attrition" in sections:
        charts = []
        monthly = monthly_hire_resign_combined(df)
        if not monthly.empty:
            charts.append((t("chart_monthly_hire", lang),
                           line_chart(monthly, "year_month", ["hire_count", "resign_count"],
                                      t("chart_monthly_hire", lang),
                                      labels={"hire_count": t("series_hire", lang),
                                              "resign_count": t("series_resign", lang)},
                                      lang=lang)))
        tbd = turnover_by_dept(df)
        if not tbd.empty:
            charts.append((t("chart_turnover_by_dept", lang),
                           turnover_rate_bar(tbd, t("chart_turnover_by_dept", lang), lang=lang)))
        atd = avg_tenure_by_dept(df)
        if not atd.empty:
            charts.append((t("chart_avg_tenure_dept", lang),
                           avg_tenure_bar(atd, t("chart_avg_tenure_dept", lang), lang=lang)))
        if charts:
            blocks.append(("attrition", t("tab_attrition", lang), charts))

    if "yoy" in sections:
        charts = []
        yoy = yoy_summary(df)
        if not yoy.empty:
            charts.append((t("chart_yoy_overview", lang),
                           yoy_bar_line_chart(yoy, t("chart_yoy_overview", lang), lang=lang)))
            charts.append((t("chart_yoy_turnover", lang),
                           yoy_turnover_chart(yoy, t("chart_yoy_turnover", lang), lang=lang)))
        yoy_dept = yoy_dept_headcount(df)
        if not yoy_dept.empty:
            charts.append((t("chart_yoy_dept", lang),
                           yoy_dept_trend_chart(yoy_dept, t("chart_yoy_dept", lang), lang=lang)))
        if charts:
            blocks.append(("yoy", t("tab_yoy", lang), charts))

    if "forecast" in sections:
        fdf = headcount_forecast(df, months_ahead=6)
        if not fdf.empty:
            blocks.append(("forecast", t("tab_forecast", lang),
                           [(t("chart_forecast", lang),
                             forecast_chart(fdf, t("chart_forecast", lang), lang=lang))]))

    if "cohort" in sections:
        cdf = cohort_retention(df)
        if not cdf.empty:
            blocks.append(("cohort", t("tab_cohort", lang), [
                (t("chart_cohort_heatmap", lang),
                 cohort_heatmap(cdf, t("chart_cohort_heatmap", lang), lang=lang)),
                (t("chart_cohort_survival", lang),
                 cohort_survival_chart(cdf, t("chart_cohort_survival", lang), lang=lang)),
            ]))

    if "di" in sections:
        charts = []
        bdf = di_gender_balance(df)
        if not bdf.empty:
            charts.append((t("chart_di_gender_balance", lang),
                           di_gender_balance_chart(bdf, t("chart_di_gender_balance", lang), lang=lang)))
        mat = di_position_gender_matrix(df)
        if not mat.empty:
            charts.append((t("chart_di_position_heatmap", lang),
                           di_position_heatmap(mat, t("chart_di_position_heatmap", lang), lang=lang)))
        if charts:
            blocks.append(("di", t("tab_di", lang), charts))

    if "risk" in sections:
        risk_df = attrition_risk_scores(df)
        if not risk_df.empty:
            summary = risk_summary(risk_df)
            drd = risk_by_dept(risk_df)
            charts = [
                (t("chart_risk_dist", lang),
                 risk_donut_chart(summary, t("chart_risk_dist", lang), lang=lang)),
            ]
            if not drd.empty:
                charts.append((t("chart_risk_by_dept", lang),
                               risk_by_dept_chart(drd, t("chart_risk_by_dept", lang), lang=lang)))
            blocks.append(("risk", t("tab_risk", lang), charts))

    # ── HTML 조립 ─────────────────────────────────────────────────────────────
    section_htmls: list[str] = []
    for sec_key, sec_title, items in blocks:
        inner = ""
        for chart_title, content in items:
            if chart_title == "__kpi__":
                inner += f'<div class="kpi-grid">{content}</div>'
            else:
                inner += (
                    f'<div class="chart-card">'
                    f'<div class="chart-title">{chart_title}</div>'
                    f'{_fig_html(content)}'
                    f'</div>'
                )
        section_htmls.append(
            f'<section class="section">'
            f'<h2 class="section-title">{sec_title}</h2>'
            f'<div class="chart-grid">{inner}</div>'
            f'</section>'
        )

    body = "\n".join(section_htmls)

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}{company_str}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Malgun Gothic','Apple SD Gothic Neo',Arial,sans-serif;
       background:#f0f2f6;padding:32px;color:#333}}
  .report-header{{background:linear-gradient(135deg,#2E86AB,#1a5276);
                  color:#fff;border-radius:12px;padding:28px 32px;margin-bottom:28px}}
  .report-header h1{{font-size:24px;margin-bottom:6px}}
  .report-header .meta{{font-size:13px;opacity:.85}}
  .section{{background:#fff;border-radius:10px;padding:24px;
            margin-bottom:24px;box-shadow:0 2px 10px rgba(0,0,0,.07)}}
  .section-title{{font-size:17px;font-weight:700;color:#2E86AB;
                  border-left:4px solid #2E86AB;padding-left:10px;margin-bottom:18px}}
  .chart-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}}
  .chart-card{{background:#f8f9fa;border-radius:8px;padding:12px;overflow:hidden}}
  .chart-title{{font-size:13px;font-weight:600;color:#555;margin-bottom:8px}}
  .kpi-grid{{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:4px}}
  .kpi-card{{background:#f8f9fa;border-radius:8px;padding:16px 20px;min-width:140px;flex:1}}
  .kpi-val{{font-size:22px;font-weight:700;color:#333;margin-bottom:4px}}
  .kpi-lbl{{font-size:11px;color:#888}}
  .footer{{text-align:center;color:#bbb;font-size:12px;margin-top:28px}}
  @media(max-width:900px){{.chart-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="report-header">
  <h1>📊 {title}{company_str}</h1>
  <div class="meta">{today_str} &nbsp;·&nbsp; HR Excel Statistics Dashboard</div>
</div>
{body}
<div class="footer">Generated by HR Excel Statistics Dashboard &nbsp;·&nbsp; {today_str}</div>
</body>
</html>"""

    return html.encode("utf-8")


def chart_to_png(fig: go.Figure, scale: float = 2.0) -> Optional[bytes]:
    """Plotly 차트 PNG — kaleido 기반. 실패 시 None 반환 (내부 호환용)."""
    try:
        return fig.to_image(format="png", scale=scale)
    except Exception:
        return None


def filename_with_date(base: str, ext: str, lang: str = "ko") -> str:
    """
    날짜 포함 파일명 생성.
    예: "hr_report_20260414.xlsx"
    """
    today = date.today().strftime("%Y%m%d")
    return f"{base}_{today}.{ext}"


# ══════════════════════════════════════════════════════════════════════════════
# PDF 보고서 내보내기
# ══════════════════════════════════════════════════════════════════════════════

def _load_korean_font() -> Optional[str]:
    """Windows/Mac/Linux 시스템에서 한국어 지원 폰트 경로 반환."""
    import os
    candidates = [
        r"C:\Windows\Fonts\malgun.ttf",           # Windows Malgun Gothic
        r"C:\Windows\Fonts\malgunbd.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo-Regular.ttc",  # macOS
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _mpl_hbar(labels: list, values: list, title: str,
               color: str = "#2E86AB", max_items: int = 12) -> bytes:
    """수평 막대그래프 → PNG bytes (matplotlib Agg)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = labels[:max_items]
    values = values[:max_items]
    n = len(labels)
    height = max(2.5, n * 0.38)

    fig, ax = plt.subplots(figsize=(7.5, height))
    fig.patch.set_facecolor("white")
    bars = ax.barh(labels, values, color=color, alpha=0.88, height=0.6)
    ax.bar_label(bars, fmt="%.0f", padding=4, fontsize=9, color="#333")
    ax.set_xlabel("", fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10, color="#1a2d42")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=9)
    ax.set_facecolor("#f8fafc")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _mpl_pie(labels: list, values: list, title: str,
             colors: Optional[list] = None) -> bytes:
    """도넛 파이차트 → PNG bytes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _C = ["#2E86AB", "#A23B72", "#F18F01", "#44BBA4", "#C73E1D", "#7B2D8B"]
    colors = colors or _C[:len(labels)]

    fig, ax = plt.subplots(figsize=(5, 3.8))
    fig.patch.set_facecolor("white")
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors,
        autopct="%1.1f%%", startangle=90,
        wedgeprops=dict(width=0.55),
        textprops=dict(fontsize=9),
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_title(title, fontsize=11, fontweight="bold", pad=12, color="#1a2d42")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _mpl_line(x: list, y: list, title: str,
              color: str = "#2E86AB", ylabel: str = "") -> bytes:
    """라인 차트 → PNG bytes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.5, 3.0))
    fig.patch.set_facecolor("white")
    ax.plot(x, y, color=color, linewidth=2, marker="o", markersize=5)
    ax.fill_between(x, y, alpha=0.12, color=color)
    ax.set_title(title, fontsize=11, fontweight="bold", pad=10, color="#1a2d42")
    ax.set_ylabel(ylabel, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_facecolor("#f8fafc")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def to_pdf(
    df: pd.DataFrame,
    lang: str = "ko",
    company_name: str = "",
    start_date: str = "",
    end_date: str = "",
) -> bytes:
    """
    HR 통계 PDF 보고서 생성.

    Args:
        df:           정제된 DataFrame (parser.clean_data 결과)
        lang:         언어 코드 ("ko" | "en" | "fr")
        company_name: 표지에 표시할 회사명
        start_date:   기간 시작 (YYYY-MM)
        end_date:     기간 종료 (YYYY-MM)

    Returns:
        bytes (PDF)
    """
    from fpdf import FPDF
    from analytics import (
        summary_kpis, headcount_by_dept, headcount_by_gender,
        headcount_by_age_group, tenure_distribution,
        monthly_hire_resign_combined, turnover_by_dept,
        resign_reason_breakdown, tth_kpi, _tth_source_col,
    )

    # ── 색상 상수 ─────────────────────────────────────────────────────────
    C_PRIMARY   = (46, 134, 171)    # #2E86AB
    C_SECONDARY = (68, 187, 164)    # #44BBA4
    C_ACCENT    = (241, 143, 1)     # #F18F01
    C_DARK      = (26, 45, 66)      # #1a2d42
    C_LIGHT     = (240, 244, 248)   # #f0f4f8
    C_WHITE     = (255, 255, 255)
    C_GRAY      = (140, 150, 160)

    # ── i18n 레이블 (PDF에서 사용) ─────────────────────────────────────────
    L = {
        "ko": {
            "report_title": "HR 통계 보고서",
            "period":       "분석 기간",
            "generated":    "생성일",
            "kpi_title":    "핵심 지표 요약",
            "total_emp":    "전체 재직 인원",
            "new_hires":    "입사자",
            "resigned":     "퇴사자",
            "turnover":     "이직률",
            "avg_tenure":   "평균 근속",
            "headcount":    "인원 현황",
            "by_dept":      "부서별 인원",
            "by_gender":    "성별 비율",
            "by_age":       "연령대별 인원",
            "by_tenure":    "근속연수 분포",
            "attrition":    "입퇴사 현황",
            "monthly":      "월별 입퇴사 추이",
            "by_dept_turn": "부서별 퇴사자",
            "resign_reason":"퇴사 사유",
            "tth_title":    "채용 소요시간",
            "tth_avg":      "평균",
            "tth_median":   "중앙값",
            "tth_min":      "최단",
            "tth_max":      "최장",
            "tth_n":        "분석 건수",
            "days":         "일",
            "ppl":          "명",
            "yr":           "년",
            "confidential": "대외비",
            "page":         "페이지",
        },
        "en": {
            "report_title": "HR Statistics Report",
            "period":       "Analysis Period",
            "generated":    "Generated",
            "kpi_title":    "Key Metrics Summary",
            "total_emp":    "Total Employees",
            "new_hires":    "New Hires",
            "resigned":     "Resignations",
            "turnover":     "Turnover Rate",
            "avg_tenure":   "Avg. Tenure",
            "headcount":    "Headcount",
            "by_dept":      "By Department",
            "by_gender":    "By Gender",
            "by_age":       "By Age Group",
            "by_tenure":    "Tenure Distribution",
            "attrition":    "Attrition",
            "monthly":      "Monthly Hire / Resign Trend",
            "by_dept_turn": "Resignations by Dept",
            "resign_reason":"Resignation Reasons",
            "tth_title":    "Time-to-Hire",
            "tth_avg":      "Avg",
            "tth_median":   "Median",
            "tth_min":      "Fastest",
            "tth_max":      "Slowest",
            "tth_n":        "Hires Analyzed",
            "days":         "days",
            "ppl":          "ppl",
            "yr":           "yr",
            "confidential": "Confidential",
            "page":         "Page",
        },
        "fr": {
            "report_title": "Rapport RH Statistiques",
            "period":       "Période d'analyse",
            "generated":    "Généré le",
            "kpi_title":    "Résumé des indicateurs clés",
            "total_emp":    "Effectif total",
            "new_hires":    "Nouvelles embauches",
            "resigned":     "Départs",
            "turnover":     "Taux de rotation",
            "avg_tenure":   "Ancienneté moy.",
            "headcount":    "Effectifs",
            "by_dept":      "Par département",
            "by_gender":    "Par genre",
            "by_age":       "Par tranche d'âge",
            "by_tenure":    "Distribution ancienneté",
            "attrition":    "Entrées / Sorties",
            "monthly":      "Évolution mensuelle",
            "by_dept_turn": "Départs par département",
            "resign_reason":"Motifs de départ",
            "tth_title":    "Délai de recrutement",
            "tth_avg":      "Moy.",
            "tth_median":   "Médiane",
            "tth_min":      "Le plus rapide",
            "tth_max":      "Le plus long",
            "tth_n":        "Recrutements analysés",
            "days":         "j",
            "ppl":          "pers.",
            "yr":           "an",
            "confidential": "Confidentiel",
            "page":         "Page",
        },
    }
    lbl = L.get(lang, L["en"])

    # ── FPDF 서브클래스: 헤더·푸터 ────────────────────────────────────────
    class HRReport(FPDF):
        def __init__(self, font_name: str, lbl: dict, company: str):
            super().__init__(orientation="P", unit="mm", format="A4")
            self.font_name = font_name
            self.lbl = lbl
            self.company = company
            self.set_auto_page_break(auto=True, margin=20)

        def header(self):
            if self.page_no() == 1:
                return  # 표지는 별도 처리
            # 상단 파란 바
            self.set_fill_color(*C_PRIMARY)
            self.rect(0, 0, 210, 10, "F")
            self.set_font(self.font_name, "B", 8)
            self.set_text_color(*C_WHITE)
            self.set_y(2)
            self.cell(0, 6, self.lbl["report_title"], align="C")
            self.set_text_color(*C_DARK)
            self.ln(8)

        def footer(self):
            if self.page_no() == 1:
                return
            self.set_y(-15)
            self.set_draw_color(*C_PRIMARY)
            self.set_line_width(0.3)
            self.line(15, self.get_y(), 195, self.get_y())
            self.set_font(self.font_name, "", 7)
            self.set_text_color(*C_GRAY)
            self.cell(0, 8,
                      f"{self.lbl['confidential']}  |  {self.company}  |  "
                      f"{self.lbl['page']} {self.page_no()}",
                      align="C")

        def section_title(self, txt: str, color=C_PRIMARY):
            self.set_fill_color(*color)
            self.set_text_color(*C_WHITE)
            self.set_font(self.font_name, "B", 12)
            self.cell(0, 9, f"  {txt}", ln=True, fill=True)
            self.set_text_color(*C_DARK)
            self.ln(3)

        def kpi_table(self, rows: list[tuple[str, str]]):
            """rows: [(label, value), ...]  2열 레이아웃."""
            col_w = 85
            row_h = 12
            for i, (label, value) in enumerate(rows):
                fill = i % 2 == 0
                self.set_fill_color(*C_LIGHT) if fill else self.set_fill_color(*C_WHITE)
                self.set_font(self.font_name, "", 10)
                self.set_text_color(*C_GRAY)
                self.cell(col_w, row_h, f"  {label}", border=0, fill=True)
                self.set_font(self.font_name, "B", 11)
                self.set_text_color(*C_PRIMARY)
                self.cell(col_w, row_h, value, border=0, fill=True, ln=True)
                self.set_text_color(*C_DARK)
            self.ln(4)

        def embed_image(self, img_bytes: bytes, w: float = 170):
            buf = io.BytesIO(img_bytes)
            x = (210 - w) / 2
            self.image(buf, x=x, w=w)
            self.ln(4)

        def embed_two_images(self, img1: bytes, img2: bytes, w: float = 82):
            buf1, buf2 = io.BytesIO(img1), io.BytesIO(img2)
            self.image(buf1, x=15, w=w)
            self.set_xy(15 + w + 6, self.get_y() - self.image(buf2, x=15 + w + 6, w=w, dry_run=True).rendered_page_break_height if hasattr(self, '_last_h') else self.get_y())
            # simpler: place both side by side using absolute x
            self.set_y(self.get_y())
            self.ln(2)

    # ── 폰트 로드 ─────────────────────────────────────────────────────────
    font_path = _load_korean_font()
    pdf = HRReport(font_name="helvetica", lbl=lbl, company=company_name)

    if font_path:
        try:
            pdf.add_font("KRFont", fname=font_path, uni=True)
            pdf.add_font("KRFont", style="B", fname=font_path, uni=True)
            pdf.font_name = "KRFont"
        except Exception:
            pass

    fn = pdf.font_name  # shorthand

    # ── 데이터 준비 ───────────────────────────────────────────────────────
    kpis       = summary_kpis(df)
    dept_ser   = headcount_by_dept(df)
    gender_ser = headcount_by_gender(df, lang)
    age_ser    = headcount_by_age_group(df, lang)
    tenure_ser = tenure_distribution(df, lang)
    monthly_df = monthly_hire_resign_combined(df)
    turnover_dept = turnover_by_dept(df)
    resign_ser = resign_reason_breakdown(df)
    tth_data   = tth_kpi(df)
    tth_src    = _tth_source_col(df)

    today_str  = date.today().strftime("%Y-%m-%d")
    period_str = f"{start_date} ~ {end_date}" if start_date else ""

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 1: 표지
    # ══════════════════════════════════════════════════════════════════════
    pdf.add_page()

    # 상단 색상 블록
    pdf.set_fill_color(*C_PRIMARY)
    pdf.rect(0, 0, 210, 80, "F")

    # 로고 영역 (흰 원)
    pdf.set_fill_color(*C_WHITE)
    pdf.ellipse(85, 18, 40, 40, "F")
    pdf.set_font(fn, "B", 20)
    pdf.set_text_color(*C_PRIMARY)
    pdf.set_xy(85, 28)
    pdf.cell(40, 20, "HR", align="C")

    # 제목
    pdf.set_font(fn, "B", 24)
    pdf.set_text_color(*C_WHITE)
    pdf.set_xy(15, 68)
    pdf.cell(180, 12, lbl["report_title"], align="C")

    # 회사명
    pdf.set_font(fn, "", 14)
    pdf.set_text_color(*C_WHITE)
    pdf.set_xy(15, 82)
    pdf.cell(180, 10, company_name, align="C")

    # 구분선
    pdf.set_draw_color(*C_SECONDARY)
    pdf.set_line_width(1.0)
    pdf.line(60, 105, 150, 105)

    # 날짜 및 기간
    pdf.set_font(fn, "", 11)
    pdf.set_text_color(*C_DARK)
    pdf.set_xy(15, 112)
    if period_str:
        pdf.cell(180, 8, f"{lbl['period']}: {period_str}", align="C")
        pdf.ln(8)
        pdf.cell(180, 8, f"{lbl['generated']}: {today_str}", align="C")
    else:
        pdf.cell(180, 8, f"{lbl['generated']}: {today_str}", align="C")

    # 하단 기밀 라벨
    pdf.set_font(fn, "", 9)
    pdf.set_text_color(*C_GRAY)
    pdf.set_xy(15, 270)
    pdf.cell(180, 8, lbl["confidential"], align="C")

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 2: KPI 요약
    # ══════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title(f"01  {lbl['kpi_title']}")

    kpi_rows = [
        (lbl["total_emp"],  f"{kpis.get('total_employees', 0):,} {lbl['ppl']}"),
        (lbl["new_hires"],  f"{kpis.get('new_hires', 0):,} {lbl['ppl']}"),
        (lbl["resigned"],   f"{kpis.get('resignations', 0):,} {lbl['ppl']}"),
        (lbl["turnover"],   f"{kpis.get('turnover_rate', 0):.1f} %"),
        (lbl["avg_tenure"], f"{kpis.get('avg_tenure', 0):.1f} {lbl['yr']}"),
    ]
    if tth_src and tth_data.get("n", 0) > 0:
        kpi_rows += [
            (f"{lbl['tth_avg']} TTH", f"{tth_data['avg']} {lbl['days']}"),
            (f"{lbl['tth_median']} TTH", f"{tth_data['median']} {lbl['days']}"),
        ]
    pdf.kpi_table(kpi_rows)

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 3: 인원 현황
    # ══════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title(f"02  {lbl['headcount']}")

    if not dept_ser.empty:
        img_dept = _mpl_hbar(
            dept_ser.index.tolist(), dept_ser.values.tolist(),
            lbl["by_dept"], "#2E86AB",
        )
        pdf.embed_image(img_dept, w=160)

    # 성별 + 연령대 나란히
    imgs = []
    if not gender_ser.empty:
        imgs.append(_mpl_pie(
            gender_ser.index.tolist(), gender_ser.values.tolist(),
            lbl["by_gender"],
        ))
    if not age_ser.empty:
        imgs.append(_mpl_hbar(
            age_ser.index.tolist(), age_ser.values.tolist(),
            lbl["by_age"], "#44BBA4",
        ))

    if len(imgs) == 2:
        y0 = pdf.get_y()
        pdf.image(io.BytesIO(imgs[0]), x=15,  y=y0, w=82)
        pdf.image(io.BytesIO(imgs[1]), x=110, y=y0, w=82)
        pdf.set_y(y0 + 60)
    elif len(imgs) == 1:
        pdf.embed_image(imgs[0], w=140)

    # 근속연수
    if not tenure_ser.empty:
        pdf.add_page()
        pdf.section_title(f"02  {lbl['by_tenure']}", color=C_SECONDARY)
        img_ten = _mpl_hbar(
            tenure_ser.index.tolist(), tenure_ser.values.tolist(),
            lbl["by_tenure"], "#F18F01",
        )
        pdf.embed_image(img_ten, w=150)

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 4: 입퇴사 현황
    # ══════════════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.section_title(f"03  {lbl['attrition']}")

    if not monthly_df.empty:
        months = monthly_df["year_month"].tolist()
        joins  = monthly_df["join"].tolist() if "join" in monthly_df.columns else []
        leaves = monthly_df["leave"].tolist() if "leave" in monthly_df.columns else []
        if joins:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(7.5, 3.2))
            fig.patch.set_facecolor("white")
            x = range(len(months))
            w = 0.38
            ax.bar([i - w/2 for i in x], joins,  width=w, color="#2E86AB",
                   alpha=0.85, label="Join")
            ax.bar([i + w/2 for i in x], leaves, width=w, color="#C73E1D",
                   alpha=0.85, label="Leave")
            ax.set_xticks(list(x))
            ax.set_xticklabels(months, rotation=45, ha="right", fontsize=7)
            ax.set_title(lbl["monthly"], fontsize=11, fontweight="bold",
                         color="#1a2d42", pad=10)
            ax.legend(fontsize=9)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_facecolor("#f8fafc")
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            pdf.embed_image(buf.read(), w=160)

    if not resign_ser.empty:
        img_reason = _mpl_pie(
            resign_ser.index.tolist()[:6],
            resign_ser.values.tolist()[:6],
            lbl["resign_reason"],
        )
        pdf.embed_image(img_reason, w=120)

    # ══════════════════════════════════════════════════════════════════════
    # PAGE 5: 채용 소요시간 (데이터 있을 때만)
    # ══════════════════════════════════════════════════════════════════════
    if tth_src and tth_data.get("n", 0) > 0:
        from analytics import tth_series as _tth_series, tth_by_department as _tth_dept
        pdf.add_page()
        pdf.section_title(f"04  {lbl['tth_title']}")

        tth_kpi_rows = [
            (lbl["tth_avg"],    f"{tth_data['avg']} {lbl['days']}"),
            (lbl["tth_median"], f"{tth_data['median']} {lbl['days']}"),
            (lbl["tth_min"],    f"{tth_data['min']} {lbl['days']}"),
            (lbl["tth_max"],    f"{tth_data['max']} {lbl['days']}"),
            (lbl["tth_n"],      f"{tth_data['n']:,} {lbl['ppl']}"),
        ]
        pdf.kpi_table(tth_kpi_rows)

        # TTH 분포 히스토그램
        tth_s = _tth_series(df)
        if not tth_s.empty:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(7.5, 3.0))
            fig.patch.set_facecolor("white")
            ax.hist(tth_s, bins=15, color="#2E86AB", alpha=0.80, edgecolor="white")
            ax.axvline(tth_s.mean(), color="#F18F01", linewidth=1.8,
                       linestyle="--", label=f"{lbl['tth_avg']}: {tth_s.mean():.1f}{lbl['days']}")
            ax.set_xlabel(f"{lbl['tth_avg']} ({lbl['days']})", fontsize=9)
            ax.set_title(lbl["tth_title"], fontsize=11, fontweight="bold",
                         color="#1a2d42", pad=10)
            ax.legend(fontsize=9)
            ax.spines[["top", "right"]].set_visible(False)
            ax.set_facecolor("#f8fafc")
            fig.tight_layout()
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            pdf.embed_image(buf.read(), w=155)

        # TTH by dept
        dept_tth = _tth_dept(df)
        if not dept_tth.empty:
            img_tth_dept = _mpl_hbar(
                dept_tth["department"].tolist(),
                dept_tth["avg"].tolist(),
                lbl["by_dept"], "#A23B72",
            )
            pdf.embed_image(img_tth_dept, w=150)

    # ── 출력 ──────────────────────────────────────────────────────────────
    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()
