# Design Ref: §3.3 — 엑셀/CSV 파싱, 컬럼 자동 매핑, 데이터 정제
"""
parser.py — HR 엑셀 파일 파싱 모듈

파일 로드 → 컬럼 자동 감지 → 검증 → 데이터 정제 흐름을 담당합니다.

Plan SC: 컬럼 매핑 오류 없이 표준 포맷 자동 인식
Plan SC: 엑셀 업로드 후 30초 내 대시보드 표시
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Optional

import pandas as pd

from config import (
    ACTIVE_VALUES,
    AGE_BINS,
    AGE_LABELS,
    COLUMN_MAP,
    INACTIVE_VALUES,
    REQUIRED_COLUMNS,
    TENURE_BINS,
    TENURE_LABELS,
)


# ── 파일 로드 ──────────────────────────────────────────────────────────────

def load_file(file_obj, filename: str) -> pd.DataFrame:
    """
    업로드된 파일 객체를 DataFrame으로 로드.

    지원 형식: .xlsx, .xls, .csv
    인코딩 자동 감지: utf-8-sig → euc-kr → cp949

    Args:
        file_obj: Streamlit UploadedFile 또는 file-like 객체
        filename: 파일명 (확장자 감지용)

    Returns:
        로드된 DataFrame (컬럼명 정규화 전)

    Raises:
        ValueError: 지원하지 않는 파일 형식
        UnicodeDecodeError: 인코딩 실패
    """
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext in ("xlsx", "xlsm"):
        df = pd.read_excel(file_obj, engine="openpyxl")
    elif ext == "xls":
        df = pd.read_excel(file_obj, engine="xlrd")
    elif ext == "csv":
        df = _load_csv(file_obj)
    else:
        raise ValueError(f"Unsupported file type: .{ext}")

    # 컬럼명 앞뒤 공백 제거
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _load_csv(file_obj) -> pd.DataFrame:
    """CSV 파일을 인코딩 자동 감지하여 로드."""
    raw = file_obj.read() if hasattr(file_obj, "read") else file_obj
    if isinstance(file_obj, (bytes, bytearray)):
        raw = file_obj

    for encoding in ("utf-8-sig", "utf-8", "euc-kr", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=encoding)
        except (UnicodeDecodeError, Exception):
            continue

    raise UnicodeDecodeError("csv", b"", 0, 1, "Cannot decode CSV with known encodings")


# ── 컬럼 감지 ─────────────────────────────────────────────────────────────

def detect_columns(df: pd.DataFrame, column_map: dict | None = None) -> dict[str, str | None]:
    """
    DataFrame 컬럼명을 표준 컬럼명으로 자동 매핑.

    매핑 전략:
      1. 정확히 일치 (대소문자·공백 무시)
      2. 포함 관계 (표준 후보 키워드가 실제 컬럼에 포함)

    Args:
        df: 원본 DataFrame
        column_map: 커스텀 컬럼 매핑 (없으면 config.COLUMN_MAP 사용)

    Returns:
        {표준_컬럼명: 실제_컬럼명 or None}
    """
    cmap = column_map or COLUMN_MAP
    actual_cols = list(df.columns)
    # 정규화된 실제 컬럼명 목록
    normalized = {_normalize(c): c for c in actual_cols}

    mapping: dict[str, str | None] = {}

    for std_key, candidates in cmap.items():
        found = None
        for candidate in candidates:
            norm_candidate = _normalize(candidate)
            # 1) 정확 일치
            if norm_candidate in normalized:
                found = normalized[norm_candidate]
                break
        if found is None:
            # 2) 포함 관계 (실제 컬럼명이 후보 키워드를 포함)
            for norm_actual, actual in normalized.items():
                for candidate in candidates:
                    if _normalize(candidate) in norm_actual:
                        found = actual
                        break
                if found:
                    break
        mapping[std_key] = found

    return mapping


def _normalize(text: str) -> str:
    """컬럼명 정규화: 소문자, 공백/특수문자 제거."""
    return re.sub(r"[\s_\-\.]", "", str(text).lower().strip())


# ── 검증 ──────────────────────────────────────────────────────────────────

def validate_mapping(mapping: dict[str, str | None]) -> tuple[bool, list[str]]:
    """
    필수 컬럼이 모두 매핑되었는지 검증.

    Args:
        mapping: detect_columns() 결과

    Returns:
        (is_valid, missing_required_columns)
    """
    missing = [col for col in REQUIRED_COLUMNS if mapping.get(col) is None]
    return len(missing) == 0, missing


# ── 데이터 정제 ───────────────────────────────────────────────────────────

def clean_data(df: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    """
    원본 DataFrame을 표준 컬럼명으로 변환하고 파생 컬럼을 생성.

    처리 내용:
      - 매핑된 컬럼만 선택 후 표준명으로 rename
      - 날짜 컬럼 파싱 (hire_date, birth_date, resign_date)
      - is_active 정규화 → bool
      - 파생 컬럼 생성: tenure_years, age, age_group, age_bin,
                        hire_year_month, resign_year_month, tenure_group

    Args:
        df: 원본 DataFrame
        mapping: detect_columns() 결과

    Returns:
        정제된 DataFrame (표준 컬럼명 사용)
    """
    # 매핑된 컬럼만 선택 → 표준명으로 rename
    rename_map = {v: k for k, v in mapping.items() if v is not None}
    cols_to_keep = list(rename_map.keys())
    df_clean = df[cols_to_keep].rename(columns=rename_map).copy()

    today = pd.Timestamp(date.today())

    # ── 날짜 파싱 ─────────────────────────────────────
    for date_col in ("hire_date", "birth_date", "resign_date"):
        if date_col in df_clean.columns:
            df_clean[date_col] = pd.to_datetime(
                df_clean[date_col], errors="coerce", dayfirst=False
            )

    # ── is_active 정규화 ──────────────────────────────
    if "is_active" in df_clean.columns:
        df_clean["is_active"] = df_clean["is_active"].apply(_normalize_active)
    elif "resign_date" in df_clean.columns:
        # 퇴사일이 있으면 퇴사자, 없으면 재직
        df_clean["is_active"] = df_clean["resign_date"].isna()
    else:
        df_clean["is_active"] = True  # 정보 없으면 전원 재직 가정

    # ── 파생 컬럼: 근속연수 ───────────────────────────
    if "hire_date" in df_clean.columns:
        df_clean["tenure_years"] = (
            (today - df_clean["hire_date"]).dt.days / 365.25
        ).round(1)
        df_clean["hire_year_month"] = df_clean["hire_date"].dt.strftime("%Y-%m")

        # 근속연수 구간 (tenure_group은 config.TENURE_LABELS 키로 조회)
        df_clean["tenure_bin"] = pd.cut(
            df_clean["tenure_years"],
            bins=TENURE_BINS,
            labels=range(len(TENURE_BINS) - 1),
            right=False,
        ).astype("Int64")

    # ── 파생 컬럼: 연령 ───────────────────────────────
    if "birth_date" in df_clean.columns:
        df_clean["age"] = (
            (today - df_clean["birth_date"]).dt.days / 365.25
        ).round(1)
        df_clean["age_bin"] = pd.cut(
            df_clean["age"],
            bins=AGE_BINS,
            labels=range(len(AGE_BINS) - 1),
            right=False,
        ).astype("Int64")

    # ── 파생 컬럼: 퇴사 월 ───────────────────────────
    if "resign_date" in df_clean.columns:
        df_clean["resign_year_month"] = df_clean["resign_date"].dt.strftime("%Y-%m")

    # ── 성별 정규화 ───────────────────────────────────
    if "gender" in df_clean.columns:
        df_clean["gender"] = df_clean["gender"].apply(_normalize_gender)

    # ── Full Name 합치기 ─────────────────────────────
    # name 컬럼이 없고 last_name/first_name 이 있으면 합칩니다.
    # name 컬럼이 있어도 last_name+first_name 이 더 풍부하면 덮어씁니다.
    has_last  = "last_name"  in df_clean.columns
    has_first = "first_name" in df_clean.columns

    if has_last or has_first:
        def _combine(row):
            last  = str(row.get("last_name",  "") or "").strip()
            first = str(row.get("first_name", "") or "").strip()
            parts = [p for p in [last, first] if p and p.lower() != "nan"]
            return " ".join(parts) if parts else ""

        combined = df_clean.apply(_combine, axis=1)

        # name 컬럼 없거나 비어있는 경우 채워 넣기
        if "name" not in df_clean.columns:
            df_clean["name"] = combined
        else:
            # 기존 name 값이 있는 행은 유지, 없는 행만 combined 로 채움
            mask_empty = df_clean["name"].isna() | (df_clean["name"].astype(str).str.strip() == "")
            df_clean.loc[mask_empty, "name"] = combined[mask_empty]

            # last+first 조합이 더 길면 (= 성+이름 분리 저장된 경우) combined 를 사용
            longer = combined.str.len() > df_clean["name"].str.len().fillna(0)
            df_clean.loc[longer, "name"] = combined[longer]

    return df_clean


def _normalize_active(value) -> bool:
    """재직여부 값을 bool로 정규화."""
    if pd.isna(value):
        return True
    if value in ACTIVE_VALUES:
        return True
    if value in INACTIVE_VALUES:
        return False
    # 문자열 추가 처리
    str_val = str(value).strip().upper()
    if str_val in {"Y", "YES", "TRUE", "재직", "O", "1"}:
        return True
    if str_val in {"N", "NO", "FALSE", "퇴사", "X", "0"}:
        return False
    return True  # 알 수 없으면 재직 가정


def _normalize_gender(value) -> str:
    """성별 값을 M/F/기타로 정규화."""
    if pd.isna(value):
        return "기타"
    str_val = str(value).strip()
    if str_val in {"남", "남자", "M", "m", "Male", "male", "MALE",
                   "H", "h", "Homme", "homme", "HOMME"}:   # H = Homme (French)
        return "남"
    if str_val in {"여", "여자", "F", "f", "Female", "female", "FEMALE",
                   "Femme", "femme", "FEMME"}:              # Femme (French)
        return "여"
    return "기타"


# ── 필터 헬퍼 ─────────────────────────────────────────────────────────────

def filter_active(df: pd.DataFrame) -> pd.DataFrame:
    """재직자만 필터링."""
    if "is_active" in df.columns:
        return df[df["is_active"] == True].copy()
    return df


def filter_resigned(df: pd.DataFrame) -> pd.DataFrame:
    """퇴사자만 필터링."""
    if "is_active" in df.columns:
        return df[df["is_active"] == False].copy()
    return pd.DataFrame(columns=df.columns)


def filter_by_date_range(
    df: pd.DataFrame,
    date_col: str,
    start: Optional[str | pd.Timestamp] = None,
    end: Optional[str | pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    특정 날짜 컬럼 기준으로 기간 필터링.

    Args:
        df: DataFrame
        date_col: 필터 기준 컬럼명 (예: "hire_date", "resign_date")
        start: 시작일 (None이면 제한 없음)
        end: 종료일 (None이면 제한 없음)
    """
    if date_col not in df.columns:
        return df
    mask = pd.Series([True] * len(df), index=df.index)
    if start:
        mask &= df[date_col] >= pd.Timestamp(start)
    if end:
        mask &= df[date_col] <= pd.Timestamp(end)
    return df[mask].copy()


