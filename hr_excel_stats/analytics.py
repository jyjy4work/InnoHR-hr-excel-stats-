# Design Ref: §3.4 — 모든 통계 계산 함수 (인원/입퇴사/채용/교육/조직)
"""
analytics.py — HR 통계 계산 모듈

정제된 DataFrame(parser.clean_data 결과)을 받아 각종 통계를 계산합니다.
모든 함수는 순수 함수(pure function)로 side-effect 없이 결과를 반환합니다.

Plan SC: 주요 통계 5종 이상 정확 산출
Plan SC: 엑셀 업로드 후 30초 내 대시보드 표시
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from config import AGE_BINS, AGE_LABELS, TENURE_BINS, TENURE_LABELS


# ══════════════════════════════════════════════════════════════════════════════
# 인원 현황 (Headcount)
# ══════════════════════════════════════════════════════════════════════════════

def headcount_total(df: pd.DataFrame) -> int:
    """전체 재직 인원수."""
    active = df[df["is_active"] == True] if "is_active" in df.columns else df
    return len(active)


def headcount_by_dept(df: pd.DataFrame) -> pd.Series:
    """부서별 재직 인원수. 내림차순 정렬."""
    active = _active_only(df)
    if "department" not in active.columns:
        return pd.Series(dtype=int)
    return active["department"].value_counts().sort_values(ascending=False)


def headcount_by_position(df: pd.DataFrame) -> pd.Series:
    """직급별 재직 인원수."""
    active = _active_only(df)
    if "position" not in active.columns:
        return pd.Series(dtype=int)
    return active["position"].value_counts().sort_values(ascending=False)


_GENDER_MAP: dict[str, dict[str, str]] = {
    "ko": {
        "남": "남", "남성": "남", "m": "남", "male": "남", "homme": "남",
        "여": "여", "여성": "여", "f": "여", "female": "여", "femme": "여",
    },
    "en": {
        "남": "Male", "남성": "Male", "m": "Male", "male": "Male", "homme": "Male",
        "여": "Female", "여성": "Female", "f": "Female", "female": "Female", "femme": "Female",
    },
    "fr": {
        "남": "Homme", "남성": "Homme", "m": "Homme", "male": "Homme", "homme": "Homme",
        "여": "Femme", "여성": "Femme", "f": "Femme", "female": "Femme", "femme": "Femme",
    },
}


def headcount_by_gender(df: pd.DataFrame, lang: str = "ko") -> pd.Series:
    """성별 재직 인원수. lang에 따라 레이블 번역."""
    active = _active_only(df)
    if "gender" not in active.columns:
        return pd.Series(dtype=int)
    gmap = _GENDER_MAP.get(lang, _GENDER_MAP["ko"])
    translated = active["gender"].astype(str).str.strip().str.lower().map(
        lambda v: gmap.get(v, v)
    )
    return translated.value_counts()


def headcount_by_age_group(df: pd.DataFrame, lang: str = "ko") -> pd.Series:
    """
    연령대별 재직 인원수.
    age_bin 컬럼이 없으면 빈 Series 반환.
    """
    active = _active_only(df)
    if "age_bin" not in active.columns:
        return pd.Series(dtype=int)
    labels = AGE_LABELS.get(lang, AGE_LABELS["ko"])
    counts = active["age_bin"].value_counts().sort_index()
    # 빈 구간도 0으로 포함
    full_index = range(len(labels))
    counts = counts.reindex(full_index, fill_value=0)
    counts.index = labels
    return counts


def age_gender_pyramid(df: pd.DataFrame, lang: str = "ko") -> pd.DataFrame:
    """
    연령대 × 성별 피라미드 데이터.

    Returns:
        DataFrame with columns [age_label, 남, 여]
        연령대 낮은 순서로 정렬 (차트 위에서 아래로 나이가 늘어나도록).
    """
    active = _active_only(df)
    if "age_bin" not in active.columns or "gender" not in active.columns:
        return pd.DataFrame()
    labels = AGE_LABELS.get(lang, AGE_LABELS["ko"])
    gmap = _GENDER_MAP.get(lang, _GENDER_MAP["ko"])
    # 원본 성별값을 번역
    translated_gender = active["gender"].astype(str).str.strip().str.lower().map(
        lambda v: gmap.get(v, v)
    )
    # 번역된 레이블 (남→Male 등)
    m_label = gmap.get("남", "남")
    f_label = gmap.get("여", "여")
    rows = []
    for i, label in enumerate(labels):
        age_group = translated_gender[active["age_bin"] == i]
        rows.append({
            "age_label": label,
            m_label: int((age_group == m_label).sum()),
            f_label: int((age_group == f_label).sum()),
        })
    return pd.DataFrame(rows)


def headcount_by_employment_type(df: pd.DataFrame) -> pd.Series:
    """고용형태별 재직 인원수."""
    active = _active_only(df)
    if "employment_type" not in active.columns:
        return pd.Series(dtype=int)
    return active["employment_type"].value_counts()


def tenure_distribution(df: pd.DataFrame, lang: str = "ko") -> pd.Series:
    """
    근속연수 구간별 재직 인원수.
    구간: 1년미만 / 1~3년 / 3~5년 / 5~10년 / 10년+
    """
    active = _active_only(df)
    if "tenure_bin" not in active.columns:
        return pd.Series(dtype=int)
    labels = TENURE_LABELS.get(lang, TENURE_LABELS["ko"])
    counts = active["tenure_bin"].value_counts().sort_index()
    full_index = range(len(labels))
    counts = counts.reindex(full_index, fill_value=0)
    counts.index = labels
    return counts


def avg_tenure(df: pd.DataFrame) -> float:
    """전체 재직자 평균 근속연수 (년)."""
    active = _active_only(df)
    if "tenure_years" not in active.columns:
        return 0.0
    valid = active["tenure_years"].dropna()
    return round(float(valid.mean()), 1) if not valid.empty else 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 입퇴사 / 이직 (Attrition)
# ══════════════════════════════════════════════════════════════════════════════

def monthly_hires(
    df: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    월별 입사자 수.

    Returns:
        DataFrame with columns [year_month, hire_count]
    """
    if "hire_year_month" not in df.columns:
        return pd.DataFrame(columns=["year_month", "hire_count"])

    series = df["hire_year_month"].dropna()
    if start:
        series = series[series >= start]
    if end:
        series = series[series <= end]

    counts = series.value_counts().sort_index()
    return counts.reset_index().rename(
        columns={"hire_year_month": "year_month", "count": "hire_count"}
    )


