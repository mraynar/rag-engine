"""
Auto-sanitization for tabular data ingestion.

Normalizes during ingestion WITHOUT touching original columns:
  _YEAR        — integer year extracted from any year/date column
  _MONTH_CODE  — integer month 1-12 from any format (English/Indonesian/numeric)
  _MONTH_EN    — English month name ("January".."December")
  _OPERATOR    — uppercase operator/LOP value

Executor/resolver use _YEAR and _MONTH_CODE exclusively — no more per-dataset
format workarounds needed. Works automatically for any new datasource added.
"""
import re
import pandas as pd
from typing import Optional

# ── Month normalization tables ──────────────────────────────────────────────

MONTH_TO_CODE = {
    # English full
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    # Indonesian full
    "januari": 1, "februari": 2, "maret": 3,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "oktober": 10, "desember": 12,
    # English abbreviated
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}

CODE_TO_EN = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}


def _parse_month(val) -> Optional[int]:
    """Convert any month representation to code 1-12 or None."""
    if val is None:
        return None
    try:
        n = int(float(str(val).strip()))
        if 1 <= n <= 12:
            return n
    except (ValueError, TypeError):
        pass
    if isinstance(val, str):
        key = val.strip().lower()
        if key in MONTH_TO_CODE:
            return MONTH_TO_CODE[key]
        m = re.match(r'^\d{4}-(\d{2})', key)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 12:
                return n
    try:
        dt = pd.to_datetime(val, errors='coerce')
        if dt is not pd.NaT and not pd.isna(dt):
            return int(dt.month)
    except Exception:
        pass
    return None


def _parse_year(val) -> Optional[int]:
    """Extract a valid year (1990-2100) from any representation."""
    if val is None:
        return None
    try:
        n = int(float(str(val).strip()))
        if 1990 <= n <= 2100:
            return n
    except (ValueError, TypeError):
        pass
    if isinstance(val, str):
        m = re.match(r'^(\d{4})-', val.strip())
        if m:
            n = int(m.group(1))
            if 1990 <= n <= 2100:
                return n
    try:
        dt = pd.to_datetime(val, errors='coerce')
        if dt is not pd.NaT and not pd.isna(dt):
            yr = int(dt.year)
            if 1990 <= yr <= 2100:
                return yr
    except Exception:
        pass
    return None


def _normalize_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """Add _YEAR, _MONTH_CODE, _MONTH_EN. Original columns untouched."""
    # Best YEAR source priority
    year_col = None
    for priority in ["YEAR", "TAHUN"]:
        for c in df.columns:
            if c.upper().strip() == priority:
                year_col = c
                break
        if year_col:
            break
    if not year_col:
        for c in df.columns:
            if any(kw in c.upper().strip() for kw in ["DATE", "TANGGAL", "TIMESTAMP"]):
                year_col = c
                break

    if year_col and "_YEAR" not in df.columns:
        df = df.copy()
        df["_YEAR"] = df[year_col].apply(_parse_year).astype("Int64")

    # Best MONTH source priority
    month_col = None
    for priority in ["MONTH", "BULAN", "MONTH_CODE"]:
        for c in df.columns:
            if c.upper().strip() == priority:
                month_col = c
                break
        if month_col:
            break
    if not month_col and year_col:
        for c in df.columns:
            if any(kw in c.upper().strip() for kw in ["DATE", "TANGGAL", "TIMESTAMP"]):
                month_col = c
                break

    if month_col and "_MONTH_CODE" not in df.columns:
        if "_YEAR" not in df.columns:
            df = df.copy()
        codes = df[month_col].apply(_parse_month)
        df["_MONTH_CODE"] = codes.astype("Int64")
        df["_MONTH_EN"] = codes.map(lambda c: CODE_TO_EN.get(c) if c is not None else None)

    return df


def _normalize_operator(df: pd.DataFrame) -> pd.DataFrame:
    """Add _OPERATOR (uppercase) from LOP/VESSEL OPERATOR column."""
    op_col = None
    for c in df.columns:
        cu = c.upper().strip()
        if cu in ["LOP", "VESSEL OPERATOR", "VESSELOPERATOR", "OPERATOR", "NAMA PERUSAHAAN"]:
            op_col = c
            break
    if op_col and "_OPERATOR" not in df.columns:
        df["_OPERATOR"] = df[op_col].astype(str).str.upper().str.strip().where(
            df[op_col].notna(), other=None
        )
    return df


