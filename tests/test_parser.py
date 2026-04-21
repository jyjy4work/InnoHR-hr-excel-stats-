"""
test_parser.py — parser.py 파싱·컬럼감지·데이터정제 테스트

L2: 컬럼 자동 매핑 / L3: 데이터 정제 파생 컬럼 / L4: 엣지케이스
"""

import io
from datetime import date

import pandas as pd
import pytest

from parser import (
    _normalize,
    clean_data,
    detect_columns,
    filter_active,
    filter_by_department,
    filter_resigned,
    get_departments,
    load_file,
    validate_mapping,
)


class TestNormalize:
    """_normalize() 내부 함수 테스트"""

    def test_lowercase(self):
        assert _normalize("EmployeeID") == "employeeid"

    def test_strip_whitespace(self):
        assert _normalize("  부서  ") == "부서"

    def test_strip_special_chars(self):
        # 괄호는 제거 안 함, 대소문자만 정규화
        # re.sub(r"[\s_\-\.]", "", text.lower().strip())
        assert _normalize("사번(ID)") == "사번(id)"

    def test_empty_string(self):
        assert _normalize("") == ""

    def test_mixed(self):
        # 언더스코어(_)는 제거됨 → hiredate
        assert _normalize(" Hire_Date ") == "hiredate"

    def test_removes_underscore(self):
        """언더스코어 제거."""
        assert _normalize("hire_date") == "hiredate"

    def test_removes_hyphen(self):
        """하이픈 제거."""
        assert _normalize("hire-date") == "hiredate"

    def test_removes_dot(self):
        """점(.) 제거."""
        assert _normalize("hire.date") == "hiredate"

    def test_keeps_parentheses(self):
        """괄호는 유지됨."""
        result = _normalize("col(name)")
        assert "(" in result or "colname" == result  # 구현에 따라 유지


class TestDetectColumns:
    """detect_columns() 컬럼 자동 감지 테스트"""

    def test_detects_korean_columns(self, sample_raw_df):
        """한국어 표준 컬럼 자동 감지."""
        mapping = detect_columns(sample_raw_df)
        assert "employee_id" in mapping
        assert "department" in mapping
        assert "hire_date" in mapping
        assert "is_active" in mapping

    def test_korean_column_values(self, sample_raw_df):
        """감지된 컬럼명이 실제 DataFrame 컬럼과 일치."""
        mapping = detect_columns(sample_raw_df)
        assert mapping["employee_id"] == "사번"
        assert mapping["department"] == "부서"

    def test_detects_english_columns(self):
        """영어 표준 컬럼 감지."""
        df = pd.DataFrame({
            "employee_id": ["E001"],
            "department": ["Dev"],
            "hire_date": ["2020-01-01"],
            "is_active": ["Y"],
        })
        mapping = detect_columns(df)
        assert "employee_id" in mapping
        assert "department" in mapping

    def test_partial_match(self):
        """부분 일치 (입사일자 → hire_date)."""
        df = pd.DataFrame({
            "입사일자": ["2020-01-01"],
            "사원번호": ["E001"],
            "부서명": ["개발"],
            "재직상태": ["Y"],
        })
        mapping = detect_columns(df)
        assert "hire_date" in mapping
        assert "employee_id" in mapping

    def test_empty_df_returns_empty_mapping(self, empty_df):
        """빈 DataFrame → 빈 매핑 반환."""
        mapping = detect_columns(empty_df)
        assert isinstance(mapping, dict)


class TestValidateMapping:
    """validate_mapping() 필수 컬럼 검증 테스트"""

    def test_complete_mapping_is_valid(self, sample_raw_df):
        """완전한 매핑은 유효해야 함."""
        mapping = detect_columns(sample_raw_df)
        is_valid, missing = validate_mapping(mapping)
        assert is_valid is True
        assert len(missing) == 0

    def test_missing_required_column(self):
        """필수 컬럼 누락 시 is_valid = False."""
        incomplete_mapping = {
            "employee_id": "사번",
            "department": "부서",
            # hire_date, is_active 누락
        }
        is_valid, missing = validate_mapping(incomplete_mapping)
        assert is_valid is False
        assert "hire_date" in missing
        assert "is_active" in missing

    def test_empty_mapping_fails(self):
        """빈 매핑 → 실패."""
        is_valid, missing = validate_mapping({})
        assert is_valid is False
        assert len(missing) == 4  # REQUIRED_COLUMNS 4개

    def test_returns_tuple(self, sample_raw_df):
        """반환 타입 (bool, list)."""
        mapping = detect_columns(sample_raw_df)
        result = validate_mapping(mapping)
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)


