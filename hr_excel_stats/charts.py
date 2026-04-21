# Design Ref: §3.5 — Plotly 차트 생성 함수 (bar/line/pie/histogram)
"""
charts.py — Plotly 차트 생성 모듈

모든 함수는 plotly.graph_objects.Figure를 반환합니다.
한국어 폰트(Malgun Gothic)와 공통 스타일이 자동 적용됩니다.

Design 결정: plotly_white 테마, 한국어 폰트 fallback, 공통 색상 팔레트
"""

from __future__ import annotations

from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import APP_CONFIG
from i18n import t

# ── 공통 스타일 상수 ──────────────────────────────────────────────────────
_THEME = APP_CONFIG["chart_theme"]
_FONT = APP_CONFIG["chart_font_family"]
_HEIGHT = APP_CONFIG["chart_height"]
_COLORS = APP_CONFIG["chart_colors"]

_BASE_LAYOUT = dict(
    font=dict(family=_FONT, size=13),
    plot_bgcolor="rgba(0,0,0,0)",    # 투명 → 컨테이너 배경 상속 (다크모드 호환)
    paper_bgcolor="rgba(0,0,0,0)",   # 투명
    margin=dict(l=40, r=20, t=50, b=40),
    height=_HEIGHT,
    title_font=dict(size=15, family=_FONT),
)

# 반투명 그리드·축선 — 라이트/다크 모두에서 가시성 확보
_GRID_COLOR = "rgba(128,128,128,.18)"
_LINE_COLOR = "rgba(128,128,128,.30)"


def _polish(fig: go.Figure) -> go.Figure:
    """모든 차트에 다크모드 호환 축·범례 스타일 적용."""
    fig.update_xaxes(
        gridcolor=_GRID_COLOR,
        linecolor=_LINE_COLOR,
        tickfont=dict(size=11),
        title_font=dict(size=12),
        zeroline=False,
    )
    fig.update_yaxes(
        gridcolor=_GRID_COLOR,
        linecolor=_LINE_COLOR,
        tickfont=dict(size=11),
        title_font=dict(size=12),
        zeroline=False,
    )
    # 범례 배경 투명 — 다크모드에서 흰 박스 방지
    fig.update_layout(
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(size=12),
        )
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# 막대그래프
# ══════════════════════════════════════════════════════════════════════════════

def bar_chart(
    data: pd.Series,
    title: str,
    x_label: str = "",
    y_label: str = "",
    color: str = _COLORS[0],
    horizontal: bool = False,
    max_items: int = 20,
) -> go.Figure:
    """
    단순 막대그래프.

    Args:
        data: index=카테고리, values=값인 Series
        title: 차트 제목
        x_label / y_label: 축 레이블
        horizontal: True면 수평 막대
        max_items: 표시할 최대 항목 수 (초과 시 상위 N개)
    """
    if data.empty:
        return _empty_figure(title)

    data = data.head(max_items)

    if horizontal:
        fig = go.Figure(go.Bar(
            x=data.values,
            y=data.index.astype(str),
            orientation="h",
            marker_color=color,
            text=data.values,
            textposition="outside",
        ))
        fig.update_layout(
            **_BASE_LAYOUT,
            title=dict(text=title, font=dict(size=15)),
            xaxis=dict(title=y_label),
            yaxis=dict(title=x_label, autorange="reversed"),
            template=_THEME,
        )
    else:
        fig = go.Figure(go.Bar(
            x=data.index.astype(str),
            y=data.values,
            marker_color=color,
            text=data.values,
            textposition="outside",
        ))
        fig.update_layout(
            **_BASE_LAYOUT,
            title=dict(text=title, font=dict(size=15)),
            xaxis=dict(title=x_label, tickangle=-30),
            yaxis=dict(title=y_label),
            template=_THEME,
        )
    return _polish(fig)