def _deduplicate_column_names(column_names: list) -> list:
    counts = {}
    used_names = set()
    unique_names = []
    for column_name in column_names:
        count = counts.get(column_name, 0) + 1
        unique_name = column_name if count == 1 else f"{column_name}_{count}"
        while unique_name in used_names:
            count += 1
            unique_name = f"{column_name}_{count}"
        counts[column_name] = count
        used_names.add(unique_name)
        unique_names.append(unique_name)
    return unique_names


def sanitize_and_combine(xls: dict) -> tuple:
    """
    Normalize, sanitize, and combine tabular sheets into one DataFrame.

    Every row gets extra normalized columns alongside originals:
      _sheet       — source sheet name
      _YEAR        — integer year or null
      _MONTH_CODE  — integer month 1-12 or null  
      _MONTH_EN    — English month name or null
      _OPERATOR    — uppercase operator/LOP or null
    """
    sanitized_dfs = []
    sync_stats = {}

    for sheet_name, df in xls.items():
        before = df.shape[0]
        df.columns = [str(col).strip().upper() for col in df.columns]
        unique_columns = _deduplicate_column_names(list(df.columns))
        if unique_columns != list(df.columns):
            print(f"[sanitize] Sheet '{sheet_name}': renamed duplicate columns")
        df.columns = unique_columns
        df = df.dropna(how="all")
        df = df.drop_duplicates()
        after = df.shape[0]
        sync_stats[sheet_name] = {"raw_rows": before, "final_rows": after, "dropped_rows": before - after}
        print(f"[sanitize] Sheet '{sheet_name}': {before} → {after} rows")
        df = df.copy()
        df.insert(0, "_sheet", sheet_name)
        df = _normalize_temporal(df)
        df = _normalize_operator(df)
        sanitized_dfs.append(df)

    if not sanitized_dfs:
        raise ValueError("No data found in any sheet after sanitization.")

    combined_df = pd.concat(sanitized_dfs, axis=0, ignore_index=True)
    all_cols = [c for c in combined_df.columns if c != "_sheet"]
    column_schema = {"_all_sheets": all_cols}
    for df_sheet in sanitized_dfs:
        sname = df_sheet["_sheet"].iloc[0] if not df_sheet.empty else "unknown"
        column_schema[sname] = [c for c in df_sheet.columns if c != "_sheet"]

    return combined_df, column_schema, sync_stats


def _dataframe_to_clean_records_legacy(combined_df: pd.DataFrame) -> list:
    clean_records = []
    for _, row in combined_df.iterrows():
        clean_record = {}
        for k, v in row.items():
            try:
                is_null = pd.isnull(v)
            except (TypeError, ValueError):
                is_null = False
            if is_null:
                v_clean = None
            elif hasattr(v, "isoformat"):
                v_clean = v.isoformat()
            elif hasattr(v, "item"):
                try:
                    v_clean = v.item()
                except Exception:
                    v_clean = str(v)
            else:
                v_clean = v
            clean_record[str(k)] = v_clean
        clean_records.append(clean_record)
    return clean_records


def dataframe_to_clean_records(combined_df: pd.DataFrame) -> list:
    """Serialize DataFrame to clean JSON-safe list of dicts."""
    try:
        clean_df = combined_df.copy()

        def serialize_value(value):
            try:
                is_null = pd.isnull(value)
            except (TypeError, ValueError):
                is_null = False
            if is_null:
                return None
            if hasattr(value, "isoformat"):
                return value.isoformat()
            if hasattr(value, "item"):
                try:
                    return value.item()
                except Exception:
                    return str(value)
            return value

        for column_name in clean_df.columns:
            serialized = clean_df[column_name].astype(object).apply(serialize_value)
            clean_df[column_name] = pd.Series(
                serialized.tolist(), index=serialized.index, dtype=object
            ).where(lambda s: pd.notna(s), None)

        return clean_df.to_dict(orient="records")
    except Exception as error:
        print(f"[dataframe_to_clean_records] Fast path failed, fallback: {error}")
        return _dataframe_to_clean_records_legacy(combined_df)
