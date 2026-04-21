# [Design] HR Excel 통계 앱

**Feature**: hr-excel-stats  
**Phase**: Design  
**Created**: 2026-04-14  
**Status**: Draft  
**Architecture**: Option C + i18n (Pragmatic + Multilingual)

---

## Context Anchor

| 항목 | 내용 |
|------|------|
| **WHY** | HR 담당자의 반복적 수작업 집계를 없애고 일관된 통계 리포트를 즉시 제공 |
| **WHO** | HR 담당자 / 인사팀 (엑셀 파일 보유, 파이썬 비전문가) |
| **RISK** | 엑셀 컬럼 구조 불일치 시 파싱 오류 / 다국어 번역 누락 |
| **SUCCESS** | 업로드 후 30초 내 대시보드 표시 + 한국어·영어·프랑스어 보고서 내보내기 |
| **SCOPE** | 로컬 Python Streamlit 앱, 표준 HR 엑셀 포맷, 외부 서버 없음 |

---

## 1. Overview

HR 담당자가 표준 엑셀 파일을 업로드하면 인원 현황·입퇴사/이직·추가 통계를 자동 산출하고, 한국어·영어·프랑스어 3개 언어로 보고서를 내보낼 수 있는 로컬 Streamlit 앱.

### 선택 아키텍처: Option C + i18n

7개 파일로 명확한 책임 분리. i18n 모듈을 통해 3개 언어를 독립적으로 관리.

---

## 2. 프로젝트 구조

```
hr_excel_stats/
├── app.py              ← Streamlit 진입점 + 페이지 라우팅 + 언어 선택
├── parser.py           ← 엑셀/CSV 파싱, 컬럼 자동 매핑, 데이터 정제
├── analytics.py        ← 모든 통계 계산 함수 (인원/입퇴사/채용/교육/조직)
├── charts.py           ← Plotly 차트 생성 함수
├── exporter.py         ← 엑셀(.xlsx) / CSV / 이미지(PNG) 내보내기
├── config.py           ← 컬럼 매핑 설정, 표준 컬럼명 상수, 앱 설정
├── i18n.py             ← 한국어 / 영어 / 프랑스어 번역 딕셔너리
├── requirements.txt
├── run.bat             ← Windows 실행 스크립트
└── run.sh              ← Mac/Linux 실행 스크립트
```

---

## 3. 모듈 상세 설계

### 3.1 `config.py` — 설정 및 상수

```python
# 표준 HR 컬럼명 매핑 (한국어 기본)
COLUMN_MAP = {
    "employee_id": ["사번", "직원번호", "EMP_ID", "employee_id"],
    "name": ["이름", "성명", "name"],
    "department": ["부서", "팀", "부서명", "department"],
    "position": ["직급", "직위", "position", "grade"],
    "gender": ["성별", "gender", "sex"],
    "birth_date": ["생년월일", "birth_date", "birthdate"],
    "hire_date": ["입사일", "입사일자", "hire_date"],
    "employment_type": ["고용형태", "고용유형", "employment_type"],
    "is_active": ["재직여부", "재직", "is_active", "status"],
    "resign_date": ["퇴사일", "퇴사일자", "resign_date"],
    "resign_reason": ["퇴사사유", "퇴직사유", "resign_reason"],
}

SUPPORTED_LANGUAGES = ["한국어", "English", "Français"]
LANGUAGE_CODES = {"한국어": "ko", "English": "en", "Français": "fr"}

APP_CONFIG = {
    "max_file_size_mb": 50,
    "preview_rows": 5,
    "chart_theme": "plotly_white",
}
```

### 3.2 `i18n.py` — 다국어 지원