def monthly_resignations(
    df: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    월별 퇴사자 수.

    Returns:
        DataFrame with columns [year_month, resign_count]
    """
    if "resign_year_month" not in df.columns:
        return pd.DataFrame(columns=["year_month", "resign_count"])

    resigned = df[df["is_active"] == False] if "is_active" in df.columns else df
    series = resigned["resign_year_month"].dropna()
    if start:
        series = series[series >= start]
    if end:
        series = series[series <= end]

    counts = series.value_counts().sort_index()
    return counts.reset_index().rename(
        columns={"resign_year_month": "year_month", "count": "resign_count"}
    )


def monthly_hire_resign_combined(
    df: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    월별 입사/퇴사 합산 DataFrame (라인차트용).

    Returns:
        DataFrame with columns [year_month, hire_count, resign_count]
    """
    hires = monthly_hires(df, start, end)
    resigns = monthly_resignations(df, start, end)

    if hires.empty and resigns.empty:
        return pd.DataFrame(columns=["year_month", "hire_count", "resign_count"])

    merged = pd.merge(hires, resigns, on="year_month", how="outer").fillna(0)
    merged["hire_count"] = merged["hire_count"].astype(int)
    merged["resign_count"] = merged["resign_count"].astype(int)
    return merged.sort_values("year_month").reset_index(drop=True)


def turnover_rate(df: pd.DataFrame) -> float:
    """
    전체 이직률 (%) 계산.
    공식: (퇴사자수 / 평균재직자수) × 100
    평균재직자 = (기초인원 + 기말인원) / 2
    """
    total = len(df)
    if total == 0:
        return 0.0

    resigned_count = len(df[df["is_active"] == False]) if "is_active" in df.columns else 0
    active_count = len(df[df["is_active"] == True]) if "is_active" in df.columns else total

    # 평균재직자 = (전체 - 퇴사자 + 전체) / 2 → 근사치
    avg_employees = (total + active_count) / 2
    if avg_employees == 0:
        return 0.0
    return round((resigned_count / avg_employees) * 100, 1)


def turnover_by_dept(df: pd.DataFrame) -> pd.Series:
    """부서별 이직률 (%)."""
    if "department" not in df.columns or "is_active" not in df.columns:
        return pd.Series(dtype=float)

    result = {}
    for dept in df["department"].dropna().unique():
        dept_df = df[df["department"] == dept]
        result[dept] = turnover_rate(dept_df)

    return pd.Series(result).sort_values(ascending=False)


def avg_tenure_by_dept(df: pd.DataFrame) -> pd.Series:
    """부서별 평균 근속연수 (재직자 기준)."""
    active = _active_only(df)
    if "department" not in active.columns or "tenure_years" not in active.columns:
        return pd.Series(dtype=float)

    result = (
        active.groupby("department")["tenure_years"]
        .mean()
        .round(1)
        .sort_values(ascending=False)
    )
    return result


def resign_reason_breakdown(df: pd.DataFrame) -> pd.Series:
    """퇴사 사유별 인원수. resign_reason 컬럼 없으면 빈 Series."""
    if "resign_reason" not in df.columns:
        return pd.Series(dtype=int)
    resigned = df[df["is_active"] == False] if "is_active" in df.columns else df
    return resigned["resign_reason"].dropna().value_counts()


def new_hires_total(df: pd.DataFrame, start: Optional[str] = None, end: Optional[str] = None) -> int:
    """기간 내 총 입사자 수."""
    result = monthly_hires(df, start, end)
    if result.empty:
        return 0
    return int(result["hire_count"].sum())


def resignations_total(df: pd.DataFrame, start: Optional[str] = None, end: Optional[str] = None) -> int:
    """기간 내 총 퇴사자 수."""
    result = monthly_resignations(df, start, end)
    if result.empty:
        return 0
    return int(result["resign_count"].sum())


# ══════════════════════════════════════════════════════════════════════════════
# 추가 통계 (Additional — 데이터 있을 경우)
# ══════════════════════════════════════════════════════════════════════════════

def recruitment_stats(df: pd.DataFrame) -> dict:
    """
    채용 현황 통계.
    채용 관련 컬럼(recruit_channel, recruit_days 등)이 없으면 빈 dict.
    """
    stats = {}
    if "recruit_channel" in df.columns:
        stats["by_channel"] = df["recruit_channel"].value_counts()
    if "recruit_days" in df.columns:
        stats["avg_days"] = round(df["recruit_days"].dropna().mean(), 1)
    return stats


def education_stats(df: pd.DataFrame) -> dict:
    """
    교육/역량 통계.
    교육 관련 컬럼(edu_completed, edu_hours 등)이 없으면 빈 dict.
    """
    stats = {}
    if "edu_completed" in df.columns:
        total = len(df)
        completed = df["edu_completed"].sum() if total > 0 else 0
        stats["completion_rate"] = round((completed / total) * 100, 1) if total > 0 else 0.0
    if "edu_hours" in df.columns:
        stats["avg_hours"] = round(df["edu_hours"].dropna().mean(), 1)
    return stats


def org_structure_stats(df: pd.DataFrame) -> dict:
    """
    조직 구조 통계 (스팬 오브 컨트롤 등).
    manager_id 컬럼이 없으면 부서별 팀 규모로 대체.
    """
    stats = {}
    active = _active_only(df)

    if "department" in active.columns:
        dept_sizes = active["department"].value_counts()
        stats["avg_team_size"] = round(float(dept_sizes.mean()), 1)
        stats["dept_size_distribution"] = dept_sizes

    if "manager_id" in active.columns:
        # 관리자 1명당 부하 직원 수
        managers = active["manager_id"].dropna().nunique()
        if managers > 0:
            stats["avg_span_of_control"] = round(len(active) / managers, 1)

    return stats


# ══════════════════════════════════════════════════════════════════════════════
# 연령 / 성별 복합 통계
# ══════════════════════════════════════════════════════════════════════════════

def avg_age_by_gender(df: pd.DataFrame) -> dict:
    """
    재직자 기준 남/여/전체 평균 나이 (raw 값 기준, 키는 항상 "남"/"여").

    Returns:
        {"all": float, "남": float, "여": float}
        나이 정보 없으면 해당 값 0.0
    """
    _male_vals   = {"남", "남성", "m", "male", "homme"}
    _female_vals = {"여", "여성", "f", "female", "femme"}
    active = _active_only(df)
    if "age" not in active.columns:
        return {"all": 0.0, "남": 0.0, "여": 0.0}

    all_ages = active["age"].dropna()
    result: dict = {"all": round(float(all_ages.mean()), 1) if not all_ages.empty else 0.0}

    if "gender" in active.columns:
        g_lower = active["gender"].astype(str).str.strip().str.lower()
        for key, vals in (("남", _male_vals), ("여", _female_vals)):
            subset = active[g_lower.isin(vals)]["age"].dropna()
            result[key] = round(float(subset.mean()), 1) if not subset.empty else 0.0
    else:
        result["남"] = 0.0
        result["여"] = 0.0

    return result


def dept_gender_ratio(df: pd.DataFrame, lang: str = "ko") -> pd.DataFrame:
    """
    부서별 성별 인원 (누적 가로 막대용).

    Returns:
        DataFrame with columns [department, <male_label>, <female_label>, <other_label>]
        총 인원 내림차순 정렬
    """
    active = _active_only(df)
    if "department" not in active.columns or "gender" not in active.columns:
        return pd.DataFrame()

    gmap = _GENDER_MAP.get(lang, _GENDER_MAP["ko"])
    _other = {"ko": "기타", "en": "Other", "fr": "Autre"}.get(lang, "Other")
    m_label = gmap.get("남", "남")
    f_label = gmap.get("여", "여")

    translated = active.copy()
    translated["gender"] = (
        translated["gender"].astype(str).str.strip().str.lower()
        .map(lambda v: gmap.get(v, _other))
    )

    pivot = (
        translated.groupby(["department", "gender"])
        .size()
        .unstack(fill_value=0)
    )
    for col in (m_label, f_label, _other):
        if col not in pivot.columns:
            pivot[col] = 0

    keep = [c for c in (m_label, f_label, _other) if c in pivot.columns]
    pivot = pivot[keep].copy()
    pivot["_total"] = pivot[keep].sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=False).drop(columns="_total")
    return pivot.reset_index()