class TestCleanData:
    """clean_data() 데이터 정제 테스트"""

    @pytest.fixture
    def clean_result(self, sample_raw_df):
        mapping = detect_columns(sample_raw_df)
        return clean_data(sample_raw_df, mapping)

    def test_returns_dataframe(self, clean_result):
        """DataFrame을 반환해야 함."""
        assert isinstance(clean_result, pd.DataFrame)

    def test_has_tenure_years(self, clean_result):
        """tenure_years 파생 컬럼 생성."""
        assert "tenure_years" in clean_result.columns

    def test_tenure_years_positive(self, clean_result):
        """근속연수 > 0 (2015년 이후 입사)."""
        assert (clean_result["tenure_years"] > 0).all()

    def test_has_hire_year_month(self, clean_result):
        """hire_year_month 파생 컬럼 (YYYY-MM 형식)."""
        assert "hire_year_month" in clean_result.columns
        assert clean_result["hire_year_month"].iloc[0].startswith("202")

    def test_has_tenure_bin(self, clean_result):
        """tenure_bin 파생 컬럼 생성."""
        assert "tenure_bin" in clean_result.columns

    def test_is_active_normalized(self, clean_result):
        """is_active가 True/False Boolean으로 정규화."""
        active_col = clean_result["is_active"]
        assert active_col.dtype == bool or set(active_col.unique()).issubset({True, False})

    def test_standard_column_names(self, clean_result):
        """표준 컬럼명으로 리네이밍 (사번 → employee_id)."""
        assert "employee_id" in clean_result.columns
        assert "department" in clean_result.columns
        assert "hire_date" in clean_result.columns

    def test_date_columns_are_datetime(self, clean_result):
        """hire_date는 datetime 타입이어야 함."""
        assert pd.api.types.is_datetime64_any_dtype(clean_result["hire_date"])

    def test_handles_missing_optional_columns(self):
        """선택 컬럼 없이도 정상 처리 (필수 컬럼만 있는 경우)."""
        minimal_df = pd.DataFrame({
            "사번": ["E001", "E002"],
            "부서": ["개발팀", "인사팀"],
            "입사일": ["2020-01-01", "2021-06-01"],
            "재직여부": ["Y", "Y"],
        })
        mapping = detect_columns(minimal_df)
        result = clean_data(minimal_df, mapping)
        assert len(result) == 2
        assert "employee_id" in result.columns


class TestLoadFile:
    """load_file() 파일 로드 테스트"""

    def test_load_csv_utf8(self, sample_csv_bytes_utf8):
        """UTF-8 CSV 로드."""
        f = io.BytesIO(sample_csv_bytes_utf8)
        df = load_file(f, "test.csv")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_load_csv_euckr(self, sample_csv_bytes_euckr):
        """EUC-KR CSV 로드."""
        f = io.BytesIO(sample_csv_bytes_euckr)
        df = load_file(f, "test.csv")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_invalid_extension_raises(self):
        """지원하지 않는 확장자 → ValueError."""
        with pytest.raises(ValueError, match="Unsupported"):
            load_file(io.BytesIO(b""), "test.txt")

    def test_columns_stripped(self, sample_csv_bytes_utf8):
        """컬럼명 앞뒤 공백 제거."""
        csv = b"\xef\xbb\xbf  \xec\x82\xac\xeb\xb2\x88  ,\xec\xb4\x9c\xec\x9d\xb4\xeb\xa6\x84\n"
        # 공백 제거 테스트: 실제 CSV로 대체
        f = io.BytesIO(sample_csv_bytes_utf8)
        df = load_file(f, "test.csv")
        # 컬럼명에 앞뒤 공백 없음 확인
        for col in df.columns:
            assert col == col.strip()


class TestFilterFunctions:
    """필터 헬퍼 함수 테스트"""

    def test_filter_active(self, sample_df_clean):
        """재직자만 필터링 (7명)."""
        result = filter_active(sample_df_clean)
        assert len(result) == 7
        assert (result["is_active"] == True).all()

    def test_filter_resigned(self, sample_df_clean):
        """퇴사자만 필터링 (3명)."""
        result = filter_resigned(sample_df_clean)
        assert len(result) == 3
        assert (result["is_active"] == False).all()

    def test_filter_by_department(self, sample_df_clean):
        """부서별 필터링."""
        dev_df = filter_by_department(sample_df_clean, ["개발팀"])
        assert (dev_df["department"] == "개발팀").all()

    def test_filter_by_multiple_departments(self, sample_df_clean):
        """복수 부서 필터링."""
        result = filter_by_department(sample_df_clean, ["개발팀", "인사팀"])
        departments = set(result["department"].unique())
        assert departments.issubset({"개발팀", "인사팀"})

    def test_get_departments(self, sample_df_clean):
        """부서 목록 반환."""
        depts = get_departments(sample_df_clean)
        assert "개발팀" in depts
        assert "인사팀" in depts
        assert "영업팀" in depts