```python
TRANSLATIONS = {
    "ko": {
        # 앱 제목/메뉴
        "app_title": "HR 통계 대시보드",
        "upload_title": "엑셀 파일 업로드",
        "upload_hint": "xlsx, xls, csv 파일을 업로드하세요 (최대 50MB)",
        "analyze_btn": "분석 시작",
        "download_excel": "엑셀 다운로드",
        "download_csv": "CSV 다운로드",
        # 탭
        "tab_dashboard": "전체 대시보드",
        "tab_headcount": "인원 현황",
        "tab_attrition": "입퇴사/이직",
        "tab_additional": "추가 통계",
        # 통계 레이블
        "total_employees": "전체 재직 인원",
        "new_hires": "입사자 수",
        "resignations": "퇴사자 수",
        "turnover_rate": "이직률",
        "avg_tenure": "평균 근속연수",
        # 차트 제목
        "chart_dept_dist": "부서별 인원 분포",
        "chart_position_dist": "직급별 인원 분포",
        "chart_gender_ratio": "성별 비율",
        "chart_age_dist": "연령대별 분포",
        "chart_tenure_dist": "근속연수 분포",
        "chart_monthly_hire": "월별 입사/퇴사 추이",
        "chart_turnover_by_dept": "부서별 이직률",
        # 필터
        "filter_date_range": "기간 선택",
        "filter_department": "부서 선택",
        "filter_all": "전체",
        # 오류
        "error_no_file": "파일을 업로드해 주세요.",
        "error_column_missing": "필수 컬럼을 찾을 수 없습니다: {cols}",
        "error_encoding": "파일 인코딩 오류. UTF-8 또는 EUC-KR 파일을 사용해 주세요.",
    },
    "en": {
        "app_title": "HR Statistics Dashboard",
        "upload_title": "Upload Excel File",
        "upload_hint": "Upload xlsx, xls, or csv file (max 50MB)",
        "analyze_btn": "Start Analysis",
        "download_excel": "Download Excel",
        "download_csv": "Download CSV",
        "tab_dashboard": "Dashboard",
        "tab_headcount": "Headcount",
        "tab_attrition": "Attrition",
        "tab_additional": "Additional Stats",
        "total_employees": "Total Employees",
        "new_hires": "New Hires",
        "resignations": "Resignations",
        "turnover_rate": "Turnover Rate",
        "avg_tenure": "Avg. Tenure (years)",
        "chart_dept_dist": "Headcount by Department",
        "chart_position_dist": "Headcount by Position",
        "chart_gender_ratio": "Gender Ratio",
        "chart_age_dist": "Age Distribution",
        "chart_tenure_dist": "Tenure Distribution",
        "chart_monthly_hire": "Monthly Hire/Resign Trend",
        "chart_turnover_by_dept": "Turnover Rate by Department",
        "filter_date_range": "Date Range",
        "filter_department": "Department",
        "filter_all": "All",
        "error_no_file": "Please upload a file.",
        "error_column_missing": "Required columns not found: {cols}",
        "error_encoding": "File encoding error. Please use UTF-8 or EUC-KR.",
    },
    "fr": {
        "app_title": "Tableau de bord RH",
        "upload_title": "Télécharger le fichier Excel",
        "upload_hint": "Télécharger un fichier xlsx, xls ou csv (max 50 Mo)",
        "analyze_btn": "Lancer l'analyse",
        "download_excel": "Télécharger Excel",
        "download_csv": "Télécharger CSV",
        "tab_dashboard": "Tableau de bord",
        "tab_headcount": "Effectifs",
        "tab_attrition": "Entrées/Sorties",
        "tab_additional": "Statistiques supplémentaires",
        "total_employees": "Total des employés",
        "new_hires": "Nouvelles embauches",
        "resignations": "Démissions",
        "turnover_rate": "Taux de rotation",
        "avg_tenure": "Ancienneté moyenne (ans)",
        "chart_dept_dist": "Effectifs par département",
        "chart_position_dist": "Effectifs par poste",
        "chart_gender_ratio": "Répartition par genre",
        "chart_age_dist": "Répartition par âge",
        "chart_tenure_dist": "Répartition par ancienneté",
        "chart_monthly_hire": "Tendance mensuelle embauches/départs",
        "chart_turnover_by_dept": "Taux de rotation par département",
        "filter_date_range": "Période",
        "filter_department": "Département",
        "filter_all": "Tous",
        "error_no_file": "Veuillez télécharger un fichier.",
        "error_column_missing": "Colonnes requises introuvables : {cols}",
        "error_encoding": "Erreur d'encodage. Utilisez UTF-8 ou EUC-KR.",
    },
}

def t(key: str, lang: str = "ko", **kwargs) -> str:
    """번역 함수. 키로 번역 문자열을 반환."""
    text = TRANSLATIONS.get(lang, TRANSLATIONS["ko"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
```