def short_tenure_ratio(df: pd.DataFrame) -> float:
    """
    재직자 중 1년 미만 단기 재직 비율 (%).
    이직 위험 선행 지표로 활용.
    """
    active = _active_only(df)
    if "tenure_years" not in active.columns or active.empty:
        return 0.0
    short = (active["tenure_years"] < 1).sum()
    return round(short / len(active) * 100, 1)


def position_age_tenure_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    직급별 평균 나이 + 평균 근속연수 + 인원수 테이블.

    Returns:
        DataFrame with columns [position, count, avg_age, avg_tenure_years]
    """
    active = _active_only(df)
    if "position" not in active.columns:
        return pd.DataFrame()

    agg: dict = {"position": []}
    records = []
    for pos, grp in active.groupby("position"):
        row: dict = {"position": pos, "count": len(grp)}
        if "age" in grp.columns:
            ages = grp["age"].dropna()
            row["avg_age"] = round(float(ages.mean()), 1) if not ages.empty else None
        if "tenure_years" in grp.columns:
            tenures = grp["tenure_years"].dropna()
            row["avg_tenure_years"] = round(float(tenures.mean()), 1) if not tenures.empty else None
        records.append(row)

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(records).sort_values("count", ascending=False).reset_index(drop=True)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 이직 위험 탐지 (Attrition Risk)
# ══════════════════════════════════════════════════════════════════════════════

def attrition_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    재직자별 이직 위험 점수(0~100) 및 등급을 계산.

    점수 구성 (합계 100점 만점):
      - 근속연수 요소 (40점): 1년 미만=40, 1~3년=25, 3~5년=12, 5년+=0
      - 부서 이직률 요소 (40점): 해당 부서 이직률 × 0.6 (최대 40점)
      - 연령 요소 (20점): 20대=20, 30대=12, 40대=5, 50대+=0
        (연령 정보 없으면 0점)

    등급:
      - High   : ≥ 60
      - Medium : 30 ~ 59
      - Low    : < 30

    Returns:
        재직자 DataFrame에 risk_score(float), risk_level(str) 컬럼 추가.
        department, name, employee_id, position, tenure_years, age 등
        원본 컬럼도 함께 포함.
    """
    active = _active_only(df).copy()
    if active.empty:
        return pd.DataFrame()

    # ── 부서별 이직률 사전 계산 ───────────────────────────────────────────
    dept_rates: dict[str, float] = {}
    if "department" in df.columns:
        for dept in df["department"].dropna().unique():
            dept_rates[dept] = turnover_rate(df[df["department"] == dept])

    # ── 행별 점수 계산 ────────────────────────────────────────────────────
    def _score(row) -> float:
        score = 0.0

        # 근속연수 요소
        if pd.notna(row.get("tenure_years")):
            t = row["tenure_years"]
            if t < 1:
                score += 40
            elif t < 3:
                score += 25
            elif t < 5:
                score += 12
            # 5년 이상 = 0

        # 부서 이직률 요소
        dept = row.get("department")
        if dept and dept in dept_rates:
            score += min(dept_rates[dept] * 0.6, 40)

        # 연령 요소
        if pd.notna(row.get("age")):
            age = row["age"]
            if age < 30:
                score += 20
            elif age < 40:
                score += 12
            elif age < 50:
                score += 5
            # 50대 이상 = 0

        return min(round(score, 1), 100.0)

    active["risk_score"] = active.apply(_score, axis=1)

    def _level(score: float) -> str:
        if score >= 60:
            return "High"
        if score >= 30:
            return "Medium"
        return "Low"

    active["risk_level"] = active["risk_score"].apply(_level)
    return active.sort_values("risk_score", ascending=False).reset_index(drop=True)


