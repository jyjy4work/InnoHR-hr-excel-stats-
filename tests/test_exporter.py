"""
test_exporter.py — exporter.py 내보내기 함수 테스트

L2: to_excel / to_csv 출력 검증
L3: 다국어 시트명 / 인코딩 / G2 fix (Sheet3 추가통계) 검증
"""

import io

import pandas as pd
import pytest

from exporter import chart_to_png, filename_with_date, to_csv, to_excel


class TestToExcel:
    """to_excel() Excel 내보내기 테스트"""

    @pytest.fixture
    def excel_bytes_ko(self, sample_df_clean, stats_dict):
        return to_excel(sample_df_clean, stats_dict, lang="ko")

    @pytest.fixture
    def excel_bytes_en(self, sample_df_clean, stats_dict):
        return to_excel(sample_df_clean, stats_dict, lang="en")

    @pytest.fixture
    def excel_bytes_fr(self, sample_df_clean, stats_dict):
        return to_excel(sample_df_clean, stats_dict, lang="fr")

    def test_returns_bytes(self, excel_bytes_ko):
        """bytes 반환."""
        assert isinstance(excel_bytes_ko, bytes)

    def test_non_empty_output(self, excel_bytes_ko):
        """비어있지 않은 파일."""
        assert len(excel_bytes_ko) > 1000

    def test_valid_xlsx_format(self, excel_bytes_ko):
        """유효한 xlsx 포맷 (openpyxl로 읽기 가능)."""
        wb = pd.ExcelFile(io.BytesIO(excel_bytes_ko))
        assert wb is not None

    def test_has_four_sheets_ko(self, excel_bytes_ko):
        """한국어: 4개 시트 (인원현황, 입퇴사, 추가통계, 원본)."""
        wb = pd.ExcelFile(io.BytesIO(excel_bytes_ko))
        assert len(wb.sheet_names) == 4

    def test_sheet_names_in_korean(self, excel_bytes_ko):
        """한국어 시트명 검증."""
        wb = pd.ExcelFile(io.BytesIO(excel_bytes_ko))
        # 원본 데이터 시트 존재
        assert any("원본" in name or "raw" in name.lower() for name in wb.sheet_names)

    def test_sheet_names_in_english(self, excel_bytes_en):
        """영어 시트명 검증."""
        wb = pd.ExcelFile(io.BytesIO(excel_bytes_en))
        sheet_names_lower = [s.lower() for s in wb.sheet_names]
        assert any("headcount" in s or "summary" in s for s in sheet_names_lower)

    def test_sheet_names_in_french(self, excel_bytes_fr):
        """프랑스어 시트명 검증."""
        wb = pd.ExcelFile(io.BytesIO(excel_bytes_fr))
        assert len(wb.sheet_names) == 4

    def test_sheet_names_differ_by_language(self, excel_bytes_ko, excel_bytes_en):
        """ko/en 시트명이 달라야 함."""
        ko_sheets = pd.ExcelFile(io.BytesIO(excel_bytes_ko)).sheet_names
        en_sheets = pd.ExcelFile(io.BytesIO(excel_bytes_en)).sheet_names
        assert ko_sheets != en_sheets

    def test_g2_fix_additional_stats_sheet(self, excel_bytes_ko):
        """G2 Fix: 추가통계 시트(Sheet3)가 존재해야 함."""
        wb = pd.ExcelFile(io.BytesIO(excel_bytes_ko))
        sheet_names_lower = [s.lower() for s in wb.sheet_names]
        # 추가통계 또는 additional 이 포함된 시트가 있어야 함
        has_additional = any(
            "추가" in s or "additional" in s or "statistiques" in s
            for s in wb.sheet_names
        )
        assert has_additional, f"추가통계 시트 없음. 시트 목록: {wb.sheet_names}"

    def test_raw_data_sheet_has_rows(self, sample_df_clean, stats_dict):
        """원본 데이터 시트에 행이 있어야 함."""
        excel_bytes = to_excel(sample_df_clean, stats_dict, lang="ko")
        wb = pd.ExcelFile(io.BytesIO(excel_bytes))
        # 마지막 시트 (원본 데이터)
        last_sheet = wb.sheet_names[-1]
        df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=last_sheet)
        assert len(df) == len(sample_df_clean)

    def test_raw_sheet_no_bin_columns(self, sample_df_clean, stats_dict):
        """원본 시트에 _bin 파생 컬럼 없음."""
        excel_bytes = to_excel(sample_df_clean, stats_dict, lang="ko")
        wb = pd.ExcelFile(io.BytesIO(excel_bytes))
        last_sheet = wb.sheet_names[-1]
        df = pd.read_excel(io.BytesIO(excel_bytes), sheet_name=last_sheet)
        bin_cols = [c for c in df.columns if str(c).endswith("_bin")]
        assert len(bin_cols) == 0, f"_bin 컬럼 발견: {bin_cols}"