### 3.3 `parser.py` — 엑셀 파싱

```python
class HRDataParser:
    def __init__(self, column_map: dict = None):
        self.column_map = column_map or COLUMN_MAP

    def load(self, file) -> pd.DataFrame:
        """파일 객체를 DataFrame으로 로드. xlsx/xls/csv 자동 감지."""

    def detect_columns(self, df: pd.DataFrame) -> dict:
        """실제 컬럼명 → 표준 컬럼명 매핑 자동 감지."""

    def validate(self, df: pd.DataFrame, mapping: dict) -> tuple[bool, list]:
        """필수 컬럼 존재 여부 검증. (is_valid, missing_cols)"""

    def clean(self, df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
        """날짜 파싱, 결측치 처리, 연령/근속 파생 컬럼 생성."""
        # hire_date → tenure_years
        # birth_date → age, age_group (20대/30대/40대/50대+)
        # resign_date 없으면 is_active = True
```

**파생 컬럼:**
| 컬럼 | 계산 |
|------|------|
| `tenure_years` | (오늘 - hire_date).days / 365 |
| `age` | (오늘 - birth_date).days / 365 |
| `age_group` | 10년 단위 구간 |
| `hire_year_month` | hire_date → YYYY-MM |
| `resign_year_month` | resign_date → YYYY-MM |

### 3.4 `analytics.py` — 통계 계산

```python
# ── 인원 현황 ──────────────────────────────────────
def headcount_total(df) -> int
def headcount_by_dept(df) -> pd.Series
def headcount_by_position(df) -> pd.Series
def headcount_by_gender(df) -> pd.Series
def headcount_by_age_group(df) -> pd.Series
def headcount_by_employment_type(df) -> pd.Series
def tenure_distribution(df) -> pd.Series   # 구간: 1년미만/1-3년/3-5년/5-10년/10년+

# ── 입퇴사/이직 ────────────────────────────────────
def monthly_hires(df, start, end) -> pd.DataFrame   # YYYY-MM, hire_count
def monthly_resignations(df, start, end) -> pd.DataFrame
def turnover_rate(df, period="year") -> float        # (퇴사자/평균재직자) × 100
def turnover_by_dept(df) -> pd.Series
def avg_tenure_by_dept(df) -> pd.Series
def resign_reason_breakdown(df) -> pd.Series         # 데이터 있을 경우

# ── 추가 통계 (데이터 있을 경우) ──────────────────────
def recruitment_stats(df) -> dict                    # 채용 채널별, 소요일
def education_stats(df) -> dict                      # 교육 이수율
def org_structure_stats(df) -> dict                  # 스팬 오브 컨트롤
```

### 3.5 `charts.py` — 차트 생성

모든 함수는 `plotly.graph_objects.Figure`를 반환.

```python
def bar_chart(data, x, y, title, color=None, lang="ko") -> go.Figure
def horizontal_bar(data, title, lang="ko") -> go.Figure
def pie_chart(data, names, title, lang="ko") -> go.Figure
def line_chart(data, x, y, title, lang="ko") -> go.Figure
def histogram(data, x, title, bins=10, lang="ko") -> go.Figure
def kpi_metric(label, value, delta=None) -> None   # st.metric 래퍼
```

**공통 스타일:**
- 테마: `plotly_white`
- 폰트: 한국어 `NanumGothic` fallback 포함
- 색상 팔레트: `["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#3B1F2B"]`

### 3.6 `exporter.py` — 내보내기

```python
class HRExporter:
    def to_excel(self, stats_dict: dict, lang: str = "ko") -> bytes:
        """통계 결과를 다국어 레이블로 Excel 파일 생성. BytesIO 반환."""
        # 시트 구성:
        # Sheet1: 인원 현황 요약
        # Sheet2: 입퇴사/이직 요약
        # Sheet3: 추가 통계
        # Sheet4: 원본 데이터 (선택)

    def to_csv(self, df: pd.DataFrame, encoding: str = "utf-8-sig") -> bytes:
        """CSV 내보내기. utf-8-sig로 한국어 엑셀 호환."""

    def chart_to_png(self, fig: go.Figure) -> bytes:
        """Plotly 차트를 PNG 이미지로 변환. kaleido 패키지 필요."""
```