def risk_summary(risk_df: pd.DataFrame) -> dict:
    """
    이직 위험 요약 통계.

    Returns:
        {
          "high_count": int,
          "medium_count": int,
          "low_count": int,
          "high_pct": float,   # 전체 재직자 대비 %
          "total": int,
          "avg_score": float,
        }
    """
    if risk_df.empty:
        return {"high_count": 0, "medium_count": 0, "low_count": 0,
                "high_pct": 0.0, "total": 0, "avg_score": 0.0}
    total = len(risk_df)
    high   = int((risk_df["risk_level"] == "High").sum())
    medium = int((risk_df["risk_level"] == "Medium").sum())
    low    = int((risk_df["risk_level"] == "Low").sum())
    return {
        "high_count":   high,
        "medium_count": medium,
        "low_count":    low,
        "high_pct":     round(high / total * 100, 1) if total else 0.0,
        "total":        total,
        "avg_score":    round(float(risk_df["risk_score"].mean()), 1),
    }


def risk_by_dept(risk_df: pd.DataFrame) -> pd.DataFrame:
    """
    부서별 High/Medium/Low 인원수.

    Returns:
        DataFrame columns: [department, High, Medium, Low, total, high_pct]
        high_pct 내림차순 정렬
    """
    if risk_df.empty or "department" not in risk_df.columns:
        return pd.DataFrame()

    pivot = (
        risk_df.groupby(["department", "risk_level"])
        .size()
        .unstack(fill_value=0)
    )
    for col in ("High", "Medium", "Low"):
        if col not in pivot.columns:
            pivot[col] = 0
    pivot = pivot[["High", "Medium", "Low"]].copy()
    pivot["total"] = pivot["High"] + pivot["Medium"] + pivot["Low"]
    pivot["high_pct"] = (pivot["High"] / pivot["total"] * 100).round(1)
    return pivot.sort_values("high_pct", ascending=False).reset_index()


# ══════════════════════════════════════════════════════════════════════════════
# 연도별 비교 (YoY)
# ══════════════════════════════════════════════════════════════════════════════

