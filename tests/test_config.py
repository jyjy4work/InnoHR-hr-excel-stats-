"""
test_config.py — config.py 상수 및 설정 검증 테스트

L1: 설정 상수 존재 및 타입 검증
"""

import pytest
from config import (
    ACTIVE_VALUES,
    AGE_BINS,
    AGE_LABELS,
    APP_CONFIG,
    COLUMN_MAP,
    INACTIVE_VALUES,
    LANGUAGE_CODES,
    OPTIONAL_COLUMNS,
    REQUIRED_COLUMNS,
    SUPPORTED_LANGUAGES,
    TENURE_BINS,
    TENURE_LABELS,
)


class TestColumnMap:
    """COLUMN_MAP 검증"""

    def test_column_map_has_required_keys(self):
        """필수 표준 컬럼이 모두 정의되어 있어야 함."""
        required_keys = [
            "employee_id", "name", "department", "position",
            "gender", "birth_date", "hire_date", "employment_type",
            "is_active", "resign_date", "resign_reason",
        ]
        for key in required_keys:
            assert key in COLUMN_MAP, f"COLUMN_MAP에 '{key}' 없음"

    def test_column_map_values_are_lists(self):
        """각 컬럼 매핑은 리스트여야 함."""
        for key, values in COLUMN_MAP.items():
            assert isinstance(values, list), f"{key}: list가 아님"
            assert len(values) > 0, f"{key}: 별칭 목록이 비어있음"

    def test_required_columns_are_subset_of_column_map(self):
        """REQUIRED_COLUMNS는 COLUMN_MAP의 부분집합이어야 함."""
        for col in REQUIRED_COLUMNS:
            assert col in COLUMN_MAP, f"REQUIRED_COLUMNS의 '{col}'이 COLUMN_MAP에 없음"

    def test_korean_aliases_exist(self):
        """주요 컬럼에 한국어 별칭이 존재해야 함."""
        korean_checks = {
            "employee_id": "사번",
            "department": "부서",
            "hire_date": "입사일",
            "is_active": "재직여부",
        }
        for col, korean in korean_checks.items():
            assert korean in COLUMN_MAP[col], f"{col}에 한국어 별칭 '{korean}' 없음"

    def test_english_aliases_exist(self):
        """주요 컬럼에 영문 소문자 별칭이 존재해야 함."""
        for key in COLUMN_MAP:
            aliases_lower = [a.lower() for a in COLUMN_MAP[key]]
            assert key.lower() in aliases_lower or any(
                key in a for a in COLUMN_MAP[key]
            ), f"{key}: 영문 별칭 없음"


class TestRequiredColumns:
    """REQUIRED_COLUMNS 검증"""

    def test_four_required_columns(self):
        """필수 컬럼은 4개여야 함 (설계 §3.3)."""
        assert len(REQUIRED_COLUMNS) == 4

    def test_required_columns_content(self):
        """필수 컬럼은 employee_id, department, hire_date, is_active."""
        assert set(REQUIRED_COLUMNS) == {"employee_id", "department", "hire_date", "is_active"}


class TestLanguageConfig:
    """언어 설정 검증"""

    def test_supported_languages(self):
        """한국어/English/Français 3개 언어 지원."""
        assert "한국어" in SUPPORTED_LANGUAGES
        assert "English" in SUPPORTED_LANGUAGES
        assert "Français" in SUPPORTED_LANGUAGES

    def test_language_codes_mapping(self):
        """언어명 → 코드 매핑 정확성."""
        assert LANGUAGE_CODES["한국어"] == "ko"
        assert LANGUAGE_CODES["English"] == "en"
        assert LANGUAGE_CODES["Français"] == "fr"

    def test_all_supported_languages_have_codes(self):
        """지원 언어가 모두 코드를 가져야 함."""
        for lang in SUPPORTED_LANGUAGES:
            assert lang in LANGUAGE_CODES


class TestAppConfig:
    """APP_CONFIG 검증"""

    def test_max_file_size(self):
        """최대 파일 크기 50MB."""
        assert APP_CONFIG["max_file_size_mb"] == 50

    def test_chart_theme(self):
        """차트 테마 plotly_white."""
        assert APP_CONFIG["chart_theme"] == "plotly_white"

    def test_chart_font_includes_malgun(self):
        """한국어 폰트 Malgun Gothic 포함."""
        assert "Malgun Gothic" in APP_CONFIG["chart_font_family"]

    def test_chart_colors_count(self):
        """차트 색상 10개 이상."""
        assert len(APP_CONFIG["chart_colors"]) >= 10


class TestBinLabels:
    """근속연수/연령 구간 검증"""

    def test_tenure_bins_count(self):
        """근속 구간: 6개 경계값 (5구간)."""
        assert len(TENURE_BINS) == 6

    def test_tenure_labels_three_languages(self):
        """근속 레이블: ko/en/fr 3개 언어."""
        assert set(TENURE_LABELS.keys()) == {"ko", "en", "fr"}

    def test_tenure_labels_five_items(self):
        """근속 레이블: 각 언어 5개."""
        for lang, labels in TENURE_LABELS.items():
            assert len(labels) == 5, f"{lang}: 근속 레이블 5개가 아님"

    def test_age_bins_count(self):
        """연령 구간: 6개 경계값 (5구간)."""
        assert len(AGE_BINS) == 6

    def test_age_labels_three_languages(self):
        """연령 레이블: ko/en/fr."""
        assert set(AGE_LABELS.keys()) == {"ko", "en", "fr"}

    def test_age_labels_five_items(self):
        """연령 레이블: 각 언어 5개."""
        for lang, labels in AGE_LABELS.items():
            assert len(labels) == 5, f"{lang}: 연령 레이블 5개가 아님"


class TestActiveValues:
    """재직 여부 값 정규화 검증"""

    def test_active_values_contain_common_truthy(self):
        """재직 값에 Y, True, 재직 포함."""
        assert "Y" in ACTIVE_VALUES
        assert True in ACTIVE_VALUES
        assert "재직" in ACTIVE_VALUES

    def test_inactive_values_contain_common_falsy(self):
        """퇴사 값에 N, False, 퇴사 포함."""
        assert "N" in INACTIVE_VALUES
        assert False in INACTIVE_VALUES
        assert "퇴사" in INACTIVE_VALUES

    def test_no_overlap_between_active_inactive(self):
        """재직/퇴사 값이 겹치지 않아야 함 (True/False 제외)."""
        # 문자열 값만 비교
        active_str = {v for v in ACTIVE_VALUES if isinstance(v, str)}
        inactive_str = {v for v in INACTIVE_VALUES if isinstance(v, str)}
        overlap = active_str & inactive_str
        assert len(overlap) == 0, f"겹치는 값: {overlap}"