def grouped_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: list[str],
    title: str,
    labels: dict | None = None,
) -> go.Figure:
    """
    그룹 막대그래프 (예: 입사/퇴사 월별 비교).

    Args:
        df: DataFrame
        x_col: x축 컬럼명
        y_cols: 각 그룹의 y축 컬럼명 리스트
        labels: {컬럼명: 표시 레이블} dict
    """
    if df.empty:
        return _empty_figure(title)

    labels = labels or {}
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        if col in df.columns:
            fig.add_trace(go.Bar(
                name=labels.get(col, col),
                x=df[x_col],
                y=df[col],
                marker_color=_COLORS[i % len(_COLORS)],
                text=df[col],
                textposition="outside",
            ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        barmode="group",
        template=_THEME,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 원형 차트
# ══════════════════════════════════════════════════════════════════════════════

def pie_chart(
    data: pd.Series,
    title: str,
    hole: float = 0.35,
) -> go.Figure:
    """
    원형(도넛) 차트.

    Args:
        data: index=레이블, values=값인 Series
        hole: 도넛 구멍 크기 (0=원형, 0.35=도넛)
    """
    if data.empty:
        return _empty_figure(title)

    fig = go.Figure(go.Pie(
        labels=data.index.astype(str),
        values=data.values,
        hole=hole,
        marker=dict(colors=_COLORS[:len(data)]),
        textinfo="label+percent",
        hovertemplate="%{label}: %{value}명 (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        template=_THEME,
        showlegend=True,
        legend=dict(orientation="v"),
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 라인 차트
# ══════════════════════════════════════════════════════════════════════════════

def line_chart(
    df: pd.DataFrame,
    x_col: str,
    y_cols: list[str],
    title: str,
    labels: dict | None = None,
    lang: str = "ko",
) -> go.Figure:
    """
    라인 차트 (예: 월별 입퇴사 추이).

    Args:
        df: DataFrame
        x_col: x축 컬럼명
        y_cols: y축 컬럼명 리스트 (복수 라인)
        labels: {컬럼명: 표시 레이블}
    """
    if df.empty:
        return _empty_figure(title)

    labels = labels or {}
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        if col in df.columns:
            fig.add_trace(go.Scatter(
                name=labels.get(col, col),
                x=df[x_col],
                y=df[col],
                mode="lines+markers+text",
                marker=dict(color=_COLORS[i % len(_COLORS)], size=8),
                line=dict(color=_COLORS[i % len(_COLORS)], width=2),
                text=df[col],
                textposition="top center",
            ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=t("axis_year_month", lang), tickangle=-30),
        yaxis=dict(title=t("axis_count", lang)),
        template=_THEME,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 히스토그램 / 분포 차트
# ══════════════════════════════════════════════════════════════════════════════

def histogram_chart(
    data: pd.Series,
    title: str,
    x_label: str = "",
    y_label: str = "",
    color: str = _COLORS[2],
    nbins: int = 10,
) -> go.Figure:
    """연속형 데이터의 히스토그램 (예: 연령 분포)."""
    valid = data.dropna()
    if valid.empty:
        return _empty_figure(title)

    fig = go.Figure(go.Histogram(
        x=valid,
        nbinsx=nbins,
        marker_color=color,
        opacity=0.85,
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=x_label),
        yaxis=dict(title=y_label or "인원수"),
        template=_THEME,
        bargap=0.1,
    )
    return _polish(fig)


def category_bar(
    data: pd.Series,
    title: str,
    x_label: str = "",
    lang: str = "ko",
) -> go.Figure:
    """
    구간 레이블이 있는 막대그래프 (근속연수/연령대 분포용).
    순서를 유지하여 표시.
    """
    if data.empty:
        return _empty_figure(title)

    fig = go.Figure(go.Bar(
        x=data.index.astype(str),
        y=data.values,
        marker_color=_COLORS[3],
        text=data.values,
        textposition="outside",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=x_label, categoryorder="array", categoryarray=list(data.index)),
        yaxis=dict(title=t("axis_count", lang)),
        template=_THEME,
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 복합 대시보드 차트
# ══════════════════════════════════════════════════════════════════════════════

def turnover_rate_bar(
    data: pd.Series,
    title: str,
    lang: str = "ko",
) -> go.Figure:
    """부서별 이직률 수평 막대그래프."""
    if data.empty:
        return _empty_figure(title)

    fig = go.Figure(go.Bar(
        x=data.values,
        y=data.index.astype(str),
        orientation="h",
        marker_color=[
            _COLORS[3] if v >= 15 else _COLORS[0]
            for v in data.values
        ],
        text=[f"{v:.1f}%" for v in data.values],
        textposition="outside",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=t("axis_rate", lang)),
        yaxis=dict(title=t("axis_department", lang), autorange="reversed"),
        template=_THEME,
    )
    return _polish(fig)


def avg_tenure_bar(
    data: pd.Series,
    title: str,
    lang: str = "ko",
) -> go.Figure:
    """부서별 평균 근속연수 수평 막대그래프."""
    if data.empty:
        return _empty_figure(title)

    fig = go.Figure(go.Bar(
        x=data.values,
        y=data.index.astype(str),
        orientation="h",
        marker_color=_COLORS[4],
        text=[f"{v:.1f}{t('avg_tenure_unit', lang)}" for v in data.values],
        textposition="outside",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=t("avg_tenure", lang)),
        yaxis=dict(title=t("axis_department", lang), autorange="reversed"),
        template=_THEME,
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 이직 위험 차트
# ══════════════════════════════════════════════════════════════════════════════

_RISK_COLORS = {
    "High":   "#C73E1D",   # 빨강
    "Medium": "#F18F01",   # 주황
    "Low":    "#44BBA4",   # 초록
}

def risk_donut_chart(summary: dict, title: str, lang: str = "ko") -> go.Figure:
    """이직 위험 등급 도넛 차트."""
    from i18n import t as _t
    labels = [
        _t("risk_high", lang),
        _t("risk_medium", lang),
        _t("risk_low", lang),
    ]
    values = [summary.get("high_count", 0),
              summary.get("medium_count", 0),
              summary.get("low_count", 0)]
    colors = [_RISK_COLORS["High"], _RISK_COLORS["Medium"], _RISK_COLORS["Low"]]

    if sum(values) == 0:
        return _empty_figure(title)

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12),
        hovertemplate="%{label}: %{value}명 (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        showlegend=True,
        legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center"),
        annotations=[dict(
            text=f"<b>{sum(values)}</b><br>{_t('total_employees', lang)}",
            x=0.5, y=0.5, font_size=14,
            showarrow=False, xref="paper", yref="paper",
        )],
        template=_THEME,
    )
    return _polish(fig)


def risk_by_dept_chart(dept_risk_df, title: str, lang: str = "ko") -> go.Figure:
    """부서별 High/Medium/Low 누적 가로 막대."""
    from i18n import t as _t
    if dept_risk_df.empty:
        return _empty_figure(title)

    fig = go.Figure()
    for level in ("Low", "Medium", "High"):   # 아래부터 쌓기
        if level not in dept_risk_df.columns:
            continue
        label_map = {"High": _t("risk_high", lang),
                     "Medium": _t("risk_medium", lang),
                     "Low": _t("risk_low", lang)}
        fig.add_trace(go.Bar(
            y=dept_risk_df["department"],
            x=dept_risk_df[level],
            name=label_map[level],
            orientation="h",
            marker_color=_RISK_COLORS[level],
            text=dept_risk_df[level].apply(lambda v: str(int(v)) if v > 0 else ""),
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate=f"{label_map[level]}: %{{x}}<extra></extra>",
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        barmode="stack",
        xaxis=dict(title=_t("axis_count", lang)),
        yaxis=dict(title=_t("axis_department", lang), autorange="reversed"),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center",
                    traceorder="reversed"),
        template=_THEME,
    )
    return _polish(fig)


def risk_scatter_chart(risk_df, title: str, lang: str = "ko") -> go.Figure:
    """
    위험 점수 산포도: x=근속연수, y=위험점수, 색=등급, 크기=일정.
    tenure_years 컬럼 없으면 빈 차트.
    """
    from i18n import t as _t
    if risk_df.empty or "tenure_years" not in risk_df.columns:
        return _empty_figure(title)

    fig = go.Figure()
    for level in ("High", "Medium", "Low"):
        subset = risk_df[risk_df["risk_level"] == level]
        if subset.empty:
            continue

        # 호버에 표시할 정보
        hover_parts = ["<b>%{customdata[0]}</b>" if "name" in subset.columns else ""]
        hover_parts += [f"{_t('risk_score_label', lang)}: %{{y:.0f}}"]
        if "department" in subset.columns:
            hover_parts.append(f"{_t('axis_department', lang)}: %{{customdata[1]}}")
        hover_template = "<br>".join(p for p in hover_parts if p) + "<extra></extra>"

        custom = list(zip(
            subset.get("name", pd.Series([""] * len(subset))).fillna(""),
            subset.get("department", pd.Series([""] * len(subset))).fillna(""),
        ))

        fig.add_trace(go.Scatter(
            x=subset["tenure_years"],
            y=subset["risk_score"],
            mode="markers",
            name={"High": _t("risk_high", lang),
                  "Medium": _t("risk_medium", lang),
                  "Low": _t("risk_low", lang)}[level],
            marker=dict(
                color=_RISK_COLORS[level],
                size=9,
                line=dict(color="white", width=1),
                opacity=0.85,
            ),
            customdata=custom,
            hovertemplate=hover_template,
        ))

    # 기준선
    fig.add_hline(y=60, line_dash="dot", line_color="#C73E1D",
                  annotation_text=_t("risk_high", lang), annotation_position="right")
    fig.add_hline(y=30, line_dash="dot", line_color="#F18F01",
                  annotation_text=_t("risk_medium", lang), annotation_position="right")

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("axis_tenure", lang)),
        yaxis=dict(title=_t("risk_score_label", lang), range=[0, 105]),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
        template=_THEME,
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 부서별 성비 누적 막대
# ══════════════════════════════════════════════════════════════════════════════

def dept_gender_stacked_bar(df: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """
    부서별 성별 누적 가로 막대 차트.

    Args:
        df: dept_gender_ratio() 결과 DataFrame (columns: department, 남, 여, 기타)
        title: 차트 제목
        lang: 언어 코드
    """
    if df.empty:
        return _empty_figure(title)

    # 컬럼명은 lang에 따라 달라짐 → 번역 레이블로 색상 매핑
    male_lbl   = t("gender_male", lang)
    female_lbl = t("gender_female", lang)
    other_lbl  = t("gender_other", lang)
    color_map = {
        male_lbl:   _COLORS[0],   # 파랑
        female_lbl: "#E85D9A",    # 핑크
        other_lbl:  _COLORS[8],   # 연한 오렌지
    }

    fig = go.Figure()
    gender_cols = [c for c in df.columns if c != "department"]
    for col in gender_cols:
        if df[col].sum() > 0:
            fig.add_trace(go.Bar(
                y=df["department"],
                x=df[col],
                name=col,
                orientation="h",
                marker_color=color_map.get(col, _COLORS[4]),
                text=df[col],
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate=f"{col}: %{{x}}<extra></extra>",
            ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        barmode="stack",
        xaxis=dict(title=t("axis_count", lang)),
        yaxis=dict(title=t("axis_department", lang), autorange="reversed"),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
        template=_THEME,
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 인구 피라미드
# ══════════════════════════════════════════════════════════════════════════════

def pyramid_chart(df: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """
    연령대 × 성별 인구 피라미드 차트.

    Args:
        df: age_gender_pyramid() 결과 DataFrame (columns: age_label, 남, 여)
        title: 차트 제목
        lang: 언어 코드

    Returns:
        가로 막대형 butterfly 차트 (남=왼쪽, 여=오른쪽)
    """
    if df.empty:
        return _empty_figure(title)

    male_label   = t("gender_male", lang)
    female_label = t("gender_female", lang)

    # age_gender_pyramid()이 lang에 맞는 컬럼명을 반환하므로 동적으로 찾기
    data_cols = [c for c in df.columns if c != "age_label"]
    m_col = data_cols[0] if len(data_cols) >= 1 else male_label
    f_col = data_cols[1] if len(data_cols) >= 2 else female_label

    # 남성은 음수 값으로 왼쪽에 표시
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df["age_label"],
        x=-df[m_col],
        name=male_label,
        orientation="h",
        marker_color=_COLORS[0],
        text=df[m_col],
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate=f"{male_label}: %{{text}}<extra></extra>",
    ))

    fig.add_trace(go.Bar(
        y=df["age_label"],
        x=df[f_col],
        name=female_label,
        orientation="h",
        marker_color="#E85D9A",
        text=df[f_col],
        textposition="inside",
        insidetextanchor="middle",
        hovertemplate=f"{female_label}: %{{text}}<extra></extra>",
    ))

    # x축 최대값 계산 (눈금 대칭)
    max_val = int(max(df[m_col].max(), df[f_col].max(), 1))
    tick_step = max(1, (max_val // 4))
    tick_vals = list(range(-max_val - tick_step, max_val + tick_step + 1, tick_step))
    tick_texts = [str(abs(v)) for v in tick_vals]

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        barmode="overlay",
        bargap=0.15,
        xaxis=dict(
            tickvals=tick_vals,
            ticktext=tick_texts,
            title=t("axis_count", lang),
            zeroline=True,
            zerolinecolor="#aaa",
            zerolinewidth=1.5,
        ),
        yaxis=dict(
            title=t("axis_age", lang),
            autorange="reversed",           # 20대가 위, 60대+가 아래
        ),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
        template=_THEME,
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 연도별 비교 (YoY) 차트
# ══════════════════════════════════════════════════════════════════════════════

def yoy_bar_line_chart(yoy_df: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """연도별 입사/퇴사 막대 + 재직인원 라인 (이중축)."""
    from i18n import t as _t
    if yoy_df.empty:
        return _empty_figure(title)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    years = yoy_df["year"].astype(str)

    fig.add_trace(go.Bar(
        x=years, y=yoy_df["new_hires"],
        name=_t("yoy_new_hires", lang),
        marker_color=_COLORS[0],
        opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=years, y=yoy_df["resignations"],
        name=_t("yoy_resignations", lang),
        marker_color=_COLORS[3],
        opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=years, y=yoy_df["headcount"],
        name=_t("yoy_headcount", lang),
        mode="lines+markers",
        line=dict(color="#333333", width=2.5, dash="dot"),
        marker=dict(size=7),
    ), secondary_y=True)

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        barmode="group",
        xaxis=dict(title="Year"),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
        template=_THEME,
    )
    fig.update_yaxes(title_text=_t("axis_count", lang), secondary_y=False)
    fig.update_yaxes(title_text=_t("yoy_headcount", lang), secondary_y=True, showgrid=False)
    return _polish(fig)


def yoy_turnover_chart(yoy_df: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """연도별 이직률 라인차트."""
    from i18n import t as _t
    if yoy_df.empty:
        return _empty_figure(title)

    current_year = str(date.today().year)
    colors = [_COLORS[3] if str(y) == current_year else _COLORS[0]
              for y in yoy_df["year"]]
    sizes  = [12 if str(y) == current_year else 8 for y in yoy_df["year"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yoy_df["year"].astype(str),
        y=yoy_df["turnover_rate"],
        mode="lines+markers",
        line=dict(color=_COLORS[0], width=2.5),
        marker=dict(color=colors, size=sizes, line=dict(color="white", width=1.5)),
        name=_t("yoy_turnover_rate", lang),
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title="Year"),
        yaxis=dict(title=_t("axis_rate", lang)),
        template=_THEME,
    )
    return _polish(fig)


def yoy_dept_trend_chart(dept_df: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """부서별 연도별 재직 인원 멀티라인 차트."""
    from i18n import t as _t
    if dept_df.empty:
        return _empty_figure(title)

    fig = go.Figure()
    years = [str(y) for y in dept_df.index]

    for i, dept in enumerate(dept_df.columns):
        fig.add_trace(go.Scatter(
            x=years,
            y=dept_df[dept],
            mode="lines+markers",
            name=str(dept),
            line=dict(color=_COLORS[i % len(_COLORS)], width=2),
            marker=dict(size=6),
            hovertemplate=f"{dept}: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title="Year"),
        yaxis=dict(title=_t("axis_count", lang)),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        template=_THEME,
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# D&I 다양성 차트
# ══════════════════════════════════════════════════════════════════════════════

def di_gender_balance_chart(balance_df: "pd.DataFrame", title: str, lang: str = "ko") -> go.Figure:
    """
    부서별 성별 균형 점수 수평 막대 차트.
    색상: 빨강(불균형 0) → 초록(균형 1)
    """
    from i18n import t as _t

    if balance_df.empty:
        return _empty_figure(title)

    depts = balance_df["department"].tolist()
    scores = balance_df["balance_score"].tolist()
    male_r = balance_df["male_ratio"].tolist()
    female_r = balance_df["female_ratio"].tolist()

    colors = [
        f"hsl({int(s * 120)}, 70%, 45%)"   # 0→red(0°), 1→green(120°)
        for s in scores
    ]

    hover = [
        f"<b>{d}</b><br>"
        f"{_t('gender_male', lang)}: {m:.1f}%  {_t('gender_female', lang)}: {f:.1f}%<br>"
        f"{_t('di_balance_score', lang)}: {s:.3f}"
        for d, m, f, s in zip(depts, male_r, female_r, scores)
    ]

    fig = go.Figure(go.Bar(
        x=scores,
        y=depts,
        orientation="h",
        marker_color=colors,
        hovertext=hover,
        hoverinfo="text",
        text=[f"{s:.2f}" for s in scores],
        textposition="outside",
    ))

    fig.add_vline(x=1.0, line=dict(color="green", width=1, dash="dot"),
                  annotation_text="1.0", annotation_position="top")
    fig.add_vline(x=0.5, line=dict(color="orange", width=1, dash="dot"),
                  annotation_text="0.5", annotation_position="top")

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("di_balance_score", lang), range=[0, 1.15]),
        yaxis=dict(title="", autorange="reversed"),
        template=_THEME,
    )
    return _polish(fig)


def di_position_heatmap(matrix_df: "pd.DataFrame", title: str, lang: str = "ko") -> go.Figure:
    """
    직급 × 부서 여성 비율(%) 히트맵.
    파란색(0%) → 빨간색(100%), 50%=흰색
    """
    from i18n import t as _t
    import numpy as np

    if matrix_df.empty:
        return _empty_figure(title)

    z = matrix_df.values
    text = [
        [f"{v:.0f}%" if not (v != v) else "" for v in row]   # NaN check
        for row in z
    ]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=matrix_df.columns.tolist(),
        y=matrix_df.index.tolist(),
        text=text,
        texttemplate="%{text}",
        colorscale=[
            [0.0,  "#2166AC"],   # 0% → 파랑 (남성 우세)
            [0.5,  "#F7F7F7"],   # 50% → 흰색 (균형)
            [1.0,  "#D6604D"],   # 100% → 빨강 (여성 우세)
        ],
        zmin=0, zmax=100,
        colorbar=dict(title="%", ticksuffix="%"),
        hovertemplate="%{y} × %{x}: <b>%{z:.1f}% F</b><extra></extra>",
    ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("axis_department", lang)),
        yaxis=dict(title=_t("axis_position", lang)),
        template=_THEME,
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 코호트 리텐션 차트 (Cohort Retention)
# ══════════════════════════════════════════════════════════════════════════════

def cohort_heatmap(cohort_df: "pd.DataFrame", title: str, lang: str = "ko") -> go.Figure:
    """
    입사 코호트 × 기간별 잔존율 히트맵.
    - x축: 기간 (6/12/18/24/30/36개월)
    - y축: 입사 연도 (코호트)
    - 색상: 잔존율 (0~100%)
    - 셀 텍스트: 퍼센트 값 (측정 불가 셀은 빈칸)
    """
    from i18n import t as _t

    if cohort_df.empty:
        return _empty_figure(title)

    period_cols = [c for c in ["m6", "m12", "m18", "m24", "m30", "m36"] if c in cohort_df.columns]
    period_labels = [f"{int(c[1:])}M" for c in period_cols]

    cohorts = cohort_df["cohort_year"].astype(str).tolist()
    z_vals = cohort_df[period_cols].values.tolist()
    text_vals = [
        [f"{v:.0f}%" if v is not None and str(v) != "nan" else "" for v in row]
        for row in z_vals
    ]

    import numpy as np
    z_numeric = np.array(
        [[v if (v is not None and str(v) != "nan") else float("nan") for v in row] for row in z_vals],
        dtype=float,
    )

    fig = go.Figure(go.Heatmap(
        z=z_numeric,
        x=period_labels,
        y=cohorts,
        text=text_vals,
        texttemplate="%{text}",
        colorscale=[
            [0.0,  "#C73E1D"],
            [0.5,  "#F18F01"],
            [0.75, "#8BC34A"],
            [1.0,  "#1B5E20"],
        ],
        zmin=0, zmax=100,
        colorbar=dict(title="%", ticksuffix="%"),
        hoverongaps=False,
        hovertemplate="%{y} · %{x}: <b>%{z:.1f}%</b><extra></extra>",
    ))

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("cohort_period_label", lang)),
        yaxis=dict(title=_t("cohort_year_label", lang), autorange="reversed"),
        template=_THEME,
    )
    return _polish(fig)


def cohort_survival_chart(cohort_df: "pd.DataFrame", title: str, lang: str = "ko") -> go.Figure:
    """
    코호트별 생존 곡선 (선 차트).
    - x축: 기간 (개월)
    - y축: 잔존율 (%)
    - 라인: 각 입사 연도
    """
    from i18n import t as _t

    if cohort_df.empty:
        return _empty_figure(title)

    period_cols = [c for c in ["m6", "m12", "m18", "m24", "m30", "m36"] if c in cohort_df.columns]
    x_vals = [int(c[1:]) for c in period_cols]

    fig = go.Figure()

    for _, row in cohort_df.iterrows():
        y_vals = []
        x_plot = []
        for col, x in zip(period_cols, x_vals):
            v = row.get(col)
            if v is not None and str(v) != "nan":
                y_vals.append(float(v))
                x_plot.append(x)

        if not y_vals:
            continue

        cohort_label = f"{int(row['cohort_year'])} ({int(row['cohort_size'])} {_t('cohort_ppl_unit', lang)})"
        fig.add_trace(go.Scatter(
            x=x_plot,
            y=y_vals,
            mode="lines+markers",
            name=cohort_label,
            line=dict(width=2),
            marker=dict(size=7),
            hovertemplate=f"{cohort_label}<br>%{{x}}M: <b>%{{y:.1f}}%</b><extra></extra>",
        ))

    fig.add_hline(
        y=50, line_dash="dot", line_color="gray", line_width=1,
        annotation_text="50%", annotation_position="right",
        annotation_font=dict(size=10, color="gray"),
    )

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("cohort_period_label", lang), tickvals=x_vals,
                   ticktext=[f"{x}M" for x in x_vals]),
        yaxis=dict(title=_t("cohort_retention_rate", lang), range=[0, 105]),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        template=_THEME,
        hovermode="x unified",
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 인원 예측 차트 (Forecast)
# ══════════════════════════════════════════════════════════════════════════════

def forecast_chart(forecast_df: "pd.DataFrame", title: str, lang: str = "ko") -> go.Figure:
    """
    인원 예측 차트.
    - 파란 실선: 실제 인원 (historical headcount)
    - 회색 점선: 선형 추세선 (fitted trend over history)
    - 주황 파선: 예측값 (future predicted)
    - 연주황 밴드: ±10% 신뢰 구간
    - 세로 빨간 점선: 오늘 기준선
    """
    import pandas as pd
    from datetime import datetime

    if forecast_df.empty:
        return _empty_figure(title)

    fig = go.Figure()

    # ── ±10% 신뢰 밴드 (fill between lower/upper) ─────────────────────────
    fut = forecast_df[forecast_df["predicted"].notna()].copy()
    if not fut.empty:
        fig.add_trace(go.Scatter(
            x=pd.concat([fut["month"], fut["month"].iloc[::-1]]),
            y=pd.concat([fut["upper"], fut["lower"].iloc[::-1]]),
            fill="toself",
            fillcolor="rgba(255,165,0,0.15)",
            line=dict(color="rgba(255,165,0,0)"),
            name=t("forecast_band", lang),
            hoverinfo="skip",
            showlegend=True,
        ))

    # ── 실제 인원 (파란 실선) ────────────────────────────────────────────
    hist = forecast_df[forecast_df["headcount"].notna()].copy()
    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["month"],
            y=hist["headcount"],
            mode="lines+markers",
            name=t("forecast_actual", lang),
            line=dict(color=_COLORS[0], width=2),
            marker=dict(size=5),
        ))

    # ── 추세선 (회색 점선, 과거 구간) ────────────────────────────────────
    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["month"],
            y=hist["trend"],
            mode="lines",
            name=t("forecast_trend", lang),
            line=dict(color="gray", width=1, dash="dot"),
        ))

    # ── 예측값 (주황 파선) ────────────────────────────────────────────────
    if not fut.empty:
        # 연결을 위해 마지막 실제 지점도 포함
        connect_row = hist.iloc[[-1]][["month", "headcount"]].rename(columns={"headcount": "predicted"})
        fut_plot = pd.concat([connect_row, fut[["month", "predicted"]]], ignore_index=True)
        fig.add_trace(go.Scatter(
            x=fut_plot["month"],
            y=fut_plot["predicted"],
            mode="lines+markers",
            name=t("forecast_predicted", lang),
            line=dict(color="orange", width=2, dash="dash"),
            marker=dict(size=6, symbol="diamond"),
        ))

    # ── 오늘 기준선 ───────────────────────────────────────────────────────
    today = datetime.today()
    fig.add_vline(
        x=today.timestamp() * 1000,
        line=dict(color="red", width=1, dash="dot"),
        annotation_text=t("forecast_today", lang),
        annotation_position="top right",
        annotation_font=dict(size=11, color="red"),
    )

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title="", tickformat="%Y-%m"),
        yaxis=dict(title=t("axis_count", lang)),
        legend=dict(orientation="h", y=-0.18, x=0.5, xanchor="center"),
        template=_THEME,
        hovermode="x unified",
    )
    return _polish(fig)