def yoy_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    연도별 HR 핵심 지표.
    Returns DataFrame columns: [year, headcount, new_hires, resignations, turnover_rate, avg_tenure]
    hire_date 없으면 빈 DataFrame.
    """
    if "hire_date" not in df.columns:
        return pd.DataFrame()

    # 연도 범위 결정
    hire_years = df["hire_date"].dropna().dt.year
    if hire_years.empty:
        return pd.DataFrame()

    resign_years = pd.Series(dtype=int)
    if "resign_date" in df.columns:
        resign_years = df["resign_date"].dropna().dt.year

    min_year = int(hire_years.min())
    max_year = int(date.today().year)

    rows = []
    for yr in range(min_year, max_year + 1):
        yr_end = pd.Timestamp(f"{yr}-12-31")
        yr_start = pd.Timestamp(f"{yr}-01-01")

        # 해당 연도 말 재직자: 입사일 <= 연말 AND (퇴사일 없거나 퇴사일 > 연말)
        hired_by_end = df["hire_date"].notna() & (df["hire_date"] <= yr_end)
        if "resign_date" in df.columns:
            not_resigned = df["resign_date"].isna() | (df["resign_date"] > yr_end)
        else:
            not_resigned = pd.Series([True] * len(df), index=df.index)
        active_at_end = df[hired_by_end & not_resigned]
        headcount_end = len(active_at_end)

        # 입사자: 해당 연도에 입사
        new_hires = int((df["hire_date"].dt.year == yr).sum()) if "hire_date" in df.columns else 0

        # 퇴사자: 해당 연도에 퇴사
        if "resign_date" in df.columns:
            resignations = int((df["resign_date"].dt.year == yr).fillna(False).sum())
        else:
            resignations = 0

        # 건너뛰기: 입사자도 퇴사자도 재직자도 없는 연도
        if headcount_end == 0 and new_hires == 0 and resignations == 0:
            continue

        # 전년도 말 재직자 (이직률 분모용)
        if yr > min_year:
            prev_end = pd.Timestamp(f"{yr-1}-12-31")
            hired_by_prev = df["hire_date"].notna() & (df["hire_date"] <= prev_end)
            if "resign_date" in df.columns:
                not_resigned_prev = df["resign_date"].isna() | (df["resign_date"] > prev_end)
            else:
                not_resigned_prev = pd.Series([True] * len(df), index=df.index)
            headcount_start = len(df[hired_by_prev & not_resigned_prev])
        else:
            headcount_start = 0

        avg_denom = (headcount_start + headcount_end) / 2
        if avg_denom == 0:
            avg_denom = max(headcount_end, 1)
        tr = round(resignations / avg_denom * 100, 1)

        # 평균 근속연수 (해당 연도 말 기준 재직자)
        if "hire_date" in active_at_end.columns and not active_at_end.empty:
            tenures = (yr_end - active_at_end["hire_date"]).dt.days / 365.25
            avg_ten = round(float(tenures.dropna().mean()), 1) if not tenures.dropna().empty else 0.0
        else:
            avg_ten = 0.0

        rows.append({
            "year": yr,
            "headcount": headcount_end,
            "new_hires": new_hires,
            "resignations": resignations,
            "turnover_rate": tr,
            "avg_tenure": avg_ten,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def yoy_dept_headcount(df: pd.DataFrame) -> pd.DataFrame:
    """
    부서별 연도별 연말 재직 인원.
    Returns DataFrame: index=year (int), columns=department names (top 8 by latest year)
    """
    if "hire_date" not in df.columns or "department" not in df.columns:
        return pd.DataFrame()

    hire_years = df["hire_date"].dropna().dt.year
    if hire_years.empty:
        return pd.DataFrame()

    min_year = int(hire_years.min())
    max_year = int(date.today().year)
    depts = df["department"].dropna().unique()

    records = {}
    for yr in range(min_year, max_year + 1):
        yr_end = pd.Timestamp(f"{yr}-12-31")
        hired_by_end = df["hire_date"].notna() & (df["hire_date"] <= yr_end)
        if "resign_date" in df.columns:
            not_resigned = df["resign_date"].isna() | (df["resign_date"] > yr_end)
        else:
            not_resigned = pd.Series([True] * len(df), index=df.index)
        active_at_end = df[hired_by_end & not_resigned]
        row = {}
        for dept in depts:
            row[dept] = int((active_at_end["department"] == dept).sum())
        if any(v > 0 for v in row.values()):
            records[yr] = row

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(records).T
    result.index.name = "year"
    # top 8 by latest year
    latest_yr = max(records.keys())
    top_depts = result.loc[latest_yr].sort_values(ascending=False).head(8).index.tolist()
    return result[top_depts]


# ══════════════════════════════════════════════════════════════════════════════
# 부서 상세 (Dept Detail)
# ══════════════════════════════════════════════════════════════════════════════

def dept_detail(df: pd.DataFrame, dept_name: str) -> dict:
    """
    특정 부서의 상세 HR 통계.

    Returns dict:
    {
        "headcount": int,           # 현재 재직자 수
        "new_hires_ytd": int,       # 올해 입사자 수
        "resignations_ytd": int,    # 올해 퇴사자 수
        "turnover_rate": float,     # 해당 부서 이직률
        "avg_tenure": float,        # 평균 근속연수
        "avg_age": float,           # 평균 나이 (없으면 0.0)
        "gender_dist": pd.Series,   # 성별 분포 (남/여/기타)
        "position_dist": pd.Series, # 직급별 인원
        "tenure_dist": pd.Series,   # 근속연수 구간별 인원
        "age_dist": pd.Series,      # 연령대별 인원
        "risk_high_count": int,     # 고위험 직원 수
        "risk_avg_score": float,    # 평균 위험 점수
        "member_table": pd.DataFrame, # 부서원 목록 (이름·직급·근속·나이·위험점수)
    }
    """
    dept_df = df[df["department"] == dept_name].copy() if "department" in df.columns else pd.DataFrame()
    if dept_df.empty:
        return {}

    active = dept_df[dept_df["is_active"] == True] if "is_active" in dept_df.columns else dept_df
    current_year = date.today().year

    # 기본 KPI
    headcount = len(active)

    new_hires_ytd = 0
    if "hire_date" in dept_df.columns:
        new_hires_ytd = int((dept_df["hire_date"].dt.year == current_year).sum())

    resignations_ytd = 0
    if "resign_date" in dept_df.columns:
        resignations_ytd = int((dept_df["resign_date"].dt.year == current_year).fillna(False).sum())

    tr = turnover_rate(dept_df)
    at = avg_tenure(dept_df)

    avg_age_val = 0.0
    if "age" in active.columns:
        ages = active["age"].dropna()
        avg_age_val = round(float(ages.mean()), 1) if not ages.empty else 0.0

    # 분포
    gender_dist = headcount_by_gender(dept_df)
    position_dist = headcount_by_position(dept_df)
    tenure_dist = tenure_distribution(dept_df)
    age_dist = headcount_by_age_group(dept_df)

    # 이직 위험
    risk_df = attrition_risk_scores(dept_df)
    risk_high = int((risk_df["risk_level"] == "High").sum()) if not risk_df.empty else 0
    risk_avg = round(float(risk_df["risk_score"].mean()), 1) if not risk_df.empty else 0.0

    # 부서원 목록
    member_cols = {}
    for col in ["name", "position", "tenure_years", "age", "risk_score", "risk_level"]:
        if col in risk_df.columns:
            member_cols[col] = risk_df[col]
    member_table = risk_df[list(member_cols.keys())].copy() if member_cols else pd.DataFrame()
    if not member_table.empty:
        for num_col in ["tenure_years", "age", "risk_score"]:
            if num_col in member_table.columns:
                member_table[num_col] = member_table[num_col].round(1)

    return {
        "headcount": headcount,
        "new_hires_ytd": new_hires_ytd,
        "resignations_ytd": resignations_ytd,
        "turnover_rate": tr,
        "avg_tenure": at,
        "avg_age": avg_age_val,
        "gender_dist": gender_dist,
        "position_dist": position_dist,
        "tenure_dist": tenure_dist,
        "age_dist": age_dist,
        "risk_high_count": risk_high,
        "risk_avg_score": risk_avg,
        "member_table": member_table,
    }


# ══════════════════════════════════════════════════════════════════════════════
# D&I 다양성 지표 (Diversity & Inclusion)
# ══════════════════════════════════════════════════════════════════════════════

def di_gender_balance(df: pd.DataFrame) -> pd.DataFrame:
    """
    부서별 성별 균형 점수.

    score = 1 − |male_ratio − 0.5| × 2
    1.0 = 완전 균형(50/50), 0.0 = 단일 성별

    Returns:
        DataFrame: department, total, male, female, male_ratio, female_ratio, balance_score
    """
    active = _active_only(df)
    if not has_column(active, "gender", "department"):
        return pd.DataFrame()

    # 남/여 raw 값 모두 인식 (언어 무관하게 계산)
    _male_vals   = {"남", "남성", "m", "male", "homme"}
    _female_vals = {"여", "여성", "f", "female", "femme"}
    rows = []
    for dept, gdf in active.groupby("department"):
        total = len(gdf)
        if total == 0:
            continue
        g_lower = gdf["gender"].astype(str).str.strip().str.lower()
        male   = int(g_lower.isin(_male_vals).sum())
        female = int(g_lower.isin(_female_vals).sum())
        valid = male + female
        if valid == 0:
            continue
        male_ratio = male / valid
        score = 1.0 - abs(male_ratio - 0.5) * 2
        rows.append({
            "department":    dept,
            "total":         total,
            "male":          male,
            "female":        female,
            "male_ratio":    round(male_ratio * 100, 1),
            "female_ratio":  round((1 - male_ratio) * 100, 1),
            "balance_score": round(score, 3),
        })

    return pd.DataFrame(rows).sort_values("balance_score", ascending=False) if rows else pd.DataFrame()


def di_age_diversity(df: pd.DataFrame) -> dict:
    """
    전사 연령 다양성 지수 (Shannon Entropy 기반, 0~1 정규화).

    Returns:
        dict: age_diversity_index(0~1), n_age_groups, dominant_group, dominant_pct
    """
    active = _active_only(df)
    if "age_bin" not in active.columns:
        return {}

    counts = active["age_bin"].value_counts()
    total = counts.sum()
    if total == 0:
        return {}

    probs = counts / total
    entropy = float(-np.sum(probs * np.log(probs + 1e-10)))
    n_groups = len(counts)
    max_entropy = float(np.log(n_groups)) if n_groups > 1 else 1.0
    normalized = entropy / max_entropy if max_entropy > 0 else 0.0

    return {
        "age_diversity_index": round(normalized, 3),
        "n_age_groups":        int(n_groups),
        "dominant_group":      str(counts.idxmax()),
        "dominant_pct":        round(float(counts.max() / total * 100), 1),
    }


def di_position_gender_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    직급 × 부서 여성 비율(%) 매트릭스.

    Returns:
        DataFrame: index=position, columns=department, values=female_ratio(%)
        데이터 없으면 빈 DataFrame.
    """
    active = _active_only(df)
    if not has_column(active, "gender", "department", "position"):
        return pd.DataFrame()

    def _female_pct(s: pd.Series) -> float:
        tot = len(s)
        return round((s == "여").sum() / tot * 100, 1) if tot > 0 else float("nan")

    try:
        matrix = (
            active.groupby(["position", "department"])["gender"]
            .apply(_female_pct)
            .unstack()
        )
    except Exception:
        return pd.DataFrame()

    return matrix


