# Design Ref: §3.1 — 컬럼 매핑 설정, 표준 컬럼명 상수, 앱 설정
"""
config.py — HR Excel Stats 앱 설정 및 상수

표준 HR 컬럼 매핑, 앱 전역 설정, 언어 코드를 정의합니다.
"""

# ── 표준 HR 컬럼 매핑 ──────────────────────────────────────────────────────
# 표준 컬럼명 → 파일에서 인식할 수 있는 다양한 컬럼명 목록
# Plan SC: 컬럼 매핑 오류 없이 표준 포맷 자동 인식
COLUMN_MAP: dict[str, list[str]] = {
    "employee_id":      ["사번", "직원번호", "사원번호", "emp_id", "employee_id", "id"],
    "name":             ["이름", "성명", "직원명", "사원명", "name", "full_name", "fullname"],
    "last_name":        ["성", "성씨", "last_name", "lastname", "surname", "nom", "family_name"],
    "first_name":       ["이름(이름)", "first_name", "firstname", "prénom", "prenom", "given_name", "forename"],
    "department":       ["부서", "팀", "부서명", "팀명", "department", "dept", "team"],
    "position":         ["직급", "직위", "직책", "position", "grade", "rank", "level"],
    "gender":           ["성별", "gender", "sex"],
    "birth_date":       ["생년월일", "생일", "birth_date", "birthdate", "dob", "date_of_birth"],
    "hire_date":        ["입사일", "입사일자", "입사날짜", "hire_date", "join_date", "start_date"],
    "employment_type":  ["고용형태", "고용유형", "계약형태", "employment_type", "emp_type", "contract_type"],
    "is_active":        ["재직여부", "재직", "재직상태", "is_active", "status", "active"],
    "resign_date":      ["퇴사일", "퇴사일자", "퇴직일", "resign_date", "end_date", "termination_date"],
    "resign_reason":    ["퇴사사유", "퇴직사유", "퇴사이유", "resign_reason", "termination_reason"],
    "application_date": ["지원일", "서류접수일", "지원날짜", "지원일자", "접수일",
                         "application_date", "apply_date", "applied_date", "candidate_date"],
    "offer_date":       ["오퍼일", "제안일", "offer일", "합격통보일", "채용통보일",
                         "offer_date", "offer_sent_date", "acceptance_date"],
}

# 필수 컬럼 (없으면 에러 처리)
REQUIRED_COLUMNS: list[str] = [
    "employee_id",
    "department",
    "hire_date",
    "is_active",
]

# 선택 컬럼 (없으면 해당 통계 스킵)
OPTIONAL_COLUMNS: list[str] = [
    "name",
    "position",
    "gender",
    "birth_date",
    "employment_type",
    "resign_date",
    "resign_reason",
    "application_date",
    "offer_date",
]

# ── 언어 설정 ─────────────────────────────────────────────────────────────
SUPPORTED_LANGUAGES: list[str] = ["한국어", "English", "Français"]
LANGUAGE_CODES: dict[str, str] = {
    "한국어": "ko",
    "English": "en",
    "Français": "fr",
}
DEFAULT_LANGUAGE: str = "ko"

# ── 앱 전역 설정 ──────────────────────────────────────────────────────────
APP_CONFIG: dict = {
    "max_file_size_mb": 50,
    "preview_rows": 5,
    "chart_theme": "plotly_white",
    "chart_height": 400,
    "chart_font_family": "Malgun Gothic, NanumGothic, Apple SD Gothic Neo, sans-serif",
    "chart_colors": ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B",
                     "#44BBA4", "#E94F37", "#393E41", "#F5A65B", "#7B2D8B"],
}

# ── 근속연수 구간 ──────────────────────────────────────────────────────────
TENURE_BINS: list[float] = [0, 1, 3, 5, 10, float("inf")]
TENURE_LABELS: dict[str, list[str]] = {
    "ko": ["1년 미만", "1~3년", "3~5년", "5~10년", "10년 이상"],
    "en": ["< 1 yr", "1~3 yrs", "3~5 yrs", "5~10 yrs", "10+ yrs"],
    "fr": ["< 1 an", "1~3 ans", "3~5 ans", "5~10 ans", "10+ ans"],
}

# ── 연령대 구간 ───────────────────────────────────────────────────────────
AGE_BINS: list[int] = [0, 30, 40, 50, 60, 200]
AGE_LABELS: dict[str, list[str]] = {
    "ko": ["20대", "30대", "40대", "50대", "60대+"],
    "en": ["20s", "30s", "40s", "50s", "60s+"],
    "fr": ["20 ans", "30 ans", "40 ans", "50 ans", "60 ans+"],
}

# ── 재직여부 값 정규화 ─────────────────────────────────────────────────────
ACTIVE_VALUES: list = [
    True, 1,
    "Y", "y", "YES", "yes",
    "재직", "O", "o",
    "TRUE", "true",
    # English
    "Active", "active", "ACTIVE",
    # French
    "Actif", "actif", "ACTIF",
]
INACTIVE_VALUES: list = [
    False, 0,
    "N", "n", "NO", "no",
    "퇴사", "X", "x",
    "FALSE", "false",
    # English
    "Inactive", "inactive", "INACTIVE",
    # French
    "Inactif", "inactif", "INACTIF",
]
