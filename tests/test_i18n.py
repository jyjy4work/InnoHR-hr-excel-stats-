"""
test_i18n.py — i18n.py 다국어 번역 테스트

L1: 번역 함수 동작 / L2: 키 커버리지 / L3: 3개 언어 동등성
"""

import pytest
from i18n import TRANSLATIONS, get_age_labels, get_tenure_labels, t


class TestTranslationFunction:
    """t() 함수 기본 동작 테스트"""

    def test_returns_korean_by_default(self):
        """기본 언어는 ko."""
        result = t("app_title")
        assert result == TRANSLATIONS["ko"]["app_title"]

    def test_returns_correct_lang(self):
        """언어 코드별 정확한 번역 반환."""
        assert t("app_title", "ko") != t("app_title", "en")
        assert t("app_title", "ko") != t("app_title", "fr")

    def test_fallback_to_key_on_missing(self):
        """번역 키가 없으면 키 자체를 반환 (에러 없음)."""
        result = t("nonexistent_key_xyz", "ko")
        assert result == "nonexistent_key_xyz"

    def test_fallback_to_ko_if_lang_missing(self):
        """알 수 없는 언어 코드 → ko 폴백."""
        result = t("app_title", "xx")
        assert result == TRANSLATIONS["ko"]["app_title"]

    def test_format_kwargs(self):
        """포맷 인자(kwargs) 치환 동작."""
        result = t("error_column_missing", "ko", cols="사번, 부서")
        assert "사번" in result or "{cols}" not in result

    def test_all_three_languages_have_app_title(self):
        """3개 언어 모두 app_title 보유."""
        for lang in ("ko", "en", "fr"):
            result = t("app_title", lang)
            assert result != "app_title", f"{lang}: app_title 미번역"


class TestTranslationCoverage:
    """번역 키 커버리지 테스트"""

    CRITICAL_KEYS = [
        # 앱 기본
        "app_title", "upload_title", "analyze_btn",
        # 탭
        "tab_dashboard", "tab_headcount", "tab_attrition", "tab_additional",
        # KPI
        "total_employees", "new_hires", "resignations", "turnover_rate", "avg_tenure",
        # 차트 제목
        "chart_dept_dist", "chart_position_dist", "chart_gender_ratio",
        "chart_age_dist", "chart_tenure_dist", "chart_monthly_hire",
        "chart_turnover_by_dept",
        # 다운로드
        "download_excel", "download_csv",
        # Excel 시트명
        "sheet_headcount", "sheet_attrition", "sheet_additional", "sheet_raw",
        # 오류
        "error_no_file", "error_column_missing",
    ]

    @pytest.mark.parametrize("key", CRITICAL_KEYS)
    def test_key_exists_in_all_languages(self, key):
        """핵심 키가 ko/en/fr 모두에 존재해야 함."""
        for lang in ("ko", "en", "fr"):
            result = t(key, lang)
            assert result != key, f"'{key}' 키가 {lang}에 없음 (키 그대로 반환됨)"

    def test_ko_has_most_keys(self):
        """ko는 50개 이상의 키를 보유해야 함."""
        assert len(TRANSLATIONS["ko"]) >= 50

    def test_en_coverage_vs_ko(self):
        """en은 ko 키의 70% 이상 커버해야 함."""
        ko_keys = set(TRANSLATIONS["ko"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())
        coverage = len(en_keys & ko_keys) / len(ko_keys)
        assert coverage >= 0.70, f"en 커버리지 {coverage:.0%} < 70%"

    def test_fr_coverage_vs_ko(self):
        """fr은 ko 키의 70% 이상 커버해야 함."""
        ko_keys = set(TRANSLATIONS["ko"].keys())
        fr_keys = set(TRANSLATIONS["fr"].keys())
        coverage = len(fr_keys & ko_keys) / len(ko_keys)
        assert coverage >= 0.70, f"fr 커버리지 {coverage:.0%} < 70%"

    def test_axis_labels_exist(self):
        """차트 축 레이블이 존재해야 함."""
        axis_keys = ["axis_count", "axis_year_month"]
        for key in axis_keys:
            for lang in ("ko", "en", "fr"):
                assert t(key, lang) != key, f"'{key}' 없음 ({lang})"

    def test_filter_keys_exist(self):
        """필터 레이블이 존재해야 함."""
        for lang in ("ko", "en", "fr"):
            assert t("filter_department", lang) != "filter_department"
            assert t("filter_all", lang) != "filter_all"


class TestHelperFunctions:
    """get_tenure_labels / get_age_labels 헬퍼 테스트"""

    def test_get_tenure_labels_ko(self):
        """한국어 근속 레이블 5개 반환."""
        labels = get_tenure_labels("ko")
        assert len(labels) == 5
        assert "1년 미만" in labels

    def test_get_tenure_labels_en(self):
        """영어 근속 레이블 5개 반환."""
        labels = get_tenure_labels("en")
        assert len(labels) == 5
        assert "< 1 yr" in labels

    def test_get_tenure_labels_fr(self):
        """프랑스어 근속 레이블 5개 반환."""
        labels = get_tenure_labels("fr")
        assert len(labels) == 5
        assert "< 1 an" in labels

    def test_get_age_labels_ko(self):
        """한국어 연령 레이블 5개 반환."""
        labels = get_age_labels("ko")
        assert len(labels) == 5
        assert "20대" in labels

    def test_get_age_labels_en(self):
        """영어 연령 레이블 5개 반환."""
        labels = get_age_labels("en")
        assert len(labels) == 5
        assert "20s" in labels

    def test_get_age_labels_fr(self):
        """프랑스어 연령 레이블 5개 반환."""
        labels = get_age_labels("fr")
        assert len(labels) == 5
        assert "20 ans" in labels

    def test_unknown_lang_fallback(self):
        """알 수 없는 언어 → ko 폴백."""
        labels = get_tenure_labels("xx")
        assert labels == get_tenure_labels("ko")


class TestSheetNames:
    """Excel 시트명 다국어 검증"""

    def test_sheet_names_are_unique_per_lang(self):
        """같은 언어 내에서 시트명이 중복되지 않아야 함."""
        sheet_keys = ["sheet_headcount", "sheet_attrition", "sheet_additional", "sheet_raw"]
        for lang in ("ko", "en", "fr"):
            names = [t(k, lang) for k in sheet_keys]
            assert len(names) == len(set(names)), f"{lang}: 시트명 중복"

    def test_sheet_names_differ_by_language(self):
        """ko/en 시트명은 서로 달라야 함."""
        ko_name = t("sheet_headcount", "ko")
        en_name = t("sheet_headcount", "en")
        assert ko_name != en_name