# ══════════════════════════════════════════════════════════════════════════════
# 코호트 리텐션 분석 (Cohort Retention)
# ══════════════════════════════════════════════════════════════════════════════

def cohort_retention(df: pd.DataFrame) -> pd.DataFrame:
    """
    입사 연도별 코호트 리텐션 분석.

    각 코호트(입사 연도)에서 기간별(6/12/18/24/30/36개월) 잔존율을 계산합니다.

    Returns:
        DataFrame columns: cohort_year, cohort_size, m6, m12, m18, m24, m30, m36
        값은 잔존율(%) 또는 None(아직 측정 불가).
        빈 DataFrame: 입사일 컬럼 없거나 데이터 부족.
    """
    if not has_column(df, "hire_date"):
        return pd.DataFrame()

    df2 = df.copy()
    df2["hire_date"] = pd.to_datetime(df2["hire_date"], errors="coerce")
    df2 = df2[df2["hire_date"].notna()]

    if df2.empty:
        return pd.DataFrame()

    has_resign = has_column(df, "resign_date")
    if has_resign:
        df2["resign_date"] = pd.to_datetime(df2["resign_date"], errors="coerce")
    else:
        df2["resign_date"] = pd.NaT

    today = pd.Timestamp.today()
    df2["cohort_year"] = df2["hire_date"].dt.year

    periods_months = [6, 12, 18, 24, 30, 36]
    cohorts = sorted(df2["cohort_year"].dropna().unique())
    rows = []

    for cohort in cohorts:
        cdf = df2[df2["cohort_year"] == cohort].copy()
        cohort_size = len(cdf)
        row: dict = {"cohort_year": int(cohort), "cohort_size": cohort_size}

        for p in periods_months:
            check_dates = cdf["hire_date"] + pd.DateOffset(months=p)
            eligible_mask = check_dates <= today
            eligible_df = cdf[eligible_mask].copy()

            if eligible_df.empty:
                row[f"m{p}"] = None
                continue

            check_dates_e = check_dates[eligible_mask]
            no_resign = eligible_df["resign_date"].isna()
            resigned_later = eligible_df["resign_date"] >= check_dates_e
            survived = int((no_resign | resigned_later).sum())
            row[f"m{p}"] = round(survived / len(eligible_df) * 100, 1)

        rows.append(row)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
