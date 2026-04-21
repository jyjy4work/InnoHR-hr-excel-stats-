"""
test_analytics.py — analytics.py 통계 계산 함수 테스트

L2: 17개 통계 함수 검증 / L3: 엣지케이스 (빈 데이터, 선택 컬럼 없음)
"""

import pandas as pd
import pytest

from analytics import (
    avg_tenure,
    avg_tenure_by_dept,
    headcount_by_age_group,
    headcount_by_dept,
    headcount_by_employment_type,
    headcount_by_gender,
    headcount_by_position,
    headcount_total,
    monthly_hire_resign_combined,
    monthly_hires,
    monthly_resignations,
    org_structure_stats,
    resign_reason_breakdown,
    summary_kpis,
    tenure_distribution,
    turnover_by_dept,
    turnover_rate,
)


# ══════════════════════════════════════════════════════════════════════════════
# 인원 현황 (Headcount)
# ══════════════════════════════════════════════════════════════════════════════

class TestHeadcountTotal:
    """headcount_total() 테스트"""

    def test_counts_active_only(self, sample_df_clean):
        """재직자만 카운트 (7명)."""
        assert headcount_total(sample_df_clean) == 7

    def test_empty_df_returns_zero(self, empty_df):
        """빈 DataFrame → 0."""
        assert headcount_total(empty_df) == 0

    def test_no_is_active_column(self):
        """is_active 컬럼 없으면 전체 카운트."""
        df = pd.DataFrame({"employee_id": ["E1", "E2", "E3"]})
        assert headcount_total(df) == 3


class TestHeadcountByDept:
    """headcount_by_dept() 테스트"""

    def test_returns_series(self, sample_df_clean):
        """Series 반환."""
        result = headcount_by_dept(sample_df_clean)
        assert isinstance(result, pd.Series)

    def test_three_departments(self, sample_df_clean):
        """3개 부서가 존재해야 함."""
        result = headcount_by_dept(sample_df_clean)
        assert len(result) == 3

    def test_dev_team_count(self, sample_df_clean):
        """개발팀 재직자 3명."""
        result = headcount_by_dept(sample_df_clean)
        assert result["개발팀"] == 3

    def test_sorted_descending(self, sample_df_clean):
        """내림차순 정렬."""
        result = headcount_by_dept(sample_df_clean)
        values = result.tolist()
        assert values == sorted(values, reverse=True)

    def test_missing_department_column_returns_empty(self):
        """department 컬럼 없음 → 빈 Series."""
        df = pd.DataFrame({"employee_id": ["E1"], "is_active": [True]})
        result = headcount_by_dept(df)
        assert result.empty


class TestHeadcountByGender:
    """headcount_by_gender() 테스트"""

    def test_returns_series(self, sample_df_clean):
        result = headcount_by_gender(sample_df_clean)
        assert isinstance(result, pd.Series)

    def test_male_female_counts(self, sample_df_clean):
        """재직자 남/여 비율 확인."""
        result = headcount_by_gender(sample_df_clean)
        # 재직자 7명: 남 4명, 여 3명
        assert result["남"] == 4
        assert result["여"] == 3

    def test_missing_gender_returns_empty(self):
        """gender 컬럼 없음 → 빈 Series."""
        df = pd.DataFrame({"is_active": [True, True]})
        result = headcount_by_gender(df)
        assert result.empty


class TestHeadcountByAgeGroup:
    """headcount_by_age_group() 테스트"""

    def test_returns_series(self, sample_df_clean):
        result = headcount_by_age_group(sample_df_clean)
        assert isinstance(result, pd.Series)

    def test_five_age_groups(self, sample_df_clean):
        """5개 연령 구간 (0 포함)."""
        result = headcount_by_age_group(sample_df_clean)
        assert len(result) == 5

    def test_all_groups_have_values(self, sample_df_clean):
        """모든 구간이 정수 값을 가짐."""
        result = headcount_by_age_group(sample_df_clean)
        assert (result >= 0).all()

    def test_language_labels(self, sample_df_clean):
        """언어별 레이블 변경."""
        ko_result = headcount_by_age_group(sample_df_clean, "ko")
        en_result = headcount_by_age_group(sample_df_clean, "en")
        assert list(ko_result.index) != list(en_result.index)