# ══════════════════════════════════════════════════════════════════════════════
# 내부 유틸
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# 채용 소요시간 (Time-to-Hire) 차트
# ══════════════════════════════════════════════════════════════════════════════

def tth_histogram(series: pd.Series, title: str, lang: str = "ko") -> go.Figure:
    """채용 소요시간 히스토그램."""
    from i18n import t as _t
    if series.empty:
        return _empty_figure(title)

    avg_val = series.mean()
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=series,
        nbinsx=20,
        marker_color=_COLORS[0],
        opacity=0.85,
        name=_t("tth_axis_count", lang),
    ))
    # 평균선
    fig.add_vline(
        x=avg_val,
        line_dash="dash",
        line_color=_COLORS[2],
        line_width=2,
        annotation_text=f'{_t("tth_avg_line", lang)}: {avg_val:.1f}{_t("tth_days", lang)}',
        annotation_position="top right",
        annotation_font_size=12,
    )
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("tth_axis_days", lang)),
        yaxis=dict(title=_t("tth_axis_count", lang)),
        bargap=0.05,
        template=_THEME,
    )
    return _polish(fig)


def tth_by_dept_chart(df_agg: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """부서별 평균·중앙값 채용 소요시간 수평 바차트."""
    from i18n import t as _t
    if df_agg.empty:
        return _empty_figure(title)

    df_agg = df_agg.sort_values("avg")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_agg["department"],
        x=df_agg["avg"],
        orientation="h",
        name=_t("tth_avg", lang),
        marker_color=_COLORS[0],
        text=df_agg["avg"].apply(lambda v: f"{v:.1f}{_t('tth_days', lang)}"),
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        y=df_agg["department"],
        x=df_agg["median"],
        mode="markers",
        name=_t("tth_median", lang),
        marker=dict(symbol="diamond", size=10, color=_COLORS[2]),
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("tth_axis_days", lang)),
        yaxis=dict(title=_t("tth_axis_dept", lang)),
        barmode="group",
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
        template=_THEME,
    )
    return _polish(fig)