# 인원 예측 (Forecast)
# ══════════════════════════════════════════════════════════════════════════════

def headcount_forecast(df: pd.DataFrame, months_ahead: int = 6) -> pd.DataFrame:
    """
    월별 인원 추이를 바탕으로 선형 회귀(numpy polyfit deg=1)로 향후 인원을 예측합니다.

    Returns:
        DataFrame with columns:
            month       - datetime (월 첫째 날)
            headcount   - 실제 인원 (미래 행은 NaN)
            trend       - 선형 회귀 적합 값 (과거 구간)
            predicted   - 예측 값 (미래 구간)
            lower       - 예측 하한 (predicted × 0.9)
            upper       - 예측 상한 (predicted × 1.1)
            slope       - 월별 기울기 (증감 추세)
        빈 DataFrame: 입사일 컬럼 없거나 데이터 부족
    """
    if not has_column(df, "hire_date"):
        return pd.DataFrame()

    df2 = df.copy()
    df2["_hire_month"] = pd.to_datetime(df2["hire_date"], errors="coerce").dt.to_period("M")

    has_resign = has_column(df, "resign_date")
    if has_resign:
        df2["_resign_month"] = pd.to_datetime(df2["resign_date"], errors="coerce").dt.to_period("M")

    hire_min = df2["_hire_month"].dropna().min()
    hire_max = df2["_hire_month"].dropna().max()

    if pd.isna(hire_min) or pd.isna(hire_max) or hire_min == hire_max:
        return pd.DataFrame()

    all_months = pd.period_range(hire_min, hire_max, freq="M")

    monthly_hires = df2.groupby("_hire_month").size()

    headcount_series: list[float] = []
    running = 0
    for m in all_months:
        running += int(monthly_hires.get(m, 0))
        if has_resign:
            running -= int((df2["_resign_month"] == m).sum())
        headcount_series.append(float(max(0, running)))

    n = len(all_months)
    if n < 3:
        return pd.DataFrame()

    x_hist = np.arange(n, dtype=float)
    y_hist = np.array(headcount_series)

    coeffs = np.polyfit(x_hist, y_hist, 1)
    slope, intercept = float(coeffs[0]), float(coeffs[1])

    trend_vals = slope * x_hist + intercept

    # Future months
    future_months = pd.period_range(hire_max + 1, periods=months_ahead, freq="M")
    x_future = np.arange(n, n + months_ahead, dtype=float)
    pred_vals = np.maximum(slope * x_future + intercept, 0.0)

    # Historical rows
    hist_rows = pd.DataFrame({
        "month":      [m.to_timestamp() for m in all_months],
        "headcount":  headcount_series,
        "trend":      trend_vals.tolist(),
        "predicted":  [float("nan")] * n,
        "lower":      [float("nan")] * n,
        "upper":      [float("nan")] * n,
    })

    # Future rows
    fut_rows = pd.DataFrame({
        "month":      [m.to_timestamp() for m in future_months],
        "headcount":  [float("nan")] * months_ahead,
        "trend":      [float("nan")] * months_ahead,
        "predicted":  pred_vals.tolist(),
        "lower":      (pred_vals * 0.9).tolist(),
        "upper":      (pred_vals * 1.1).tolist(),
    })

    result = pd.concat([hist_rows, fut_rows], ignore_index=True)
    result["slope"] = slope
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 종합 요약 (Dashboard용)
# ══════════════════════════════════════════════════════════════════════════════

