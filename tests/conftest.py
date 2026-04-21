"""
conftest.py — pytest 공용 픽스처

hr_excel_stats 디렉토리를 sys.path에 추가하여
모듈을 직접 import 가능하도록 설정합니다.
"""

import sys
import os
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import pytest

# hr_excel_stats 모듈 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hr_excel_stats"))


# ══════════════════════════════════════════════════════════════════════════════
# 샘플 DataFrame 픽스처
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_df_clean():
    """
    parser.clean_data() 결과와 동일한 구조의 샘플 DataFrame.
    10명의 직원 데이터: 7명 재직 / 3명 퇴사.
    """
    today = date.today()

    records = [
        # 재직자 7명
        {"employee_id": "E001", "name": "홍길동", "department": "개발팀", "position": "과장",
         "gender": "남", "hire_date": pd.Timestamp("2020-03-01"), "is_active": True,
         "employment_type": "정규직", "resign_date": pd.NaT, "resign_reason": None,
         "tenure_years": 5.1, "age": 35, "age_bin": 1, "tenure_bin": 3,
         "hire_year_month": "2020-03", "resign_year_month": None},
        {"employee_id": "E002", "name": "김영희", "department": "개발팀", "position": "대리",
         "gender": "여", "hire_date": pd.Timestamp("2022-07-01"), "is_active": True,
         "employment_type": "정규직", "resign_date": pd.NaT, "resign_reason": None,
         "tenure_years": 2.8, "age": 29, "age_bin": 0, "tenure_bin": 1,
         "hire_year_month": "2022-07", "resign_year_month": None},
        {"employee_id": "E003", "name": "이철수", "department": "인사팀", "position": "부장",
         "gender": "남", "hire_date": pd.Timestamp("2015-01-01"), "is_active": True,
         "employment_type": "정규직", "resign_date": pd.NaT, "resign_reason": None,
         "tenure_years": 11.3, "age": 45, "age_bin": 2, "tenure_bin": 4,
         "hire_year_month": "2015-01", "resign_year_month": None},
        {"employee_id": "E004", "name": "박미래", "department": "영업팀", "position": "사원",
         "gender": "여", "hire_date": pd.Timestamp("2024-01-15"), "is_active": True,
         "employment_type": "계약직", "resign_date": pd.NaT, "resign_reason": None,
         "tenure_years": 0.5, "age": 26, "age_bin": 0, "tenure_bin": 0,
         "hire_year_month": "2024-01", "resign_year_month": None},
        {"employee_id": "E005", "name": "최준혁", "department": "개발팀", "position": "차장",
         "gender": "남", "hire_date": pd.Timestamp("2018-05-01"), "is_active": True,
         "employment_type": "정규직", "resign_date": pd.NaT, "resign_reason": None,
         "tenure_years": 7.9, "age": 38, "age_bin": 1, "tenure_bin": 3,
         "hire_year_month": "2018-05", "resign_year_month": None},
        {"employee_id": "E006", "name": "정수연", "department": "인사팀", "position": "대리",
         "gender": "여", "hire_date": pd.Timestamp("2021-09-01"), "is_active": True,
         "employment_type": "정규직", "resign_date": pd.NaT, "resign_reason": None,
         "tenure_years": 3.6, "age": 31, "age_bin": 1, "tenure_bin": 2,
         "hire_year_month": "2021-09", "resign_year_month": None},
        {"employee_id": "E007", "name": "윤동현", "department": "영업팀", "position": "과장",
         "gender": "남", "hire_date": pd.Timestamp("2019-11-01"), "is_active": True,
         "employment_type": "정규직", "resign_date": pd.NaT, "resign_reason": None,
         "tenure_years": 6.4, "age": 41, "age_bin": 2, "tenure_bin": 3,
         "hire_year_month": "2019-11", "resign_year_month": None},
        # 퇴사자 3명
        {"employee_id": "E008", "name": "송지은", "department": "개발팀", "position": "사원",
         "gender": "여", "hire_date": pd.Timestamp("2023-02-01"), "is_active": False,
         "employment_type": "정규직", "resign_date": pd.Timestamp("2024-02-28"),
         "resign_reason": "자발적퇴사",
         "tenure_years": 1.1, "age": 27, "age_bin": 0, "tenure_bin": 1,
         "hire_year_month": "2023-02", "resign_year_month": "2024-02"},
        {"employee_id": "E009", "name": "한민준", "department": "영업팀", "position": "대리",
         "gender": "남", "hire_date": pd.Timestamp("2021-06-01"), "is_active": False,
         "employment_type": "계약직", "resign_date": pd.Timestamp("2024-06-30"),
         "resign_reason": "계약만료",
         "tenure_years": 3.1, "age": 33, "age_bin": 1, "tenure_bin": 2,
         "hire_year_month": "2021-06", "resign_year_month": "2024-06"},
        {"employee_id": "E010", "name": "오서연", "department": "인사팀", "position": "사원",
         "gender": "여", "hire_date": pd.Timestamp("2022-11-01"), "is_active": False,
         "employment_type": "정규직", "resign_date": pd.Timestamp("2024-11-30"),
         "resign_reason": "자발적퇴사",
         "tenure_years": 2.1, "age": 28, "age_bin": 0, "tenure_bin": 1,
         "hire_year_month": "2022-11", "resign_year_month": "2024-11"},
    ]

    return pd.DataFrame(records)


@pytest.fixture
def sample_raw_df():
    """
    파싱 전 원본 DataFrame (한국어 컬럼명).
    detect_columns / clean_data 테스트용.
    """
    return pd.DataFrame({
        "사번":    ["E001", "E002", "E003"],
        "이름":    ["홍길동", "김영희", "이철수"],
        "부서":    ["개발팀", "개발팀", "인사팀"],
        "직급":    ["과장", "대리", "부장"],
        "성별":    ["남", "여", "남"],
        "생년월일": ["1990-01-01", "1996-05-10", "1979-11-20"],
        "입사일":  ["2020-03-01", "2022-07-01", "2015-01-01"],
        "고용형태": ["정규직", "정규직", "정규직"],
        "재직여부": ["Y", "Y", "Y"],
        "퇴사일":  [None, None, None],
        "퇴사사유": [None, None, None],
    })


@pytest.fixture
def sample_csv_bytes_utf8():
    """UTF-8 인코딩 CSV 바이트."""
    csv_content = (
        "사번,이름,부서,직급,재직여부,입사일\n"
        "E001,홍길동,개발팀,과장,Y,2020-03-01\n"
        "E002,김영희,개발팀,대리,Y,2022-07-01\n"
    )
    return csv_content.encode("utf-8")


@pytest.fixture
def sample_csv_bytes_euckr():
    """EUC-KR 인코딩 CSV 바이트."""
    csv_content = (
        "사번,이름,부서,직급,재직여부,입사일\n"
        "E001,홍길동,개발팀,과장,Y,2020-03-01\n"
    )
    return csv_content.encode("euc-kr")


@pytest.fixture
def empty_df():
    """빈 DataFrame — 엣지케이스 테스트용."""
    return pd.DataFrame()


@pytest.fixture
def stats_dict(sample_df_clean):
    """analytics.summary_kpis() 호환 통계 dict."""
    return {
        "total_employees": 7,
        "new_hires": 4,
        "resignations": 3,
        "turnover_rate": 30.0,
        "avg_tenure": 5.4,
    }