class TestTenureDistribution:
    """tenure_distribution() 테스트"""

    def test_returns_series(self, sample_df_clean):
        result = tenure_distribution(sample_df_clean)
        assert isinstance(result, pd.Series)

    def test_five_bins(self, sample_df_clean):
        """5개 근속 구간."""
        result = tenure_distribution(sample_df_clean)
        assert len(result) == 5

    def test_total_equals_active_count(self, sample_df_clean):
        """구간 합계 = 재직자 수 (7명)."""
        result = tenure_distribution(sample_df_clean)
        assert result.sum() == 7


class TestAvgTenure:
    """avg_tenure() 테스트"""

    def test_returns_float(self, sample_df_clean):
        result = avg_tenure(sample_df_clean)
        assert isinstance(result, float)

    def test_positive_tenure(self, sample_df_clean):
        """평균 근속 > 0."""
        result = avg_tenure(sample_df_clean)
        assert result > 0

    def test_reasonable_range(self, sample_df_clean):
        """평균 근속 0~50년 범위."""
        result = avg_tenure(sample_df_clean)
        assert 0 < result < 50

    def test_empty_returns_zero(self, empty_df):
        """빈 DataFrame → 0.0."""
        assert avg_tenure(empty_df) == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 입퇴사 / 이직 (Attrition)
# ══════════════════════════════════════════════════════════════════════════════

class TestMonthlyHires:
    """monthly_hires() 테스트"""

    def test_returns_dataframe(self, sample_df_clean):
        result = monthly_hires(sample_df_clean)
        assert isinstance(result, pd.DataFrame)

    def test_has_required_columns(self, sample_df_clean):
        """year_month, hire_count 컬럼 포함."""
        result = monthly_hires(sample_df_clean)
        assert "year_month" in result.columns
        assert "hire_count" in result.columns

    def test_year_month_format(self, sample_df_clean):
        """YYYY-MM 형식."""
        result = monthly_hires(sample_df_clean)
        if not result.empty:
            sample_ym = result["year_month"].iloc[0]
            assert len(sample_ym) == 7
            assert sample_ym[4] == "-"

    def test_date_filter_start(self, sample_df_clean):
        """시작 날짜 필터."""
        result = monthly_hires(sample_df_clean, start="2022-01")
        assert not result.empty
        # 2015년 이전 데이터 없어야 함
        assert (result["year_month"] >= "2022-01").all()

    def test_total_hires_count(self, sample_df_clean):
        """입사자 합계 = 10명."""
        result = monthly_hires(sample_df_clean)
        assert result["hire_count"].sum() == 10


class TestMonthlyResignations:
    """monthly_resignations() 테스트"""

    def test_returns_dataframe(self, sample_df_clean):
        result = monthly_resignations(sample_df_clean)
        assert isinstance(result, pd.DataFrame)

    def test_resign_count_matches(self, sample_df_clean):
        """퇴사자 합계 = 3명."""
        result = monthly_resignations(sample_df_clean)
        assert result["resign_count"].sum() == 3


class TestMonthlyHireResignCombined:
    """monthly_hire_resign_combined() 테스트"""

    def test_returns_dataframe(self, sample_df_clean):
        result = monthly_hire_resign_combined(sample_df_clean)
        assert isinstance(result, pd.DataFrame)

    def test_has_three_columns(self, sample_df_clean):
        """year_month, hire_count, resign_count."""
        result = monthly_hire_resign_combined(sample_df_clean)
        assert set(["year_month", "hire_count", "resign_count"]).issubset(result.columns)

    def test_no_negative_values(self, sample_df_clean):
        """음수 없음."""
        result = monthly_hire_resign_combined(sample_df_clean)
        assert (result["hire_count"] >= 0).all()
        assert (result["resign_count"] >= 0).all()

    def test_sorted_by_year_month(self, sample_df_clean):
        """year_month 오름차순 정렬."""
        result = monthly_hire_resign_combined(sample_df_clean)
        if len(result) > 1:
            assert list(result["year_month"]) == sorted(result["year_month"].tolist())