def summary_kpis(
    df: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> dict:
    """
    대시보드 KPI 요약.

    Returns:
        {
            "total_employees": int,
            "new_hires": int,
            "resignations": int,
            "turnover_rate": float,
            "avg_tenure": float,
        }
    """
    return {
        "total_employees": headcount_total(df),
        "new_hires": new_hires_total(df, start, end),
        "resignations": resignations_total(df, start, end),
        "turnover_rate": turnover_rate(df),
        "avg_tenure": avg_tenure(df),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 내부 유틸
# ══════════════════════════════════════════════════════════════════════════════

def _active_only(df: pd.DataFrame) -> pd.DataFrame:
    """재직자만 필터링. is_active 컬럼 없으면 전체 반환."""
    if "is_active" not in df.columns:
        return df
    return df[df["is_active"] == True]


def has_column(df: pd.DataFrame, *cols: str) -> bool:
    """모든 컬럼이 존재하는지 확인."""
    return all(c in df.columns for c in cols)


# ══════════════════════════════════════════════════════════════════════════════
# 채용 소요시간 (Time-to-Hire)
# ══════════════════════════════════════════════════════════════════════════════

def _tth_source_col(df: pd.DataFrame) -> str | None:
    """채용 소요시간 계산에 사용할 기준 컬럼 반환 (application_date 우선)."""
    for col in ("application_date", "offer_date"):
        if col in df.columns and df[col].notna().any():
            return col
    return None


def tth_series(df: pd.DataFrame) -> pd.Series:
    """
    개인별 채용 소요시간(일) Series 반환.
    application_date → hire_date 우선, 없으면 offer_date → hire_date.
    """
    src = _tth_source_col(df)
    if src is None or "hire_date" not in df.columns:
        return pd.Series(dtype=float)
    mask = df[src].notna() & df["hire_date"].notna()
    days = (
        pd.to_datetime(df.loc[mask, "hire_date"])
        - pd.to_datetime(df.loc[mask, src])
    ).dt.days
    return days[days >= 0].rename("tth_days")


def tth_kpi(df: pd.DataFrame) -> dict:
    """채용 소요시간 핵심 KPI."""
    s = tth_series(df)
    if s.empty:
        return {"avg": None, "median": None, "min": None, "max": None, "n": 0, "source": None}
    return {
        "avg":    round(s.mean(), 1),
        "median": round(s.median(), 1),
        "min":    int(s.min()),
        "max":    int(s.max()),
        "n":      len(s),
        "source": _tth_source_col(df),
    }


def tth_by_department(df: pd.DataFrame) -> pd.DataFrame:
    """부서별 평균/중앙값 채용 소요시간."""
    src = _tth_source_col(df)
    if src is None or "hire_date" not in df.columns or "department" not in df.columns:
        return pd.DataFrame()
    mask = df[src].notna() & df["hire_date"].notna() & df["department"].notna()
    tmp = df[mask].copy()
    tmp["tth_days"] = (
        pd.to_datetime(tmp["hire_date"]) - pd.to_datetime(tmp[src])
    ).dt.days
    tmp = tmp[tmp["tth_days"] >= 0]
    agg = (
        tmp.groupby("department")["tth_days"]
        .agg(avg="mean", median="median", count="count")
        .reset_index()
    )
    agg["avg"] = agg["avg"].round(1)
    agg["median"] = agg["median"].round(1)
    return agg.sort_values("avg", ascending=False)


def tth_by_position(df: pd.DataFrame) -> pd.DataFrame:
    """직급별 평균 채용 소요시간."""
    src = _tth_source_col(df)
    if src is None or "hire_date" not in df.columns or "position" not in df.columns:
        return pd.DataFrame()
    mask = df[src].notna() & df["hire_date"].notna() & df["position"].notna()
    tmp = df[mask].copy()
    tmp["tth_days"] = (
        pd.to_datetime(tmp["hire_date"]) - pd.to_datetime(tmp[src])
    ).dt.days
    tmp = tmp[tmp["tth_days"] >= 0]
    agg = (
        tmp.groupby("position")["tth_days"]
        .agg(avg="mean", count="count")
        .reset_index()
    )
    agg["avg"] = agg["avg"].round(1)
    return agg.sort_values("avg", ascending=False)


def tth_trend_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """입사 월별 평균 채용 소요시간 추이."""
    src = _tth_source_col(df)
    if src is None or "hire_date" not in df.columns:
        return pd.DataFrame()
    mask = df[src].notna() & df["hire_date"].notna()
    tmp = df[mask].copy()
    tmp["tth_days"] = (
        pd.to_datetime(tmp["hire_date"]) - pd.to_datetime(tmp[src])
    ).dt.days
    tmp = tmp[tmp["tth_days"] >= 0]
    tmp["year_month"] = pd.to_datetime(tmp["hire_date"]).dt.to_period("M").astype(str)
    trend = (
        tmp.groupby("year_month")["tth_days"]
        .agg(avg_tth="mean", hires="count")
        .reset_index()
    )
    trend["avg_tth"] = trend["avg_tth"].round(1)
    return trend.sort_values("year_month")


def tth_distribution(df: pd.DataFrame, bins: int = 10) -> pd.Series:
    """채용 소요시간 히스토그램용 raw 시리즈 반환."""
    return tth_series(df)