def filter_by_department(df: pd.DataFrame, departments: list[str]) -> pd.DataFrame:
    """부서 목록으로 필터링. 빈 목록이면 전체 반환."""
    if not departments or "department" not in df.columns:
        return df
    return df[df["department"].isin(departments)].copy()


# ── 요약 정보 ─────────────────────────────────────────────────────────────

def get_date_range(df: pd.DataFrame, date_col: str = "hire_date") -> tuple[str, str]:
    """데이터의 날짜 범위 반환 (YYYY-MM 형식)."""
    if date_col not in df.columns:
        return ("", "")
    valid = df[date_col].dropna()
    if valid.empty:
        return ("", "")
    return (
        valid.min().strftime("%Y-%m"),
        valid.max().strftime("%Y-%m"),
    )


def get_departments(df: pd.DataFrame) -> list[str]:
    """고유 부서 목록 반환 (정렬)."""
    if "department" not in df.columns:
        return []
    return sorted(df["department"].dropna().unique().tolist())


def get_column_mapping_summary(mapping: dict[str, str | None]) -> list[dict]:
    """
    컬럼 매핑 요약 정보 반환 (UI 표시용).

    Returns:
        [{"standard": "사번", "detected": "EMP_ID", "found": True}, ...]
    """
    from config import COLUMN_MAP
    result = []
    for std_key in COLUMN_MAP.keys():
        detected = mapping.get(std_key)
        result.append({
            "standard": std_key,
            "detected": detected or "",
            "found": detected is not None,
            "required": std_key in REQUIRED_COLUMNS,
        })
    return result