### 3.7 `app.py` — Streamlit 메인

```python
# 페이지 구성
st.set_page_config(
    page_title="HR Statistics",
    page_icon="📊",
    layout="wide"
)

# 언어 선택 (사이드바)
lang_name = st.sidebar.selectbox("🌐 언어 / Language", SUPPORTED_LANGUAGES)
lang = LANGUAGE_CODES[lang_name]

# 세션 상태
# st.session_state.df_raw       ← 원본 DataFrame
# st.session_state.df_clean     ← 정제된 DataFrame
# st.session_state.col_mapping  ← 컬럼 매핑

# 화면 흐름
# 1. UPLOAD_PAGE: 파일 업로드 + 컬럼 매핑 확인
# 2. DASHBOARD: 탭 대시보드 (인원/입퇴사/추가/전체)
```

---

## 4. 데이터 흐름

```
[파일 업로드]
     ↓
parser.load(file)
     ↓
parser.detect_columns(df) → 자동 매핑 테이블
     ↓ (사용자 확인/수정)
parser.validate(df, mapping) → 오류 시 에러 메시지
     ↓
parser.clean(df, mapping) → df_clean (파생 컬럼 포함)
     ↓
analytics.*(df_clean) → 통계 결과 dict
     ↓
charts.*(stats) → Plotly Figure 리스트
     ↓
st.plotly_chart(fig) → 화면 표시
     ↓
exporter.to_excel(stats, lang) → 다운로드 버튼
```

---

## 5. 화면 설계

### 5.1 업로드 화면
```
┌─────────────────────────────────────────────────────────┐
│  🌐 언어 선택: [한국어 ▼]                    (사이드바)    │
├─────────────────────────────────────────────────────────┤
│  📊 HR 통계 대시보드                                      │
│                                                         │
│  ┌─────────────────────────────────────────┐            │
│  │  엑셀 파일을 여기에 드래그 하거나 클릭하여  │            │
│  │  업로드하세요 (.xlsx .xls .csv, 최대 50MB) │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  📋 컬럼 자동 감지 결과:                                  │
│  ┌──────────────┬──────────────────┬──────────┐         │
│  │ 표준 컬럼     │ 파일 내 컬럼      │ 상태      │         │
│  ├──────────────┼──────────────────┼──────────┤         │
│  │ 사번          │ EMP_ID           │ ✅ 자동   │         │
│  │ 부서          │ 팀명              │ ✅ 자동   │         │
│  │ 퇴사사유      │ (없음)            │ ⚠️ 선택   │         │
│  └──────────────┴──────────────────┴──────────┘         │
│                                                         │
│  [  분석 시작  ]                                          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 대시보드 화면
```
┌─────────────────────────────────────────────────────────┐
│  🔍 필터: [기간: 2024-01 ~ 2024-12] [부서: 전체 ▼]       │
├─────────────────────────────────────────────────────────┤
│  [ 전체 대시보드 | 인원 현황 | 입퇴사/이직 | 추가 통계 ]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [ 전체 인원: 245 ]  [ 입사자: 32 ]  [ 퇴사자: 18 ]       │
│  [ 이직률: 7.3% ]   [ 평균 근속: 4.2년 ]                  │
│                                                         │
│  ┌──────────────────────┐  ┌───────────────────────┐    │
│  │  부서별 인원 분포      │  │  월별 입퇴사 추이        │    │
│  │  [막대그래프]          │  │  [라인차트]             │    │
│  └──────────────────────┘  └───────────────────────┘    │
│  ┌──────────────────────┐  ┌───────────────────────┐    │
│  │  성별 비율            │  │  연령대별 분포           │    │
│  │  [원형차트]            │  │  [히스토그램]           │    │
│  └──────────────────────┘  └───────────────────────┘    │
│                                                         │
│  [📥 엑셀 다운로드]  [📥 CSV 다운로드]  [🖼️ 차트 저장]    │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 엑셀 내보내기 다국어 시트 구조

언어 선택에 따라 시트 헤더와 레이블이 변경됨.

| 시트 | 한국어 | English | Français |
|------|-------|---------|----------|
| Sheet1 | 인원 현황 요약 | Headcount Summary | Résumé des effectifs |
| Sheet2 | 입퇴사 현황 | Attrition Summary | Résumé des départs |
| Sheet3 | 추가 통계 | Additional Stats | Statistiques supplémentaires |

