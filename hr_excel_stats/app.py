# Design Ref: §3.7 — Streamlit 진입점 + 페이지 라우팅 + 언어 선택
"""
app.py — HR Excel 통계 앱 메인

실행 방법:
    streamlit run app.py

Plan SC: 엑셀 업로드 후 30초 내 대시보드 표시
Plan SC: 한국어 UI 전체 적용
"""

import streamlit as st
import pandas as pd

from config import SUPPORTED_LANGUAGES, LANGUAGE_CODES, APP_CONFIG
from i18n import t
from parser import (
    load_file, detect_columns, validate_mapping,
    clean_data, get_date_range, get_departments,
    get_column_mapping_summary, filter_by_date_range, filter_by_department,
)
from analytics import (
    summary_kpis,
    headcount_by_dept, headcount_by_position, headcount_by_gender,
    headcount_by_age_group, headcount_by_employment_type, tenure_distribution,
    age_gender_pyramid, avg_age_by_gender, dept_gender_ratio,
    short_tenure_ratio, position_age_tenure_stats,
    monthly_hire_resign_combined, turnover_by_dept, avg_tenure_by_dept,
    resign_reason_breakdown, turnover_rate, avg_tenure,
    attrition_risk_scores, risk_summary, risk_by_dept,
    has_column,
    yoy_summary, yoy_dept_headcount,
    dept_detail,
    headcount_forecast,
    cohort_retention,
    di_gender_balance, di_age_diversity, di_position_gender_matrix,
    # 채용 소요시간
    tth_kpi, tth_series, tth_by_department,
    tth_by_position, tth_trend_monthly, _tth_source_col,
)
from charts import (
    bar_chart, pie_chart, line_chart, category_bar,
    turnover_rate_bar, avg_tenure_bar, histogram_chart,
    pyramid_chart, dept_gender_stacked_bar,
    risk_donut_chart, risk_by_dept_chart, risk_scatter_chart,
    yoy_bar_line_chart, yoy_turnover_chart, yoy_dept_trend_chart,
    forecast_chart,
    cohort_heatmap, cohort_survival_chart,
    di_gender_balance_chart, di_position_heatmap,
    # 채용 소요시간
    tth_histogram, tth_by_dept_chart,
    tth_trend_chart, tth_by_position_chart,
)
from exporter import to_excel, to_csv, chart_to_png, charts_to_html, summary_png, filename_with_date, custom_report_html, to_pdf

# ── 페이지 설정 ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HR Statistics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 글로벌 CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════════════
   HR Dashboard — Global Design System
   ▸ Uses Streamlit CSS variables → works in both light & dark mode
   ▸ Accent: #2E86AB  |  Font: Inter / system stack
   ═══════════════════════════════════════════════════════════════════════ */

/* ── Deploy 버튼·무지개 데코·footer 제거 ───────────────────────────── */
[data-testid="stToolbarActionButtonLabel"]:has(+ [href*="deploy"]),
button[data-testid*="deploy"],
a[data-testid*="deploy"],
[data-testid="stAppDeployButton"] { display: none !important; }
[data-testid="stDecoration"]      { display: none !important; }
footer                            { display: none !important; }

/* ── 본문 상단 패딩 (헤더 높이 보상) ───────────────────────────────── */
.block-container {
    padding-top: 4.2rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1400px;
}

/* ── 전체 폰트 ──────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {
    font-family: 'Inter', 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
}

/* ══════════════════════════════════════════════════════════════════════
   KPI METRIC CARDS
   ══════════════════════════════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: var(--secondary-background-color) !important;
    border: 1px solid rgba(46,134,171,.20);
    border-top: 3px solid #2E86AB;
    border-radius: 12px;
    padding: 16px 20px 14px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
    transition: box-shadow .25s, transform .25s;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 6px 20px rgba(46,134,171,.22) !important;
    transform: translateY(-2px);
}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {
    font-size: 11.5px !important;
    color: var(--text-color) !important;
    opacity: .65;
    font-weight: 600 !important;
    letter-spacing: .4px;
    text-transform: uppercase;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 1.75rem !important;
    font-weight: 800 !important;
    color: var(--text-color) !important;
    letter-spacing: -.5px;
    line-height: 1.2;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 12px !important;
    font-weight: 600 !important;
}

/* ══════════════════════════════════════════════════════════════════════
   TABS
   ══════════════════════════════════════════════════════════════════════ */
[data-baseweb="tab-list"] {
    gap: 2px;
    background: var(--secondary-background-color) !important;
    border-radius: 12px;
    padding: 4px;
    flex-wrap: wrap;
    border-bottom: none !important;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 6px 13px !important;
    color: var(--text-color) !important;
    opacity: .60;
    background: transparent !important;
    border: none !important;
    white-space: nowrap;
    transition: opacity .2s, background .2s;
}
[data-baseweb="tab"]:hover {
    opacity: .90 !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: var(--background-color) !important;
    color: #2E86AB !important;
    opacity: 1 !important;
    box-shadow: 0 1px 6px rgba(0,0,0,.12) !important;
}