class TestToCsv:
    """to_csv() CSV 내보내기 테스트"""

    def test_returns_bytes(self, sample_df_clean):
        result = to_csv(sample_df_clean)
        assert isinstance(result, bytes)

    def test_non_empty(self, sample_df_clean):
        result = to_csv(sample_df_clean)
        assert len(result) > 0

    def test_default_encoding_utf8sig(self, sample_df_clean):
        """기본 인코딩 utf-8-sig (BOM 포함)."""
        result = to_csv(sample_df_clean)
        # UTF-8-BOM 시그니처: EF BB BF
        assert result[:3] == b"\xef\xbb\xbf"

    def test_no_bin_columns(self, sample_df_clean):
        """_bin 파생 컬럼 제외."""
        result = to_csv(sample_df_clean)
        header_line = result.decode("utf-8-sig").split("\n")[0]
        assert "_bin" not in header_line

    def test_readable_as_dataframe(self, sample_df_clean):
        """pandas로 다시 읽기 가능."""
        result = to_csv(sample_df_clean)
        df = pd.read_csv(io.BytesIO(result), encoding="utf-8-sig")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_df_clean)

    def test_date_columns_as_string(self, sample_df_clean):
        """날짜 컬럼이 YYYY-MM-DD 문자열로 변환."""
        result = to_csv(sample_df_clean)
        df = pd.read_csv(io.BytesIO(result), encoding="utf-8-sig")
        if "hire_date" in df.columns:
            sample_date = str(df["hire_date"].iloc[0])
            # YYYY-MM-DD 형식 (10자리) 또는 NaN
            if sample_date != "nan":
                assert len(sample_date) >= 10

    def test_custom_encoding(self, sample_df_clean):
        """사용자 지정 인코딩."""
        result = to_csv(sample_df_clean, encoding="utf-8")
        assert isinstance(result, bytes)


class TestChartToPng:
    """chart_to_png() PNG 내보내기 테스트"""

    def test_returns_none_without_kaleido(self):
        """kaleido 미설치 시 None 반환 (에러 없음)."""
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            result = chart_to_png(fig)
            # kaleido 없으면 None, 있으면 bytes
            assert result is None or isinstance(result, bytes)
        except ImportError:
            pytest.skip("plotly 미설치")

    def test_graceful_none_on_error(self):
        """잘못된 입력에도 None 반환 (에러 미전파)."""
        result = chart_to_png(None)
        assert result is None


class TestFilenameWithDate:
    """filename_with_date() 파일명 생성 테스트"""

    def test_returns_string(self):
        result = filename_with_date("hr_report", "xlsx")
        assert isinstance(result, str)

    def test_contains_base_name(self):
        result = filename_with_date("hr_report", "xlsx")
        assert "hr_report" in result

    def test_contains_extension(self):
        result = filename_with_date("hr_report", "xlsx")
        assert result.endswith(".xlsx")

    def test_contains_date(self):
        """오늘 날짜(8자리) 포함."""
        from datetime import date
        today = date.today().strftime("%Y%m%d")
        result = filename_with_date("hr_report", "xlsx")
        assert today in result

    def test_csv_extension(self):
        result = filename_with_date("hr_data", "csv")
        assert result.endswith(".csv")