---

## 7. 의존성

```txt
# requirements.txt
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.0
xlrd>=2.0.1          # .xls 지원
plotly>=5.18.0
xlsxwriter>=3.1.0
kaleido>=0.2.1        # 차트 PNG 저장
```

---

## 8. 테스트 계획

| 테스트 | 내용 |
|--------|------|
| 파싱 테스트 | 표준 포맷 엑셀 → 컬럼 자동 매핑 성공 |
| 결측 컬럼 테스트 | 필수 컬럼 없을 때 오류 메시지 정상 출력 |
| 인코딩 테스트 | EUC-KR, UTF-8, UTF-8-BOM 파일 정상 처리 |
| 통계 정확도 | 샘플 데이터로 이직률·평균근속 수동 검증 |
| 다국어 전환 | 언어 변경 시 모든 레이블·차트 제목 변경 확인 |
| 엑셀 내보내기 | 3개 언어로 내보낸 파일 내용 검증 |
| 대용량 테스트 | 10,000행 파일 30초 내 처리 |

---

## 9. 실행 방법

### Windows (`run.bat`)
```bat
@echo off
pip install -r requirements.txt
streamlit run app.py
```

### Mac/Linux (`run.sh`)
```bash
#!/bin/bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 10. 설계 결정 사항

| 결정 | 이유 |
|------|------|
| Streamlit 선택 | 데이터 앱에 최적화, 설치 간단, HR 비개발자 친화적 |
| Plotly 선택 | 인터랙티브 차트, Streamlit 네이티브 지원 |
| i18n 딕셔너리 방식 | 외부 라이브러리 불필요, 3개 언어 범위에서 충분 |
| utf-8-sig CSV | 한국어 엑셀에서 열 때 깨짐 방지 |
| kaleido PNG 저장 | Plotly 공식 이미지 저장 방식, 추가 설치 최소화 |
| 세션 상태 활용 | 페이지 재렌더링 시 데이터 유지, 빠른 필터 적용 |

---

## 11. 구현 가이드

### 11.1 구현 순서

1. `config.py` — 컬럼 매핑, 설정 상수
2. `i18n.py` — 3개 언어 번역 딕셔너리
3. `parser.py` — 파일 로드, 컬럼 감지, 데이터 정제
4. `analytics.py` — 통계 계산 함수 전체
5. `charts.py` — Plotly 차트 생성 함수
6. `exporter.py` — 엑셀/CSV/PNG 내보내기
7. `app.py` — Streamlit UI 연결 및 전체 조립
8. `requirements.txt`, `run.bat`, `run.sh`

### 11.2 핵심 구현 포인트

- **컬럼 감지**: 대소문자·공백·특수문자 무시한 fuzzy 매칭 (`str.lower().strip()`)
- **날짜 파싱**: `pd.to_datetime(errors='coerce')` + 다양한 형식 자동 처리
- **한국어 폰트**: `plotly` 차트에 `font_family="Malgun Gothic, NanumGothic, sans-serif"`
- **메모리 효율**: 10만행 이상 시 `chunksize` 로드 고려
- **다운로드 버튼**: `st.download_button`에 `BytesIO` 직접 전달

### 11.3 Session Guide

#### 모듈 맵

| 모듈 | 파일 | 예상 작업량 |
|------|------|-----------|
| M1 | config.py + i18n.py | ~50 lines, 30분 |
| M2 | parser.py | ~120 lines, 1시간 |
| M3 | analytics.py | ~150 lines, 1시간 |
| M4 | charts.py | ~100 lines, 45분 |
| M5 | exporter.py | ~80 lines, 45분 |
| M6 | app.py + run scripts | ~150 lines, 1시간 |

#### 추천 세션 플랜

| 세션 | 범위 | 명령어 |
|------|------|-------|
| Session 1 | 기반 모듈 (설정+파서) | `/pdca do hr-excel-stats --scope M1,M2` |
| Session 2 | 분석+차트 | `/pdca do hr-excel-stats --scope M3,M4` |
| Session 3 | 내보내기+앱 조립 | `/pdca do hr-excel-stats --scope M5,M6` |