def tth_trend_chart(df_trend: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """월별 채용 소요시간 추이 (라인 + 바)."""
    from i18n import t as _t
    if df_trend.empty:
        return _empty_figure(title)

    from plotly.subplots import make_subplots
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=df_trend["year_month"],
        y=df_trend["hires"],
        name=_t("tth_axis_count", lang),
        marker_color=_COLORS[0],
        opacity=0.45,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df_trend["year_month"],
        y=df_trend["avg_tth"],
        name=_t("tth_avg", lang),
        mode="lines+markers",
        line=dict(color=_COLORS[2], width=2.5),
        marker=dict(size=7),
    ), secondary_y=True)

    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title="", tickangle=-30),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center"),
        hovermode="x unified",
        template=_THEME,
    )
    fig.update_yaxes(title_text=_t("tth_axis_count", lang), secondary_y=False)
    fig.update_yaxes(title_text=_t("tth_axis_days", lang), secondary_y=True, showgrid=False)
    return _polish(fig)


def tth_by_position_chart(df_agg: pd.DataFrame, title: str, lang: str = "ko") -> go.Figure:
    """직급별 평균 채용 소요시간 바차트."""
    from i18n import t as _t
    if df_agg.empty:
        return _empty_figure(title)

    df_agg = df_agg.sort_values("avg", ascending=True)
    colors = [_COLORS[i % len(_COLORS)] for i in range(len(df_agg))]
    fig = go.Figure(go.Bar(
        y=df_agg["position"],
        x=df_agg["avg"],
        orientation="h",
        marker_color=colors,
        text=df_agg["avg"].apply(lambda v: f"{v:.1f}{_t('tth_days', lang)}"),
        textposition="outside",
        customdata=df_agg["count"],
        hovertemplate=(
            f"%{{y}}<br>{_t('tth_avg', lang)}: %{{x:.1f}}{_t('tth_days', lang)}"
            f"<br>n=%{{customdata}}<extra></extra>"
        ),
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        xaxis=dict(title=_t("tth_axis_days", lang)),
        yaxis=dict(title=_t("tth_axis_position", lang)),
        template=_THEME,
    )
    return _polish(fig)


def _empty_figure(title: str) -> go.Figure:
    """데이터 없을 때 빈 차트 (안내 메시지 포함)."""
    fig = go.Figure()
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=15)),
        annotations=[dict(
            text="데이터 없음 / No data",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )],
        template=_THEME,
    )
    return _polish(fig)
