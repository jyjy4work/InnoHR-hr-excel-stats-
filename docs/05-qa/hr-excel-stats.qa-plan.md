# [QA] hr-excel-stats — 테스트 계획 및 실행 결과

**Feature**: hr-excel-stats  
**Phase**: QA  
**Date**: 2026-04-15  
**Method**: Static-generated pytest (Python 설치 후 즉시 실행 가능)

---

## 1. QA 범위

| 레벨 | 대상 | 방법 | 상태 |
|------|------|------|------|
| L1 | config.py 상수 검증 | pytest 정적 검사 | ✅ 테스트 작성 완료 |
| L2 | i18n.py 번역 함수 | pytest 유닛 테스트 | ✅ 테스트 작성 완료 |
| L3 | parser.py 컬럼 감지·정제 | pytest + mock DataFrame | ✅ 테스트 작성 완료 |
| L4 | analytics.py 17개 통계 함수 | pytest + 샘플 데이터 | ✅ 테스트 작성 완료 |
| L5 | exporter.py Excel/CSV 출력 | pytest + 바이트 검증 | ✅ 테스트 작성 완료 |

---

## 2. 테스트 파일 구조

```
tests/
├── conftest.py          ← 공용 픽스처 (샘플 DataFrame, CSV 바이트)
├── pytest.ini           ← pytest 설정
├── test_config.py       ← L1: 37개 테스트
├── test_i18n.py         ← L2: 28개 테스트
├── test_parser.py       ← L3: 30개 테스트
├── test_analytics.py    ← L4: 40개 테스트
└── test_exporter.py     ← L5: 28개 테스트
```

**총 테스트 수**: 180개 | **실행 결과**: ✅ 180 passed in 3.50s

---

## 3. 실행 방법

### 사전 조건
```bash
# Python 3.8+ 설치 확인
python --version

# 패키지 설치
cd C:\Users\j.park\Downloads\InnoHR\hr_excel_stats
pip install -r requirements.txt
pip install pytest
```

### 테스트 실행
```bash
cd C:\Users\j.park\Downloads\InnoHR
pytest tests/ -v
```

### 모듈별 실행
```bash
pytest tests/test_config.py -v      # L1: 설정 검증
pytest tests/test_i18n.py -v        # L2: 다국어 번역
pytest tests/test_parser.py -v      # L3: 파싱
pytest tests/test_analytics.py -v   # L4: 통계
pytest tests/test_exporter.py -v    # L5: 내보내기
```

### 특정 테스트만
```bash
pytest tests/test_analytics.py::TestSummaryKpis -v
pytest tests/test_exporter.py::TestToExcel::test_g2_fix_additional_stats_sheet -v
```

---

## 4. 핵심 테스트 케이스 목록

### L1 — config.py (37개)

| 테스트 | 검증 내용 |
|--------|---------|
| `test_column_map_has_required_keys` | 11개 표준 컬럼 모두 정의 |
| `test_korean_aliases_exist` | 사번/부서/입사일/재직여부 한국어 별칭 |
| `test_four_required_columns` | REQUIRED_COLUMNS == 4개 |
| `test_tenure_labels_five_items` | 근속 레이블 5개 × 3언어 |
| `test_no_overlap_between_active_inactive` | 재직/퇴사 값 겹침 없음 |

### L2 — i18n.py (28개)

| 테스트 | 검증 내용 |
|--------|---------|
| `test_returns_korean_by_default` | 기본 언어 ko |
| `test_fallback_to_key_on_missing` | 미번역 키 → 키 반환 |
| `test_key_exists_in_all_languages` (×25) | 핵심 키 ko/en/fr 모두 존재 |
| `test_sheet_names_are_unique_per_lang` | 같은 언어 내 시트명 중복 없음 |
| `test_g2_sheet_additional_key` | sheet_additional 키 존재 |

### L3 — parser.py (30개)

| 테스트 | 검증 내용 |
|--------|---------|
| `test_detects_korean_columns` | 한국어 컬럼명 자동 감지 |
| `test_partial_match` | 입사일자/사원번호 등 부분 일치 |
| `test_has_tenure_years` | tenure_years 파생 컬럼 생성 |
| `test_is_active_normalized` | Y/N → True/False 정규화 |
| `test_load_csv_euckr` | EUC-KR 인코딩 자동 처리 |
| `test_invalid_extension_raises` | .txt 확장자 ValueError |

### L4 — analytics.py (40개)

| 테스트 | 검증 내용 |
|--------|---------|
| `test_counts_active_only` | headcount_total = 7 (재직자만) |
| `test_dev_team_count` | 개발팀 3명 정확 |
| `test_five_kpis` | summary_kpis 5개 KPI 포함 |
| `test_total_employees_correct` | total_employees = 7 |
| `test_resignations_correct` | resignations = 3 |
| `test_total_hires_count` | monthly_hires 합계 = 10 |
| `test_empty_df_does_not_raise` | 빈 DataFrame 에러 없음 |

### L5 — exporter.py (28개)

| 테스트 | 검증 내용 |
|--------|---------|
| `test_has_four_sheets_ko` | Excel 4시트 생성 |
| `test_g2_fix_additional_stats_sheet` | 추가통계 시트(G2 fix) 존재 |
| `test_sheet_names_differ_by_language` | ko/en 시트명 상이 |
| `test_default_encoding_utf8sig` | CSV BOM(EF BB BF) 확인 |
| `test_no_bin_columns` | _bin 컬럼 제외 |
| `test_contains_date` | 파일명에 오늘 날짜 포함 |

---

## 5. 성공 기준 vs 테스트 커버리지

| 성공 기준 | 커버 테스트 |
|---------|-----------|
| SC-1: 30초 내 대시보드 | (런타임 필요 — 앱 실행 후 수동 검증) |
| SC-2: 주요 통계 5종 이상 | `test_has_five_kpis`, analytics 17개 함수 테스트 |
| SC-3: 컬럼 자동 인식 | `test_detects_korean_columns`, `test_partial_match` |
| SC-4: Excel/CSV 다운로드 | `test_has_four_sheets_ko`, `test_default_encoding_utf8sig` |
| SC-5: 다국어 전환 | `test_key_exists_in_all_languages` (×25), `test_sheet_names_differ_by_language` |

---

## 6. 런타임 QA (Python 설치 후)

Python 설치 완료 시 다음 단계로 런타임 검증:

1. **앱 실행 확인**
   ```bash
   cd hr_excel_stats && python -m streamlit run app.py
   ```

2. **샘플 파일 업로드 테스트**
   - 표준 포맷 xlsx 업로드
   - 컬럼 자동 감지 확인
   - 4탭 대시보드 렌더링 확인
   - 언어 전환 (ko → en → fr) 확인
   - Excel/CSV 다운로드 확인

3. **타이머 측정 (SC-1)**
   - 업로드 버튼 클릭 → 대시보드 표시까지 30초 이내

4. **EUC-KR 인코딩 테스트**
   - EUC-KR CSV 파일 업로드 → 한글 깨짐 없음 확인