class TestTurnoverRate:
    """turnover_rate() 테스트"""

    def test_returns_float(self, sample_df_clean):
        result = turnover_rate(sample_df_clean)
        assert isinstance(result, float)

    def test_non_negative(self, sample_df_clean):
        """이직률 ≥ 0."""
        result = turnover_rate(sample_df_clean)
        assert result >= 0

    def test_reasonable_range(self, sample_df_clean):
        """이직률 0~100% 범위."""
        result = turnover_rate(sample_df_clean)
        assert 0 <= result <= 100

    def test_empty_returns_zero(self, empty_df):
        assert turnover_rate(empty_df) == 0.0


class TestTurnoverByDept:
    """turnover_by_dept() 테스트"""

    def test_returns_series_or_dict(self, sample_df_clean):
        result = turnover_by_dept(sample_df_clean)
        assert isinstance(result, (pd.Series, dict))

    def test_all_values_non_negative(self, sample_df_clean):
        """모든 이직률 ≥ 0."""
        result = turnover_by_dept(sample_df_clean)
        if isinstance(result, pd.Series):
            assert (result >= 0).all()


class TestResignReasonBreakdown:
    """resign_reason_breakdown() 테스트"""

    def test_returns_series(self, sample_df_clean):
        result = resign_reason_breakdown(sample_df_clean)
        assert isinstance(result, (pd.Series, type(None)))

    def test_voluntary_resign_exists(self, sample_df_clean):
        """자발적퇴사 항목 존재."""
        result = resign_reason_breakdown(sample_df_clean)
        if result is not None and not result.empty:
            assert "자발적퇴사" in result.index


# ══════════════════════════════════════════════════════════════════════════════
# 추가 통계 (Additional)
# ══════════════════════════════════════════════════════════════════════════════

class TestOrgStructureStats:
    """org_structure_stats() 테스트"""

    def test_returns_dict(self, sample_df_clean):
        result = org_structure_stats(sample_df_clean)
        assert isinstance(result, dict)

    def test_empty_df_returns_dict(self, empty_df):
        result = org_structure_stats(empty_df)
        assert isinstance(result, dict)


class TestSummaryKpis:
    """summary_kpis() 대시보드 KPI 통합 테스트"""

    def test_returns_dict(self, sample_df_clean):
        result = summary_kpis(sample_df_clean)
        assert isinstance(result, dict)

    def test_has_five_kpis(self, sample_df_clean):
        """5개 KPI 포함."""
        result = summary_kpis(sample_df_clean)
        required = {"total_employees", "new_hires", "resignations", "turnover_rate", "avg_tenure"}
        assert required.issubset(result.keys()), f"누락 KPI: {required - set(result.keys())}"

    def test_total_employees_correct(self, sample_df_clean):
        """total_employees = 재직자 수 (7)."""
        result = summary_kpis(sample_df_clean)
        assert result["total_employees"] == 7

    def test_resignations_correct(self, sample_df_clean):
        """resignations = 3."""
        result = summary_kpis(sample_df_clean)
        assert result["resignations"] == 3

    def test_all_values_numeric(self, sample_df_clean):
        """모든 KPI 값이 숫자."""
        result = summary_kpis(sample_df_clean)
        for key, val in result.items():
            assert isinstance(val, (int, float)), f"{key}: 숫자가 아님 ({type(val)})"

    def test_empty_df_does_not_raise(self, empty_df):
        """빈 DataFrame에서도 에러 없음."""
        result = summary_kpis(empty_df)
        assert isinstance(result, dict)