/* ══════════════════════════════════════════════════════════════════════
   SIDEBAR — adapts to light / dark mode via CSS variables
   ══════════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: var(--secondary-background-color) !important;
    border-right: 1px solid rgba(46,134,171,.12);
}
/* text inherits from theme — no forced color override */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stTextInput label,
[data-testid="stSidebar"] .stMultiSelect label {
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: .5px;
    opacity: .60;
}
[data-testid="stSidebar"] hr { border-color: rgba(128,128,128,.20) !important; }
[data-testid="stSidebar"] [data-testid="stButton"] button {
    background: linear-gradient(135deg, #2E86AB, #1f6a8e) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    letter-spacing: .3px;
    transition: all .2s;
    box-shadow: 0 2px 8px rgba(46,134,171,.30);
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
    background: linear-gradient(135deg, #3a9abf, #2E86AB) !important;
    box-shadow: 0 4px 14px rgba(46,134,171,.45) !important;
}

/* ══════════════════════════════════════════════════════════════════════
   BUTTONS
   ══════════════════════════════════════════════════════════════════════ */
[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(135deg, #2E86AB 0%, #1a6a8e 100%) !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 8px 22px !important;
    box-shadow: 0 3px 10px rgba(46,134,171,.35) !important;
    transition: all .25s !important;
    letter-spacing: .2px;
}
[data-testid="stButton"] button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(46,134,171,.45) !important;
}

/* ── Download button ──────────────────────────────────────────────── */
[data-testid="stDownloadButton"] button {
    border-radius: 9px !important;
    font-weight: 600 !important;
    border: 1.5px solid #2E86AB !important;
    color: #2E86AB !important;
    background: transparent !important;
    transition: all .2s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: #2E86AB !important;
    color: #fff !important;
}

/* ══════════════════════════════════════════════════════════════════════
   EXPANDERS
   ══════════════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    border: 1px solid rgba(46,134,171,.20) !important;
    border-radius: 10px !important;
    box-shadow: none !important;
    background: var(--secondary-background-color) !important;
}
[data-testid="stExpander"] summary {
    font-weight: 700 !important;
    color: #2E86AB !important;
    font-size: 14px !important;
}

/* ══════════════════════════════════════════════════════════════════════
   HEADINGS  — use CSS variable so dark mode keeps contrast
   ══════════════════════════════════════════════════════════════════════ */
h1 {
    color: var(--text-color) !important;
    font-weight: 800 !important;
    letter-spacing: -.6px;
    font-size: 1.9rem !important;
}
h2 {
    color: #2E86AB !important;
    font-weight: 700 !important;
    letter-spacing: -.3px;
}
h3 {
    color: var(--text-color) !important;
    font-weight: 600 !important;
    opacity: .85;
}

/* ══════════════════════════════════════════════════════════════════════
   FILE UPLOADER
   ══════════════════════════════════════════════════════════════════════ */
[data-testid="stFileUploader"] {
    border: 2px dashed rgba(46,134,171,.50) !important;
    border-radius: 14px !important;
    background: var(--secondary-background-color) !important;
    padding: 12px !important;
    transition: border-color .2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: #2E86AB !important;
}

/* ══════════════════════════════════════════════════════════════════════
   DATAFRAME
   ══════════════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(46,134,171,.15) !important;
}

/* ══════════════════════════════════════════════════════════════════════
   DIVIDER & CAPTION
   ══════════════════════════════════════════════════════════════════════ */
hr {
    border-color: rgba(46,134,171,.15) !important;
    margin: 1.2rem 0 !important;
}
[data-testid="stCaption"] {
    color: var(--text-color) !important;
    opacity: .55;
    font-size: 12px !important;
}

/* ══════════════════════════════════════════════════════════════════════
   ALERTS / INFO BOXES  — ensure text visible in dark mode
   ══════════════════════════════════════════════════════════════════════ */
[data-testid="stAlert"] p,
[data-testid="stInfo"] p,
[data-testid="stWarning"] p,
[data-testid="stSuccess"] p,
[data-testid="stError"] p { color: var(--text-color) !important; }

/* ══════════════════════════════════════════════════════════════════════
   SELECT / INPUT WIDGETS in main area
   ══════════════════════════════════════════════════════════════════════ */
[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    border-radius: 8px !important;
    border-color: rgba(46,134,171,.30) !important;
}

/* ══════════════════════════════════════════════════════════════════════
   PLOTLY CHART CONTAINER — no extra white bg
   ══════════════════════════════════════════════════════════════════════ */
.js-plotly-plot, .plotly, .plot-container {
    background: transparent !important;
}
</style>
""", unsafe_allow_html=True)

# ── 사이드바: 언어 선택 ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="padding:16px 4px 8px;font-size:20px;font-weight:800;'
        'letter-spacing:-.5px;color:#2E86AB;">📊 HR Dashboard</div>',
        unsafe_allow_html=True,
    )

    st.markdown("**🌐 언어 / Language**")
    lang_name = st.selectbox(
        label="language",
        options=SUPPORTED_LANGUAGES,
        label_visibility="collapsed",
    )
    lang = LANGUAGE_CODES[lang_name]

    st.divider()

    # 데이터 로드 시: 파일 요약 + 초기화 버튼
    df_loaded = st.session_state.get("df_clean")
    if df_loaded is not None:
        fname = st.session_state.get("filename", "")
        total = int((df_loaded["is_active"] == True).sum()) if "is_active" in df_loaded.columns else len(df_loaded)
        n_depts = df_loaded["department"].nunique() if "department" in df_loaded.columns else "-"

        st.markdown(
            f'<div style="background:rgba(46,134,171,.10);border:1px solid rgba(46,134,171,.25);'
            f'border-radius:10px;padding:12px 14px;margin-bottom:8px">'
            f'<div style="font-size:11px;opacity:.55;margin-bottom:8px;font-weight:600">📁 {fname}</div>'
            f'<div style="display:flex;gap:20px">'
            f'<div><div style="font-size:22px;font-weight:800;color:#2E86AB">{total:,}</div>'
            f'<div style="font-size:10px;opacity:.55;margin-top:2px">{t("total_employees", lang)}</div></div>'
            f'<div><div style="font-size:22px;font-weight:800;color:#44BBA4">{n_depts}</div>'
            f'<div style="font-size:10px;opacity:.55;margin-top:2px">{t("axis_department", lang)}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        if st.button(t("reset_btn", lang), use_container_width=True):
            for key in ["df_raw", "df_clean", "col_mapping", "filename"]:
                st.session_state.pop(key, None)
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# 업로드 화면
# ══════════════════════════════════════════════════════════════════════════════

def show_upload_page(lang: str):
    # ── 히어로 배너 ──────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,#1a2d42 0%,#2E86AB 100%);
                    border-radius:16px;padding:36px 40px;margin-bottom:28px;
                    box-shadow:0 4px 24px rgba(46,134,171,.25)">
          <div style="font-size:32px;font-weight:800;color:#fff;margin-bottom:8px">
            📊 {t('app_title', lang)}
          </div>
          <div style="font-size:15px;color:#b8d9ee;max-width:520px">
            {t('app_subtitle', lang)}
          </div>
          <div style="display:flex;gap:20px;margin-top:22px;flex-wrap:wrap">
            {"".join(
              f'<div style="background:rgba(255,255,255,.12);border-radius:8px;'
              f'padding:8px 14px;font-size:12px;color:#d8eeff;font-weight:600">{icon} {lbl}</div>'
              for icon, lbl in [
                ("👥","Headcount"), ("📈","Attrition"),("🔮","Forecast"),
                ("📊","Cohort"),("🌍","D&I"),("🚨","Risk"),("📤","Reports"),
              ]
            )}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        label=t("upload_title", lang),
        type=["xlsx", "xls", "csv"],
        help=t("upload_hint", lang),
    )

    if uploaded is None:
        return

    # 파일 크기 체크
    max_bytes = APP_CONFIG["max_file_size_mb"] * 1024 * 1024
    if uploaded.size > max_bytes:
        st.error(t("error_file_too_large", lang))
        return

    # ── 파일 로드 ──────────────────────────────────────────────────────────
    with st.spinner(t("loading", lang)):
        try:
            df_raw = load_file(uploaded, uploaded.name)
        except UnicodeDecodeError:
            st.error(t("error_encoding", lang))
            return
        except ValueError as e:
            st.error(t("error_unsupported", lang))
            return
        except Exception as e:
            st.error(t("error_parse", lang, msg=str(e)))
            return

    if df_raw.empty:
        st.error(t("error_empty_file", lang))
        return

    # ── 데이터 미리보기 ────────────────────────────────────────────────────
    n = APP_CONFIG["preview_rows"]
    st.subheader(t("upload_preview", lang, n=n))
    st.dataframe(df_raw.head(n), use_container_width=True)

    # ── 컬럼 자동 감지 ────────────────────────────────────────────────────
    mapping = detect_columns(df_raw)
    is_valid, missing = validate_mapping(mapping)

    st.subheader(t("column_mapping_title", lang))
    summary = get_column_mapping_summary(mapping)

    found_count  = sum(1 for i in summary if i["found"])
    total_count  = len(summary)
    req_missing  = [i["standard"] for i in summary if not i["found"] and i["required"]]

    # 진행 바 + 카운터
    pct = found_count / total_count if total_count else 0
    bar_color = "#44BBA4" if pct >= 0.7 else "#F18F01" if pct >= 0.4 else "#C73E1D"
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">'
        f'<div style="flex:1;background:rgba(128,128,128,.18);border-radius:6px;height:8px;overflow:hidden">'
        f'<div style="width:{pct*100:.0f}%;background:{bar_color};height:100%;border-radius:6px;'
        f'transition:width .4s"></div></div>'
        f'<div style="font-size:13px;font-weight:700;color:{bar_color}">'
        f'{found_count}/{total_count}</div></div>',
        unsafe_allow_html=True,
    )

    mapping_display = []
    for item in summary:
        if item["found"]:
            badge = '<span style="background:rgba(68,187,164,.20);color:#44BBA4;border-radius:5px;padding:2px 8px;font-size:11px;font-weight:700">✅ Auto</span>'
        elif item["required"]:
            badge = '<span style="background:rgba(199,62,29,.18);color:#e05a3a;border-radius:5px;padding:2px 8px;font-size:11px;font-weight:700">⚠️ Required</span>'
        else:
            badge = '<span style="background:rgba(176,120,0,.18);color:#c89a30;border-radius:5px;padding:2px 8px;font-size:11px;font-weight:700">○ Optional</span>'
        mapping_display.append({
            t("col_standard", lang): item["standard"],
            t("col_detected", lang): item["detected"] if item["detected"] else "-",
            t("col_status", lang): badge,
        })

    # HTML 테이블로 뱃지 렌더링
    rows_html = ""
    for row in mapping_display:
        rows_html += (
            f'<tr><td style="padding:7px 12px;font-size:13px;font-weight:600">{row[t("col_standard", lang)]}</td>'
            f'<td style="padding:7px 12px;font-size:13px;opacity:.75">{row[t("col_detected", lang)]}</td>'
            f'<td style="padding:7px 12px">{row[t("col_status", lang)]}</td></tr>'
        )
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;background:transparent;'
        f'border-radius:8px;overflow:hidden;border:1px solid rgba(128,128,128,.2)">'
        f'<thead><tr style="background:rgba(128,128,128,.10)">'
        f'<th style="padding:9px 12px;font-size:12px;opacity:.65;text-align:left;font-weight:700">{t("col_standard", lang)}</th>'
        f'<th style="padding:9px 12px;font-size:12px;opacity:.65;text-align:left;font-weight:700">{t("col_detected", lang)}</th>'
        f'<th style="padding:9px 12px;font-size:12px;opacity:.65;text-align:left;font-weight:700">{t("col_status", lang)}</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    # ── 필수 컬럼 누락 경고 ───────────────────────────────────────────────
    if not is_valid:
        st.error(t("error_column_missing", lang, cols=", ".join(missing)))
        return

    # ── 분석 시작 버튼 ────────────────────────────────────────────────────
    if st.button(f"🚀 {t('analyze_btn', lang)}", type="primary", use_container_width=True):
        with st.spinner(t("loading", lang)):
            df_clean = clean_data(df_raw, mapping)
        st.session_state["df_raw"] = df_raw
        st.session_state["df_clean"] = df_clean
        st.session_state["col_mapping"] = mapping
        st.session_state["filename"] = uploaded.name
        st.success(t("success", lang))
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# 대시보드 화면
# ══════════════════════════════════════════════════════════════════════════════

def show_dashboard(df: pd.DataFrame, lang: str):
    filename = st.session_state.get("filename", "")
    from datetime import date as _date
    today_str = _date.today().strftime("%Y-%m-%d")
    total_all = len(df)

    st.markdown(
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:8px;margin-bottom:6px">'
        f'<div style="font-size:26px;font-weight:800;letter-spacing:-.5px">📊 {t("app_title", lang)}</div>'
        f'<div style="display:flex;gap:8px;flex-wrap:wrap">'
        f'<span style="background:rgba(128,128,128,.12);border-radius:20px;padding:4px 12px;'
        f'font-size:12px;font-weight:600;opacity:.80">📁 {filename}</span>'
        f'<span style="background:rgba(68,187,164,.15);color:#44BBA4;border-radius:20px;padding:4px 12px;'
        f'font-size:12px;font-weight:600">👥 {total_all:,} rows</span>'
        f'<span style="background:rgba(46,134,171,.15);color:#2E86AB;border-radius:20px;padding:4px 12px;'
        f'font-size:12px;font-weight:600">📅 {today_str}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── 사이드바 필터 ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            f'<div style="font-size:12px;font-weight:700;opacity:.55;'
            f'letter-spacing:.8px;text-transform:uppercase;margin-bottom:8px">'
            f'🔍 {t("filter_title", lang)}</div>',
            unsafe_allow_html=True,
        )

        # 기간 필터
        date_min, date_max = get_date_range(df, "hire_date")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.text_input(
                t("filter_date_range", lang) + " (시작)",
                value=date_min, placeholder="YYYY-MM"
            )
        with col2:
            end_date = st.text_input(
                t("filter_date_range", lang) + " (종료)",
                value=date_max, placeholder="YYYY-MM"
            )

        # 부서 필터
        all_depts = get_departments(df)
        selected_depts = st.multiselect(
            t("filter_department", lang),
            options=all_depts,
            default=[],
            placeholder=t("filter_all", lang),
        )

        # 필터 적용 현황 배지
        active_filters = sum([
            bool(start_date and start_date != date_min),
            bool(end_date and end_date != date_max),
            bool(selected_depts),
        ])
        if active_filters:
            st.markdown(
                f'<div style="background:#1e4a6a;border-radius:6px;padding:6px 10px;'
                f'font-size:11px;color:#7dd3f0;margin-top:4px">'
                f'⚡ {active_filters} filter(s) active</div>',
                unsafe_allow_html=True,
            )

    # ── 필터 적용 ─────────────────────────────────────────────────────────
    df_filtered = df.copy()
    if start_date or end_date:
        df_filtered = filter_by_date_range(df_filtered, "hire_date", start_date or None, end_date or None)
    if selected_depts:
        df_filtered = filter_by_department(df_filtered, selected_depts)

    # ── 탭 구성 ───────────────────────────────────────────────────────────
    # 논리 흐름: 현황 → 다양성 → 변동/추세 → 심층분석 → 예측/위험 → 개인 → 내보내기
    tabs = st.tabs([
        f"🏠 {t('tab_dashboard', lang)}",       # 0  전체 KPI 요약
        f"👥 {t('tab_headcount', lang)}",        # 1  인원 현황
        f"🌍 {t('tab_di', lang)}",               # 2  D&I 다양성
        f"📈 {t('tab_attrition', lang)}",        # 3  입퇴사/이직
        f"⏱️ {t('tab_tth', lang)}",             # 4  채용 소요시간
        f"📅 {t('tab_yoy', lang)}",              # 5  연도별 비교
        f"🏢 {t('tab_dept_detail', lang)}",      # 6  부서 상세
        f"🔮 {t('tab_forecast', lang)}",         # 7  인원 예측
        f"📊 {t('tab_cohort', lang)}",           # 8  코호트 리텐션
        f"🚨 {t('tab_risk', lang)}",             # 9  이직 위험
        f"🔍 {t('tab_search', lang)}",           # 10 직원 프로필
        f"📤 {t('tab_report', lang)}",           # 11 보고서 생성
        f"➕ {t('tab_additional', lang)}",       # 12 추가 통계
    ])

    with tabs[0]:
        _render_overview(df_filtered, lang, start_date, end_date)

    with tabs[1]:
        _render_headcount(df_filtered, lang)

    with tabs[2]:
        _render_di(df_filtered, lang)

    with tabs[3]:
        _render_attrition(df_filtered, lang, start_date, end_date)

    with tabs[4]:
        _render_tth(df_filtered, lang)

    with tabs[5]:
        _render_yoy(df_filtered, lang)

    with tabs[6]:
        _render_dept_detail(df_filtered, lang)

    with tabs[7]:
        _render_forecast(df_filtered, lang)

    with tabs[8]:
        _render_cohort(df_filtered, lang)

    with tabs[9]:
        _render_risk(df_filtered, lang)

    with tabs[10]:
        _render_employee_search(df_filtered, lang)

    with tabs[11]:
        _render_report_builder(df_filtered, lang)

    with tabs[12]:
        _render_additional(df_filtered, lang)

    # ── 다운로드 섹션 ─────────────────────────────────────────────────────
    st.divider()
    st.subheader(f"💾 {t('download_section', lang)}")
    _render_downloads(df_filtered, lang, start_date, end_date)


# ══════════════════════════════════════════════════════════════════════════════
# UI 헬퍼
# ══════════════════════════════════════════════════════════════════════════════

def _section_header(title: str, subtitle: str = ""):
    """탭 내 섹션 헤더 — 파란 좌측 테두리 + 선택적 설명."""
    sub_html = (f'<div style="font-size:12px;opacity:.55;margin-top:3px">{subtitle}</div>'
                if subtitle else "")
    st.markdown(
        f'<div style="border-left:4px solid #2E86AB;padding:6px 0 6px 14px;margin-bottom:16px">'
        f'<div style="font-size:16px;font-weight:700">{title}</div>'
        f'{sub_html}</div>',
        unsafe_allow_html=True,
    )


def _kpi_row(items: list, colors: list | None = None):
    """
    KPI 메트릭 행 렌더링.
    items: [(label, value, [delta])] 리스트
    colors: 각 카드 상단 border-top 색상 리스트 (CSS via hack)
    """
    cols = st.columns(len(items))
    default_colors = ["#2E86AB","#44BBA4","#C73E1D","#F18F01","#7B2D8B","#3B1F2B"]
    for i, (col, item) in enumerate(zip(cols, items)):
        label, value = item[0], item[1]
        delta = item[2] if len(item) > 2 else None
        color = (colors[i] if colors and i < len(colors) else default_colors[i % len(default_colors)])
        # border-top 색상을 CSS 변수로 주입 (st.metric wrapper div에 id 부여 불가 → JS trick 대신 style block)
        col.markdown(
            f'<style>[data-testid="metric-container"]:nth-child({i+1}) '
            f'{{border-top-color: {color} !important}}</style>',
            unsafe_allow_html=True,
        )
        if delta is not None:
            col.metric(label, value, delta=delta)
        else:
            col.metric(label, value)


# ══════════════════════════════════════════════════════════════════════════════
# 탭 렌더러
# ══════════════════════════════════════════════════════════════════════════════

def _render_overview(df: pd.DataFrame, lang: str, start: str, end: str):
    """전체 대시보드 탭."""
    kpis = summary_kpis(df, start or None, end or None)

    # KPI 카드 (색상별)
    cols = st.columns(5)
    kpi_data = [
        (t("total_employees", lang), f"{kpis['total_employees']:,}", "#2E86AB"),
        (t("new_hires", lang),       f"{kpis['new_hires']:,}",       "#44BBA4"),
        (t("resignations", lang),    f"{kpis['resignations']:,}",    "#C73E1D"),
        (t("turnover_rate", lang),   f"{kpis['turnover_rate']:.1f}%","#F18F01"),
        (t("avg_tenure", lang),      f"{kpis['avg_tenure']:.1f} {t('avg_tenure_unit', lang)}", "#7B2D8B"),
    ]
    for col, (label, value, color) in zip(cols, kpi_data):
        col.markdown(f'<style>[data-testid="metric-container"]{{border-top-color:{color}!important}}</style>',
                     unsafe_allow_html=True)
        col.metric(label, value)

    st.divider()

    # 차트 2×2
    col1, col2 = st.columns(2)
    with col1:
        data = headcount_by_dept(df)
        st.plotly_chart(
            bar_chart(data, t("chart_dept_dist", lang),
                      y_label=t("axis_count", lang), horizontal=True),
            use_container_width=True,
            key="ov_dept",
        )
    with col2:
        monthly = monthly_hire_resign_combined(df, start or None, end or None)
        st.plotly_chart(
            line_chart(monthly, "year_month",
                       ["hire_count", "resign_count"],
                       t("chart_monthly_hire", lang),
                       labels={"hire_count": t("series_hire", lang),
                               "resign_count": t("series_resign", lang)},
                       lang=lang),
            use_container_width=True,
            key="ov_monthly",
        )

    col3, col4 = st.columns(2)
    with col3:
        gender = headcount_by_gender(df, lang)
        if not gender.empty:
            st.plotly_chart(
                pie_chart(gender, t("chart_gender_ratio", lang)),
                use_container_width=True,
                key="ov_gender",
            )
        else:
            st.info(t("warn_no_gender", lang))
    with col4:
        tenure = tenure_distribution(df, lang)
        st.plotly_chart(
            category_bar(tenure, t("chart_tenure_dist", lang), lang=lang),
            use_container_width=True,
            key="ov_tenure",
        )


def _render_headcount(df: pd.DataFrame, lang: str):
    """인원 현황 탭."""
    # ── 평균 나이 KPI ─────────────────────────────────────────────────────
    age_stats = avg_age_by_gender(df)
    if age_stats["all"] > 0:
        ca, cm, cf = st.columns(3)
        unit = t("age_unit", lang)
        ca.metric(t("avg_age_all", lang),    f"{age_stats['all']:.1f} {unit}")
        cm.metric(t("avg_age_male", lang),   f"{age_stats['남']:.1f} {unit}" if age_stats['남'] else "—")
        cf.metric(t("avg_age_female", lang), f"{age_stats['여']:.1f} {unit}" if age_stats['여'] else "—")
        st.divider()

    col1, col2 = st.columns(2)

    with col1:
        data = headcount_by_dept(df)
        st.plotly_chart(
            bar_chart(data, t("chart_dept_dist", lang),
                      y_label=t("axis_count", lang), horizontal=True),
            use_container_width=True,
            key="hc_dept",
        )

        data = headcount_by_employment_type(df)
        if not data.empty:
            st.plotly_chart(
                pie_chart(data, t("chart_emp_type_dist", lang)),
                use_container_width=True,
                key="hc_emp_type",
            )

    with col2:
        data = headcount_by_position(df)
        st.plotly_chart(
            bar_chart(data, t("chart_position_dist", lang),
                      y_label=t("axis_count", lang), horizontal=True),
            use_container_width=True,
            key="hc_position",
        )

        data = headcount_by_age_group(df, lang)
        if not data.empty:
            st.plotly_chart(
                category_bar(data, t("chart_age_dist", lang),
                             x_label=t("axis_age", lang), lang=lang),
                use_container_width=True,
                key="hc_age",
            )
        else:
            st.info(t("warn_no_birth_date", lang))

    # 연령대·성별 인구 피라미드
    pyramid_df = age_gender_pyramid(df, lang)
    if not pyramid_df.empty:
        st.plotly_chart(
            pyramid_chart(pyramid_df, t("chart_age_pyramid", lang), lang=lang),
            use_container_width=True,
            key="hc_pyramid",
        )

    # ── 부서별 성비 누적 막대 ─────────────────────────────────────────────
    dg_df = dept_gender_ratio(df, lang)
    if not dg_df.empty:
        st.plotly_chart(
            dept_gender_stacked_bar(dg_df, t("chart_dept_gender", lang), lang=lang),
            use_container_width=True,
            key="hc_dept_gender",
        )

    # ── 직급별 평균 나이 · 근속 테이블 ───────────────────────────────────
    pos_stats = position_age_tenure_stats(df)
    if not pos_stats.empty:
        st.subheader(t("chart_position_stats", lang))
        col_rename = {"position": t("axis_position", lang), "count": t("col_count", lang)}
        if "avg_age" in pos_stats.columns:
            col_rename["avg_age"] = t("col_avg_age", lang)
        if "avg_tenure_years" in pos_stats.columns:
            col_rename["avg_tenure_years"] = t("col_avg_tenure", lang)
        st.dataframe(
            pos_stats.rename(columns=col_rename),
            use_container_width=True,
            hide_index=True,
        )

    # 요약 테이블
    st.subheader(t("chart_dept_dist", lang))
    dept_df = headcount_by_dept(df).reset_index()
    dept_df.columns = [t("axis_department", lang), t("axis_count", lang)]
    st.dataframe(dept_df, use_container_width=True, hide_index=True)


def _render_attrition(df: pd.DataFrame, lang: str, start: str, end: str):
    """입퇴사/이직 탭."""
    # KPI
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("turnover_rate", lang), f"{turnover_rate(df):.1f}%")
    _combined = monthly_hire_resign_combined(df)
    c2.metric(t("new_hires", lang), f"{int(_combined['hire_count'].sum()) if not _combined.empty else 0:,}")
    c3.metric(t("avg_tenure", lang), f"{avg_tenure(df):.1f} {t('avg_tenure_unit', lang)}")
    st_risk = short_tenure_ratio(df)
    if st_risk > 0:
        c4.metric(
            t("short_tenure_risk", lang),
            f"{st_risk:.1f}%",
            help=t("short_tenure_note", lang),
        )

    st.divider()

    # 월별 입퇴사 추이
    monthly = monthly_hire_resign_combined(df, start or None, end or None)
    st.plotly_chart(
        line_chart(monthly, "year_month",
                   ["hire_count", "resign_count"],
                   t("chart_monthly_hire", lang),
                   labels={"hire_count": t("series_hire", lang),
                           "resign_count": t("series_resign", lang)},
                   lang=lang),
        use_container_width=True,
        key="at_monthly",
    )

    col1, col2 = st.columns(2)
    with col1:
        data = turnover_by_dept(df)
        st.plotly_chart(
            turnover_rate_bar(data, t("chart_turnover_by_dept", lang), lang=lang),
            use_container_width=True,
            key="at_turnover",
        )
    with col2:
        data = avg_tenure_by_dept(df)
        st.plotly_chart(
            avg_tenure_bar(data, t("chart_avg_tenure_dept", lang), lang=lang),
            use_container_width=True,
            key="at_avg_tenure",
        )

    # 퇴사 사유
    reason = resign_reason_breakdown(df)
    if not reason.empty:
        st.plotly_chart(
            pie_chart(reason, t("chart_resign_reason", lang)),
            use_container_width=True,
            key="at_resign_reason",
        )


def _render_tth(df: pd.DataFrame, lang: str):
    """채용 소요시간 탭."""
    _section_header(t("tth_title", lang), t("tth_subtitle", lang))

    src = _tth_source_col(df)

    # ── 컬럼 없을 때 안내 ────────────────────────────────────────────────
    if src is None:
        st.warning(t("tth_no_col", lang))
        with st.expander("ℹ️ " + t("tth_no_col_hint", lang)):
            st.markdown(
                "- **KO**: 지원일, 서류접수일, 지원일자, 오퍼일, 제안일\n"
                "- **EN**: application_date, apply_date, applied_date, offer_date, offer_sent_date\n"
                "- **FR**: date de candidature, date d'offre"
            )
        return

    # 사용 컬럼 표시
    src_label = t("tth_using_app", lang) if src == "application_date" else t("tth_using_offer", lang)
    st.info(src_label)

    kpi = tth_kpi(df)

    # ── KPI 카드 ─────────────────────────────────────────────────────────
    unit = t("tth_days", lang)
    _kpi_row([
        (t("tth_avg", lang),         f"{kpi['avg']} {unit}"),
        (t("tth_median", lang),      f"{kpi['median']} {unit}"),
        (t("tth_min", lang),         f"{kpi['min']} {unit}"),
        (t("tth_max", lang),         f"{kpi['max']} {unit}"),
        (t("tth_total_hires", lang), f"{kpi['n']:,} {t('tth_ppl', lang)}"),
    ], colors=["#2E86AB", "#44BBA4", "#4caf50", "#F18F01", "#A23B72"])

    st.markdown("")

    # ── Row 1: 히스토그램 + 추이 ─────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        _section_header(t("tth_distribution", lang), t("tth_distribution_sub", lang))
        series = tth_series(df)
        st.plotly_chart(
            tth_histogram(series, t("tth_distribution", lang), lang),
            use_container_width=True,
        )
    with col2:
        _section_header(t("tth_trend", lang), t("tth_trend_sub", lang))
        trend_df = tth_trend_monthly(df)
        st.plotly_chart(
            tth_trend_chart(trend_df, t("tth_trend", lang), lang),
            use_container_width=True,
        )

    st.divider()

    # ── Row 2: 부서별 + 직급별 ────────────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        _section_header(t("tth_by_dept", lang), t("tth_by_dept_sub", lang))
        dept_df = tth_by_department(df)
        if dept_df.empty:
            st.caption("부서 데이터 없음 / No department data")
        else:
            st.plotly_chart(
                tth_by_dept_chart(dept_df, t("tth_by_dept", lang), lang),
                use_container_width=True,
            )
    with col4:
        _section_header(t("tth_by_position", lang), t("tth_by_position_sub", lang))
        pos_df = tth_by_position(df)
        if pos_df.empty:
            st.caption("직급 데이터 없음 / No position data")
        else:
            st.plotly_chart(
                tth_by_position_chart(pos_df, t("tth_by_position", lang), lang),
                use_container_width=True,
            )

    st.divider()

    # ── 상세 데이터 테이블 ────────────────────────────────────────────────
    with st.expander(f"📋 {t('tth_by_dept', lang)} — {t('tth_by_dept_sub', lang)}"):
        if not dept_df.empty:
            display_df = dept_df.rename(columns={
                "department": t("tth_axis_dept", lang),
                "avg":        t("tth_avg", lang),
                "median":     t("tth_median", lang),
                "count":      t("tth_total_hires", lang),
            })
            st.dataframe(display_df, use_container_width=True, hide_index=True)


def _render_yoy(df: pd.DataFrame, lang: str):
    """연도별 비교 탭."""
    yoy_df = yoy_summary(df)

    if yoy_df.empty:
        st.info(t("no_data_section", lang))
        return

    # ── 최근 연도 vs 전년 KPI 델타 ──────────────────────────────────────
    if len(yoy_df) >= 2:
        cur = yoy_df.iloc[-1]
        prev = yoy_df.iloc[-2]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("yoy_headcount", lang),    f"{int(cur['headcount']):,}",
                  delta=f"{int(cur['headcount'] - prev['headcount']):+,}",
                  help=t("yoy_vs_prev", lang))
        c2.metric(t("yoy_new_hires", lang),    f"{int(cur['new_hires']):,}",
                  delta=f"{int(cur['new_hires'] - prev['new_hires']):+,}",
                  help=t("yoy_vs_prev", lang))
        c3.metric(t("yoy_resignations", lang), f"{int(cur['resignations']):,}",
                  delta=f"{int(cur['resignations'] - prev['resignations']):+,}",
                  delta_color="inverse",
                  help=t("yoy_vs_prev", lang))
        c4.metric(t("yoy_turnover_rate", lang), f"{cur['turnover_rate']:.1f}%",
                  delta=f"{cur['turnover_rate'] - prev['turnover_rate']:+.1f}%",
                  delta_color="inverse",
                  help=t("yoy_vs_prev", lang))
        st.divider()

    # ── 입퇴사/인원 추이 (전체 너비) ─────────────────────────────────────
    st.plotly_chart(
        yoy_bar_line_chart(yoy_df, t("chart_yoy_overview", lang), lang=lang),
        use_container_width=True,
        key="yoy_overview",
    )

    # ── 이직률 추이 | 부서별 인원 추이 ───────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            yoy_turnover_chart(yoy_df, t("chart_yoy_turnover", lang), lang=lang),
            use_container_width=True,
            key="yoy_turnover",
        )
    with col2:
        dept_df = yoy_dept_headcount(df)
        if not dept_df.empty:
            st.plotly_chart(
                yoy_dept_trend_chart(dept_df, t("chart_yoy_dept", lang), lang=lang),
                use_container_width=True,
                key="yoy_dept",
            )

    # ── 연도별 요약 테이블 ────────────────────────────────────────────────
    st.subheader(t("yoy_table_title", lang))
    table = yoy_df.copy()
    table["year"] = table["year"].astype(int)
    table["headcount"] = table["headcount"].astype(int)
    table["new_hires"] = table["new_hires"].astype(int)
    table["resignations"] = table["resignations"].astype(int)
    table["turnover_rate"] = table["turnover_rate"].round(1)
    table["avg_tenure"] = table["avg_tenure"].round(1)
    col_rename = {
        "year": "Year",
        "headcount": t("yoy_headcount", lang),
        "new_hires": t("yoy_new_hires", lang),
        "resignations": t("yoy_resignations", lang),
        "turnover_rate": t("yoy_turnover_rate", lang) + " (%)",
        "avg_tenure": t("yoy_avg_tenure", lang),
    }
    st.dataframe(
        table.rename(columns=col_rename).sort_values("Year", ascending=False),
        use_container_width=True,
        hide_index=True,
    )


def _render_dept_detail(df: pd.DataFrame, lang: str):
    """부서 상세 탭."""
    depts = sorted(df["department"].dropna().unique().tolist()) if "department" in df.columns else []
    if not depts:
        st.info(t("no_data_section", lang))
        return

    selected = st.selectbox(
        t("dept_select_label", lang),
        options=depts,
        key="dept_detail_select",
    )
    if not selected:
        return

    detail = dept_detail(df, selected)
    if not detail:
        st.info(t("no_data_section", lang))
        return

    st.subheader(f"🏢 {selected}  —  {t('dept_detail_title', lang)}")
    st.divider()

    # ── KPI 카드 6종 ─────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(t("total_employees", lang),     f"{detail['headcount']:,}")
    c2.metric(t("dept_new_hires_ytd", lang),  f"{detail['new_hires_ytd']:,}")
    c3.metric(t("dept_resignations_ytd", lang), f"{detail['resignations_ytd']:,}")
    c4.metric(t("turnover_rate", lang),        f"{detail['turnover_rate']:.1f}%")
    c5.metric(t("avg_tenure", lang),           f"{detail['avg_tenure']:.1f} {t('avg_tenure_unit', lang)}")
    if detail['avg_age'] > 0:
        c6.metric(t("avg_age", lang),          f"{detail['avg_age']:.1f} {t('age_unit', lang)}")

    st.divider()

    # ── 차트 행 1: 성별 파이 | 직급별 막대 ──────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        if not detail["gender_dist"].empty:
            st.plotly_chart(
                pie_chart(detail["gender_dist"], t("chart_gender_ratio", lang)),
                use_container_width=True, key="dd_gender",
            )
    with col2:
        if not detail["position_dist"].empty:
            st.plotly_chart(
                bar_chart(detail["position_dist"], t("chart_position_dist", lang),
                          y_label=t("axis_count", lang), horizontal=True),
                use_container_width=True, key="dd_position",
            )

    # ── 차트 행 2: 근속연수 | 연령대 ─────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        if not detail["tenure_dist"].empty:
            st.plotly_chart(
                category_bar(detail["tenure_dist"], t("chart_tenure_dist", lang), lang=lang),
                use_container_width=True, key="dd_tenure",
            )
    with col4:
        if not detail["age_dist"].empty:
            st.plotly_chart(
                category_bar(detail["age_dist"], t("chart_age_dist", lang),
                             x_label=t("axis_age", lang), lang=lang),
                use_container_width=True, key="dd_age",
            )

    # ── 이직 위험 요약 ────────────────────────────────────────────────────
    st.divider()
    cr1, cr2 = st.columns(2)
    cr1.metric(t("dept_risk_high", lang),
               f"{detail['risk_high_count']}명",
               delta=f"{detail['risk_high_count']/max(detail['headcount'],1)*100:.0f}% of dept",
               delta_color="inverse")
    cr2.metric(t("dept_avg_risk_score", lang), f"{detail['risk_avg_score']:.1f} / 100")

    # ── 부서원 테이블 ─────────────────────────────────────────────────────
    if not detail["member_table"].empty:
        st.subheader(f"👤 {t('dept_members', lang)}")
        mt = detail["member_table"].copy()
        col_rename = {
            "name":         t("col_name", lang),
            "position":     t("col_position", lang),
            "tenure_years": t("col_tenure", lang),
            "age":          t("col_age", lang),
            "risk_score":   t("col_risk_score", lang),
            "risk_level":   t("col_risk_level", lang),
        }
        mt = mt.rename(columns={k: v for k, v in col_rename.items() if k in mt.columns})
        level_col = t("col_risk_level", lang)
        if level_col in mt.columns:
            mt[level_col] = mt[level_col].map({
                "High":   t("risk_high", lang),
                "Medium": t("risk_medium", lang),
                "Low":    t("risk_low", lang),
            })
        st.dataframe(mt, use_container_width=True, hide_index=True)


def _render_forecast(df: pd.DataFrame, lang: str):
    """인원 예측 탭."""
    if not has_column(df, "hire_date"):
        st.warning(t("forecast_no_hire", lang))
        return

    # ── 슬라이더: 예측 기간 ─────────────────────────────────────────────
    months_ahead = st.slider(
        t("forecast_months_label", lang),
        min_value=3, max_value=24, value=6, step=1,
        key="forecast_slider",
    )

    fdf = headcount_forecast(df, months_ahead=months_ahead)

    if fdf.empty:
        st.info(t("forecast_no_hire", lang))
        return

    slope = float(fdf["slope"].iloc[0])

    # ── KPI 메트릭 ──────────────────────────────────────────────────────
    last_actual = fdf[fdf["headcount"].notna()]["headcount"].iloc[-1]
    last_pred   = fdf[fdf["predicted"].notna()]["predicted"].iloc[-1]
    end_month   = fdf[fdf["predicted"].notna()]["month"].iloc[-1].strftime("%Y-%m")
    delta_val   = last_pred - last_actual
    slope_sign  = "▲" if slope >= 0 else "▼"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("forecast_current_hc", lang),  f"{int(round(last_actual)):,}")
    col2.metric(t("forecast_end_hc", lang),       f"{int(round(last_pred)):,}",
                delta=f"{delta_val:+.0f}")
    col3.metric(t("forecast_end_label", lang),    end_month)
    col4.metric(t("forecast_slope_label", lang),
                f"{slope_sign} {abs(slope):.1f} {t('forecast_slope_unit', lang)}")

    # ── 차트 ────────────────────────────────────────────────────────────
    st.plotly_chart(
        forecast_chart(fdf, t("chart_forecast", lang), lang),
        use_container_width=True,
        key="forecast_main_chart",
    )

    # ── 방법론 안내 ─────────────────────────────────────────────────────
    st.caption(f"ℹ️ {t('forecast_info', lang)}")

    # ── 예측 테이블 ─────────────────────────────────────────────────────
    with st.expander(t("forecast_table_title", lang), expanded=False):
        fut_only = fdf[fdf["predicted"].notna()].copy()
        fut_only["month_str"] = fut_only["month"].dt.strftime("%Y-%m")
        table = fut_only[["month_str", "predicted", "lower", "upper"]].rename(columns={
            "month_str": t("col_month", lang),
            "predicted": t("col_predicted", lang),
            "lower":     t("col_lower", lang),
            "upper":     t("col_upper", lang),
        })
        table = table.reset_index(drop=True)
        for col in [t("col_predicted", lang), t("col_lower", lang), t("col_upper", lang)]:
            table[col] = table[col].round(1)
        st.dataframe(table, use_container_width=True, hide_index=True)


def _render_cohort(df: pd.DataFrame, lang: str):
    """코호트 리텐션 탭."""
    if not has_column(df, "hire_date"):
        st.warning(t("cohort_no_data", lang))
        return

    cdf = cohort_retention(df)

    if cdf.empty:
        st.info(t("cohort_no_data", lang))
        return

    period_cols = [c for c in ["m6", "m12", "m18", "m24", "m30", "m36"] if c in cdf.columns]

    # ── KPI 메트릭 ──────────────────────────────────────────────────────
    m12_vals = cdf["m12"].dropna() if "m12" in cdf.columns else pd.Series(dtype=float)
    avg_12 = m12_vals.mean() if not m12_vals.empty else None

    best_row = cdf.loc[cdf["m12"].idxmax()] if not m12_vals.empty else None
    worst_row = cdf.loc[cdf["m12"].idxmin()] if not m12_vals.empty else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("cohort_size_label", lang),
                f"{int(cdf['cohort_size'].sum()):,}명 / {len(cdf)}코호트")
    col2.metric(t("cohort_avg_retention", lang),
                f"{avg_12:.1f}%" if avg_12 is not None else "-")
    col3.metric(t("cohort_best_cohort", lang),
                f"{int(best_row['cohort_year'])} ({best_row['m12']:.0f}%)" if best_row is not None else "-")
    col4.metric(t("cohort_worst_cohort", lang),
                f"{int(worst_row['cohort_year'])} ({worst_row['m12']:.0f}%)" if worst_row is not None else "-")

    # ── 히트맵 ──────────────────────────────────────────────────────────
    st.plotly_chart(
        cohort_heatmap(cdf, t("chart_cohort_heatmap", lang), lang),
        use_container_width=True,
        key="cohort_heatmap_chart",
    )

    # ── 생존 곡선 ────────────────────────────────────────────────────────
    st.plotly_chart(
        cohort_survival_chart(cdf, t("chart_cohort_survival", lang), lang),
        use_container_width=True,
        key="cohort_survival_chart",
    )

    st.caption(f"ℹ️ {t('cohort_info', lang)}")

    # ── 상세 테이블 ─────────────────────────────────────────────────────
    with st.expander(t("cohort_table_title", lang), expanded=False):
        display = cdf[["cohort_year", "cohort_size"] + period_cols].copy()
        display.columns = (
            [t("cohort_year_label", lang), t("cohort_size_label", lang)]
            + [f"{int(c[1:])}M %" for c in period_cols]
        )
        st.dataframe(display.reset_index(drop=True),
                     use_container_width=True, hide_index=True)


def _render_di(df: pd.DataFrame, lang: str):
    """D&I 다양성 지표 탭."""
    if not has_column(df, "gender"):
        st.warning(t("di_no_gender", lang))
        return

    balance_df = di_gender_balance(df)
    age_stats  = di_age_diversity(df)

    # ── KPI 메트릭 ──────────────────────────────────────────────────────
    overall_balance = balance_df["balance_score"].mean() if not balance_df.empty else None
    age_idx = age_stats.get("age_diversity_index")
    dominant = age_stats.get("dominant_group", "-")
    n_groups = age_stats.get("n_age_groups", "-")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(t("di_overall_balance", lang),
                f"{overall_balance:.2f}" if overall_balance is not None else "-",
                help=t("di_balance_note", lang))
    col2.metric(t("di_age_diversity_index", lang),
                f"{age_idx:.2f}" if age_idx is not None else "-",
                help=t("di_age_note", lang))
    col3.metric(t("di_dominant_group", lang), str(dominant))
    col4.metric(t("di_n_age_groups", lang), str(n_groups))

    st.divider()

    # ── 성별 균형 점수 차트 ──────────────────────────────────────────────
    if not balance_df.empty:
        st.plotly_chart(
            di_gender_balance_chart(balance_df, t("chart_di_gender_balance", lang), lang),
            use_container_width=True,
            key="di_gender_balance_chart",
        )
        st.caption(f"ℹ️ {t('di_balance_note', lang)}")

    # ── 직급 × 부서 여성 비율 히트맵 ────────────────────────────────────
    matrix = di_position_gender_matrix(df)
    if not matrix.empty:
        st.plotly_chart(
            di_position_heatmap(matrix, t("chart_di_position_heatmap", lang), lang),
            use_container_width=True,
            key="di_position_heatmap_chart",
        )

    # ── 부서별 상세 테이블 ───────────────────────────────────────────────
    if not balance_df.empty:
        with st.expander(t("di_table_title", lang), expanded=False):
            tbl = balance_df[["department", "total", "male", "female",
                               "male_ratio", "female_ratio", "balance_score"]].copy()
            tbl.columns = [
                t("axis_department", lang),
                t("col_count", lang),
                t("gender_male", lang),
                t("gender_female", lang),
                t("col_male_ratio", lang),
                t("col_female_ratio", lang),
                t("col_balance_score", lang),
            ]
            st.dataframe(tbl.reset_index(drop=True),
                         use_container_width=True, hide_index=True)


def _render_employee_search(df: pd.DataFrame, lang: str):
    """직원 프로필 검색 탭."""
    if df.empty:
        st.info(t("profile_no_data", lang))
        return

    # ── 위험 점수 및 코호트 데이터 사전 준비 ────────────────────────────
    risk_df = attrition_risk_scores(df)
    risk_lookup: dict = {}
    if not risk_df.empty and "name" in risk_df.columns:
        for _, row in risk_df.iterrows():
            risk_lookup[row["name"]] = {
                "risk_score": row.get("risk_score"),
                "risk_level": row.get("risk_level"),
            }

    cohort_df = cohort_retention(df)
    cohort_12m: dict = {}
    if not cohort_df.empty and "m12" in cohort_df.columns:
        for _, row in cohort_df.iterrows():
            cohort_12m[int(row["cohort_year"])] = row.get("m12")

    # ── 검색 입력 ────────────────────────────────────────────────────────
    query = st.text_input(
        t("search_placeholder", lang),
        placeholder=t("search_placeholder", lang),
        key="employee_search_input",
    )

    # 검색 대상 컬럼 구성
    search_cols = [c for c in ["name", "department", "position"] if c in df.columns]
    if not search_cols:
        st.warning(t("profile_no_data", lang))
        return

    # 필터링
    if query.strip():
        q = query.strip().lower()
        mask = df[search_cols].apply(
            lambda col: col.astype(str).str.lower().str.contains(q, na=False)
        ).any(axis=1)
        results = df[mask].copy()
    else:
        results = df.copy()

    n = len(results)
    st.caption(t("search_results_count", lang).format(n=n))

    if results.empty:
        st.info(t("search_no_results", lang))
        return

    # ── 직원 선택 ────────────────────────────────────────────────────────
    def _label(row) -> str:
        parts = [str(row.get("name", "?"))]
        if "department" in row:
            parts.append(str(row["department"]))
        if "position" in row:
            parts.append(str(row["position"]))
        return " | ".join(parts)

    options = [_label(r) for _, r in results.iterrows()]
    selected_label = st.selectbox(
        t("search_select_label", lang),
        options=options,
        key="employee_search_select",
    )

    sel_idx = options.index(selected_label)
    emp = results.iloc[sel_idx]

    st.divider()

    # ── 프로필 카드 ──────────────────────────────────────────────────────
    name = str(emp.get("name", "-"))
    dept = str(emp.get("department", "-"))
    pos  = str(emp.get("position", "-"))
    is_active = bool(emp.get("is_active", True))

    status_label = t("profile_active", lang) if is_active else t("profile_inactive", lang)
    status_color = "🟢" if is_active else "🔴"

    st.subheader(f"{status_color} {name}  ·  {dept}  ·  {pos}")

    # KPI 행 1: 기본 정보
    c1, c2, c3, c4 = st.columns(4)

    hire_date = emp.get("hire_date")
    hire_str  = pd.to_datetime(hire_date).strftime("%Y-%m-%d") if pd.notna(hire_date) else "-"
    c1.metric(t("profile_hire_date", lang), hire_str)

    tenure_yr = emp.get("tenure_years")
    c2.metric(t("profile_tenure", lang),
              f"{float(tenure_yr):.1f} yr" if pd.notna(tenure_yr) else "-")

    age = emp.get("age")
    c3.metric(t("profile_age", lang),
              f"{int(age)}" if pd.notna(age) else "-")

    gender = emp.get("gender", "-")
    c4.metric(t("profile_gender", lang), str(gender) if pd.notna(gender) else "-")

    # KPI 행 2: 위험 & 코호트
    c5, c6, c7, c8 = st.columns(4)

    risk_info = risk_lookup.get(name, {})
    r_score   = risk_info.get("risk_score")
    r_level   = risk_info.get("risk_level", "-")
    level_map = {"High": t("risk_high", lang), "Medium": t("risk_medium", lang),
                 "Low": t("risk_low", lang)}
    r_level_tr = level_map.get(r_level, r_level)
    level_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(r_level, "⚪")

    c5.metric(t("profile_risk_score", lang),
              f"{r_score:.0f}" if r_score is not None else "-")
    c6.metric(t("profile_risk_level", lang),
              f"{level_color} {r_level_tr}")

    hire_year = pd.to_datetime(hire_date).year if pd.notna(hire_date) else None
    cohort_val = cohort_12m.get(hire_year) if hire_year else None
    c7.metric(t("profile_cohort_12m", lang),
              f"{cohort_val:.1f}%" if cohort_val is not None else "-")

    resign_date = emp.get("resign_date")
    resign_str  = pd.to_datetime(resign_date).strftime("%Y-%m-%d") if pd.notna(resign_date) else "-"
    c8.metric(t("profile_resign_date", lang) if not is_active else t("profile_status", lang),
              resign_str if not is_active else status_label)

    # ── 동일 부서 동료 ───────────────────────────────────────────────────
    st.divider()
    st.subheader(f"👥 {t('profile_peers_title', lang)}  —  {dept}")

    peer_cols = [c for c in ["name", "position", "tenure_years", "age", "is_active"]
                 if c in df.columns]
    peers = df[(df.get("department", pd.Series()) == dept)].copy()
    if "name" in peers.columns:
        peers = peers[peers["name"] != name]

    if peers.empty:
        st.info(t("search_no_results", lang))
    else:
        peer_display = peers[peer_cols].copy()
        col_rename = {
            "name":         t("col_name", lang),
            "position":     t("col_position", lang),
            "tenure_years": t("col_tenure", lang),
            "age":          t("col_age", lang),
            "is_active":    t("profile_status", lang),
        }
        peer_display = peer_display.rename(columns={k: v for k, v in col_rename.items() if k in peer_display.columns})
        if t("profile_status", lang) in peer_display.columns:
            peer_display[t("profile_status", lang)] = peer_display[t("profile_status", lang)].map(
                {True: t("profile_active", lang), False: t("profile_inactive", lang)}
            )
        if t("col_tenure", lang) in peer_display.columns:
            peer_display[t("col_tenure", lang)] = peer_display[t("col_tenure", lang)].round(1)
        st.dataframe(peer_display.reset_index(drop=True),
                     use_container_width=True, hide_index=True)


def _render_report_builder(df: pd.DataFrame, lang: str):
    """맞춤 보고서 생성 탭."""

    # ── 회사명 입력 ──────────────────────────────────────────────────────
    company_name = st.text_input(
        t("report_company_label", lang),
        placeholder=t("report_company_placeholder", lang),
        key="report_company_input",
    )

    st.markdown(f"**{t('report_sections_label', lang)}**")

    # ── 섹션 체크박스 (2열 그리드) ──────────────────────────────────────
    SECTIONS = [
        ("kpi",       "report_sec_kpi",       True),
        ("headcount", "report_sec_headcount",  True),
        ("attrition", "report_sec_attrition",  True),
        ("yoy",       "report_sec_yoy",        True),
        ("forecast",  "report_sec_forecast",   True),
        ("cohort",    "report_sec_cohort",     True),
        ("di",        "report_sec_di",         False),
        ("risk",      "report_sec_risk",       True),
    ]

    col_a, col_b = st.columns(2)
    selected_sections = []
    for i, (key, label_key, default) in enumerate(SECTIONS):
        col = col_a if i % 2 == 0 else col_b
        checked = col.checkbox(t(label_key, lang), value=default,
                               key=f"report_sec_{key}")
        if checked:
            selected_sections.append(key)

    st.divider()

    # ── 생성 버튼 ────────────────────────────────────────────────────────
    if st.button(t("report_generate_btn", lang), type="primary",
                 key="report_generate_btn"):
        if not selected_sections:
            st.warning(t("report_no_sections", lang))
        else:
            with st.spinner(t("report_generating", lang)):
                html_bytes = custom_report_html(
                    df,
                    sections=selected_sections,
                    lang=lang,
                    company_name=company_name,
                )
            st.success(t("report_ready", lang))
            st.download_button(
                label=t("report_download_btn", lang),
                data=html_bytes,
                file_name=filename_with_date("hr_report", "html", lang),
                mime="text/html",
                key="report_download_btn",
            )


def _render_risk(df: pd.DataFrame, lang: str):
    """이직 위험 탭."""
    risk_df = attrition_risk_scores(df)

    if risk_df.empty:
        st.info(t("no_data_section", lang))
        return

    summary = risk_summary(risk_df)
    dept_risk_df = risk_by_dept(risk_df)

    # ── KPI 카드 ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("risk_high_count", lang),
              f"{summary['high_count']}명",
              delta=f"{summary['high_pct']:.1f}% of total",
              delta_color="inverse")
    c2.metric(t("risk_medium", lang), f"{summary['medium_count']}명")
    c3.metric(t("risk_low", lang),    f"{summary['low_count']}명")
    c4.metric(t("risk_avg_score", lang), f"{summary['avg_score']:.1f} / 100")

    st.caption(f"ℹ️ {t('risk_score_note', lang)}")
    st.divider()

    # ── 차트 행 1: 도넛 + 부서별 ─────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            risk_donut_chart(summary, t("chart_risk_dist", lang), lang=lang),
            use_container_width=True,
            key="risk_donut",
        )
    with col2:
        if not dept_risk_df.empty:
            st.plotly_chart(
                risk_by_dept_chart(dept_risk_df, t("chart_risk_by_dept", lang), lang=lang),
                use_container_width=True,
                key="risk_dept",
            )

    # ── 차트 행 2: 산포도 (근속연수 × 위험점수) ──────────────────────────
    if "tenure_years" in risk_df.columns:
        st.plotly_chart(
            risk_scatter_chart(risk_df, t("chart_risk_scatter", lang), lang=lang),
            use_container_width=True,
            key="risk_scatter",
        )

    # ── 위험 직원 목록 테이블 ─────────────────────────────────────────────
    st.subheader(f"🔴 {t('risk_table_title', lang)}")

    # 표시 컬럼 선택 (있는 것만)
    display_cols_map = {
        "name":         t("col_name", lang),
        "department":   t("col_dept", lang),
        "position":     t("col_position", lang),
        "tenure_years": t("col_tenure", lang),
        "age":          t("col_age", lang),
        "risk_score":   t("col_risk_score", lang),
        "risk_level":   t("col_risk_level", lang),
    }
    avail = {k: v for k, v in display_cols_map.items() if k in risk_df.columns}
    table_df = risk_df[list(avail.keys())].rename(columns=avail).copy()

    # 소수점 정리: 근속연수 → 1자리, 나이 → 1자리, 위험점수 → 1자리
    _round_map = {
        t("col_tenure", lang): 1,
        t("col_age", lang):    1,
        t("col_risk_score", lang): 1,
    }
    for col, decimals in _round_map.items():
        if col in table_df.columns:
            table_df[col] = table_df[col].round(decimals)

    # 등급 이름 현지화
    level_col = t("col_risk_level", lang)
    if level_col in table_df.columns:
        label_map = {
            "High":   t("risk_high", lang),
            "Medium": t("risk_medium", lang),
            "Low":    t("risk_low", lang),
        }
        table_df[level_col] = table_df[level_col].map(label_map)

    # High만 기본 표시 (전체 토글)
    show_all = st.checkbox(
        f"{t('risk_medium', lang)} / {t('risk_low', lang)} 포함 전체 보기",
        value=False,
        key="risk_show_all",
    )
    if not show_all:
        high_label = t("risk_high", lang)
        display_table = table_df[table_df[level_col] == high_label]
    else:
        display_table = table_df

    # 위험 등급별 행 색상
    def _row_color(row):
        level_val = row.get(level_col, "")
        high_lbl   = t("risk_high", lang)
        medium_lbl = t("risk_medium", lang)
        if level_val == high_lbl:
            return ["background-color: #fde8e4"] * len(row)
        if level_val == medium_lbl:
            return ["background-color: #fff4e0"] * len(row)
        return [""] * len(row)

    styled = display_table.style.apply(_row_color, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)


def _render_additional(df: pd.DataFrame, lang: str):
    """추가 통계 탭."""
    from analytics import recruitment_stats, education_stats, org_structure_stats

    st.subheader(t("section_org", lang))
    org = org_structure_stats(df)
    if org:
        c1, c2 = st.columns(2)
        if "avg_team_size" in org:
            c1.metric("평균 팀 규모", f"{org['avg_team_size']:.1f}명")
        if "avg_span_of_control" in org:
            c2.metric("스팬 오브 컨트롤", f"{org['avg_span_of_control']:.1f}")
        if "dept_size_distribution" in org:
            st.plotly_chart(
                bar_chart(
                    org["dept_size_distribution"],
                    t("chart_dept_dist", lang),
                    y_label=t("axis_count", lang),
                    horizontal=True,
                ),
                use_container_width=True,
                key="add_org_dept",
            )
    else:
        st.info(t("no_data_section", lang))

    # 채용 현황
    st.subheader(t("section_recruitment", lang))
    rec = recruitment_stats(df)
    if rec:
        if "by_channel" in rec:
            st.plotly_chart(
                pie_chart(rec["by_channel"], t("section_recruitment", lang)),
                use_container_width=True,
                key="add_rec_channel",
            )
        if "avg_days" in rec:
            st.metric("평균 채용 소요일", f"{rec['avg_days']:.0f}일")
    else:
        st.info(t("no_data_section", lang))

    # 교육/역량
    st.subheader(t("section_education", lang))
    edu = education_stats(df)
    if edu:
        if "completion_rate" in edu:
            st.metric("교육 이수율", f"{edu['completion_rate']:.1f}%")
        if "avg_hours" in edu:
            st.metric("평균 교육 시간", f"{edu['avg_hours']:.1f}시간")
    else:
        st.info(t("no_data_section", lang))


def _render_downloads(df: pd.DataFrame, lang: str, start: str, end: str):
    """다운로드 버튼 섹션."""
    from analytics import summary_kpis

    kpis = summary_kpis(df, start or None, end or None)
    company = st.session_state.get("filename", "").replace(".xlsx", "").replace(".xls", "")
    c1, c2, c3, c4, c5 = st.columns(5)

    # ── 엑셀 ──────────────────────────────────────────────────────────────
    with c1:
        try:
            excel_bytes = to_excel(df, kpis, lang)
            st.download_button(
                label=t("download_excel", lang),
                data=excel_bytes,
                file_name=filename_with_date("hr_report", "xlsx", lang),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Excel 오류: {e}")

    # ── CSV ───────────────────────────────────────────────────────────────
    with c2:
        try:
            csv_bytes = to_csv(df)
            st.download_button(
                label=t("download_csv", lang),
                data=csv_bytes,
                file_name=filename_with_date("hr_data", "csv", lang),
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"CSV 오류: {e}")

    # ── HTML 차트 보고서 (항상 활성) ──────────────────────────────────────
    with c3:
        try:
            html_bytes = charts_to_html(df, lang)
            st.download_button(
                label=t("download_chart_html", lang),
                data=html_bytes,
                file_name=filename_with_date("hr_charts", "html", lang),
                mime="text/html",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"HTML 오류: {e}")

    # ── PNG 요약 보고서 (matplotlib 기반 — 항상 활성) ─────────────────────
    with c4:
        try:
            png_bytes = summary_png(df, kpis, lang)
            st.download_button(
                label=t("download_chart", lang),
                data=png_bytes,
                file_name=filename_with_date("hr_summary", "png", lang),
                mime="image/png",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PNG 오류: {e}")

    # ── PDF 보고서 ────────────────────────────────────────────────────────
    with c5:
        try:
            pdf_bytes = to_pdf(df, lang, company_name=company,
                               start_date=start, end_date=end)
            st.download_button(
                label=t("download_pdf", lang),
                data=pdf_bytes,
                file_name=filename_with_date("hr_report", "pdf", lang),
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF 오류: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 메인 라우터
# ══════════════════════════════════════════════════════════════════════════════

def main():
    df_clean = st.session_state.get("df_clean")

    if df_clean is None:
        show_upload_page(lang)
    else:
        show_dashboard(df_clean, lang)


if __name__ == "__main__":
    main()
else:
    # streamlit run app.py 실행 시 직접 호출
    main()
