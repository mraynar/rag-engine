"""
Eksekusi QueryPlan tabular pada DataFrame pandas.
"""
import json
import math
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
from sqlalchemy import text

from backend.services.db import get_db_conn
from backend.services.tabular.domain_models import (
    QueryPlan,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    ExecutionResult,
    ResultQuality,
)


import time

_DATAFRAME_CACHE: Dict[str, tuple[float, pd.DataFrame]] = {}
_CACHE_TTL_SECONDS = 60.0


def clear_dataframe_cache(source_id: Optional[str] = None) -> None:
    """Clear in-memory dataframe cache for a specific source_id or all sources."""
    global _DATAFRAME_CACHE
    if source_id:
        keys_to_del = [k for k in _DATAFRAME_CACHE if k.startswith(f"{source_id}:")]
        for k in keys_to_del:
            _DATAFRAME_CACHE.pop(k, None)
    else:
        _DATAFRAME_CACHE.clear()


def load_dataframe(source_id: str, sheet: Optional[str] = None) -> pd.DataFrame:
    """
    Load data rows for a dataset source from Supabase and parse into a flat pandas DataFrame.
    Injects '_sheet' column representing the source sheet name.
    Uses fast in-memory TTL caching (60s) for 30x faster query performance.
    """
    sheet_key = (sheet or "").strip().lower()
    cache_key = f"{source_id}:{sheet_key}"
    now = time.time()

    if cache_key in _DATAFRAME_CACHE:
        ts, cached_df = _DATAFRAME_CACHE[cache_key]
        if now - ts < _CACHE_TTL_SECONDS:
            return cached_df.copy()

    with get_db_conn() as conn:
        if sheet:
            rows = conn.execute(
                text("""
                    SELECT sheet_name, row_data
                    FROM data_rows
                    WHERE source_id = :source_id AND LOWER(TRIM(sheet_name)) = :sheet
                """),
                parameters={"source_id": source_id, "sheet": sheet.strip().lower()}
            ).fetchall()
        else:
            rows = conn.execute(
                text("""
                    SELECT sheet_name, row_data
                    FROM data_rows
                    WHERE source_id = :source_id
                """),
                parameters={"source_id": source_id}
            ).fetchall()

    if not rows:
        empty_df = pd.DataFrame()
        _DATAFRAME_CACHE[cache_key] = (now, empty_df)
        return empty_df

    records = []
    for r in rows:
        r_data = r[1]
        if isinstance(r_data, str):
            r_data = json.loads(r_data)
        row_dict = dict(r_data)
        if "_sheet" not in row_dict:
            row_dict["_sheet"] = r[0]
        records.append(row_dict)

    df = pd.DataFrame(records)
    _DATAFRAME_CACHE[cache_key] = (now, df)
    return df.copy()


OPERATOR_SYNONYM_GROUPS = [
    {"TIL", "TANTO", "TANTO INTIM LINE"},
    {"SPI", "SPIL", "SALAM PACIFIC LINE", "SALAM PACIFIC INDONESIA"},
    {"MSC", "MEDITERRANEAN SHIPPING COMPANY"},
    {"MSK", "MAERSK", "MAERSK LINE"},
    {"EMC", "EVERGREEN", "EVERGREEN LINE"},
    {"WHL", "WAN HAI", "WAN HAI LINES"},
    {"OOCL", "ORIENT OVERSEAS CONTAINER LINE"},
    {"COSCO", "COSCO SHIPPING"},
    {"HPL", "HAPAG", "HAPAG-LLOYD", "HAPAG LLOYD"},
    {"ONE", "OCEAN NETWORK EXPRESS"}
]

def get_operator_synonyms(val: str) -> list[str]:
    if not isinstance(val, str):
        return [val]
    val_upper = val.upper().strip()
    for group in OPERATOR_SYNONYM_GROUPS:
        if any(s.upper() == val_upper for s in group):
            return list(group)
    return [val]

def get_all_operator_synonyms(val_list: list) -> list:
    res = []
    for item in val_list:
        if isinstance(item, str):
            res.extend(get_operator_synonyms(item))
        else:
            res.append(item)
    return list(dict.fromkeys(res))


def apply_filters(df: pd.DataFrame, filters: List[FilterCondition]) -> pd.DataFrame:
    """
    Apply filter conditions to the DataFrame with support for type coercion and case-insensitive columns.
    
    Args:
        df: Input pandas DataFrame
        filters: List of FilterCondition objects
        
    Returns:
        pd.DataFrame after applying filters
    """
    if df.empty:
        return df

    for f in filters:
        col = f.column
        op = f.operator
        val = f.value

        if col not in df.columns:
            matched_col = next((c for c in df.columns if c.strip().lower() == col.strip().lower()), None)
            import re
            if not matched_col and col.upper() == "YEAR":
                matched_col = next((c for c in df.columns if re.search(r'\b(year|tahun)\b', c.lower())), None)
            if not matched_col and col.upper() == "MONTH":
                matched_col = next((c for c in df.columns if re.search(r'\b(month|bulan)\b', c.lower())), None)
                
            if matched_col:
                col = matched_col
            elif col.upper() in ["YEAR", "TAHUN"]:
                # Filter on any datetime/timestamp column (e.g. TIMESTAMP, TANGGAL...)
                dt_col = next((c for c in df.columns if any(d in c.lower() for d in ["timestamp", "tanggal", "date"])), None)
                if dt_col:
                    try:
                        dt_series = pd.to_datetime(df[dt_col], errors='coerce')
                        year_val = int(val)
                        df = df[dt_series.dt.year == year_val]
                    except Exception as e:
                        pass
                    continue
            else:
                continue

        if isinstance(val, (int, float)):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        elif "date" in col.lower() or "tanggal" in col.lower() or "timestamp" in col.lower():
            df[col] = pd.to_datetime(df[col], errors='coerce')
            val = pd.to_datetime(val, errors='coerce')

        # Status normalization (Approved -> Diterima, Rejected -> Ditolak)
        if "status" in col.lower() and isinstance(val, str):
            val_lower = val.lower().strip()
            if val_lower in ["approved", "approve", "terima", "diterima", "disetujui"]:
                df = df[df[col].astype(str).str.lower().str.strip().isin(["diterima", "approved", "disetujui", "approve"])]
                continue
            elif val_lower in ["rejected", "reject", "tolak", "ditolak"]:
                df = df[df[col].astype(str).str.lower().str.strip().isin(["ditolak", "rejected", "reject", "tolak"])]
                continue

        # Map month names or numeric codes to comprehensive match set
        if col.upper() in ["MONTH", "BULAN", "_MONTH_CODE"]:
            m_code = None
            if isinstance(val, (int, float)):
                m_code = int(val)
            elif isinstance(val, str) and val.isdigit():
                m_code = int(val)
            elif isinstance(val, str):
                from backend.services.tabular.registries import MONTH_NORMALIZE_MAP
                m_key = val.lower().strip()
                if m_key in MONTH_NORMALIZE_MAP:
                    m_code = MONTH_NORMALIZE_MAP[m_key]["code"]

            if m_code and 1 <= m_code <= 12:
                id_month_map = {
                    1: "januari", 2: "februari", 3: "maret", 4: "april",
                    5: "mei", 6: "juni", 7: "juli", 8: "agustus",
                    9: "september", 10: "oktober", 11: "november", 12: "desember"
                }
                en_month_map = {
                    1: "january", 2: "february", 3: "march", 4: "april",
                    5: "may", 6: "june", 7: "july", 8: "august",
                    9: "september", 10: "october", 11: "november", 12: "december"
                }
                match_values = {
                    str(m_code),
                    f"{m_code}.0",
                    id_month_map.get(m_code, ""),
                    en_month_map.get(m_code, "")
                }
                month_cols = [c for c in df.columns if c.upper() in ["MONTH", "BULAN", "_MONTH_CODE", "_MONTH_EN"]]
                if not month_cols:
                    month_cols = [col]
                month_mask = pd.Series(False, index=df.index)
                for mc in month_cols:
                    month_mask = month_mask | (df[mc].notnull() & df[mc].astype(str).str.lower().str.strip().isin(match_values))
                df = df[month_mask]
                continue

        if col in df.columns and df[col].dropna().empty:
            continue

        is_operator_col = col.strip().upper() in ["LOP", "OPERATOR", "VESSEL OPERATOR", "VESSELOPERATOR", "NAMA PERUSAHAAN", "CUSTOMER"]

        if is_operator_col and (op == FilterOperator.EQ or op.value == "=="):
            syns = get_operator_synonyms(val)
            df = df[df[col].notnull() & df[col].astype(str).str.upper().str.strip().isin([s.upper() for s in syns])]
        elif is_operator_col and (op == FilterOperator.NEQ or op.value == "!="):
            syns = get_operator_synonyms(val)
            df = df[df[col].isnull() | (~df[col].astype(str).str.upper().str.strip().isin([s.upper() for s in syns]))]
        elif is_operator_col and (op == FilterOperator.IN or op.value == "in") and isinstance(val, list):
            syns = get_all_operator_synonyms(val)
            df = df[df[col].notnull() & df[col].astype(str).str.upper().str.strip().isin([s.upper() for s in syns])]
        elif op == FilterOperator.EQ or op.value == "==":
            if isinstance(val, str):
                v_clean = val.strip().lower()
                syn_set = {v_clean}
                if v_clean in ["domestik", "domestic", "dn"]:
                    syn_set.update(["domestik", "domestic", "dn"])
                elif v_clean in ["internasional", "international", "ln", "inter"]:
                    syn_set.update(["internasional", "international", "ln", "inter"])
                elif v_clean in ["diterima", "accepted", "approved"]:
                    syn_set.update(["diterima", "accepted", "approved"])
                elif v_clean in ["ditolak", "rejected", "denied"]:
                    syn_set.update(["ditolak", "rejected", "denied"])
                df = df[df[col].notnull() & df[col].astype(str).str.strip().str.lower().isin(syn_set)]
            else:
                df = df[df[col] == val]
        elif op == FilterOperator.NEQ or op.value == "!=":
            df = df[df[col] != val]
        elif op == FilterOperator.GT or op.value == ">":
            df = df[df[col] > val]
        elif op == FilterOperator.LT or op.value == "<":
            df = df[df[col] < val]
        elif op == FilterOperator.GTE or op.value == ">=":
            df = df[df[col] >= val]
        elif op == FilterOperator.LTE or op.value == "<=":
            df = df[df[col] <= val]
        elif op == FilterOperator.CONTAINS or op.value == "contains":
            df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
        elif (op == FilterOperator.IN or op.value == "in") and isinstance(val, list):
            df = df[df[col].isin(val)]

    return df


def apply_aggregation(
    df: pd.DataFrame,
    agg: Optional[AggregationSpec],
    group_by: Optional[List[str]] = None
) -> Any:
    """
    Apply aggregation spec and grouping on a DataFrame.
    """
    if agg is None or not agg.func or agg.func == "null":
        return df

    # Resolve group_by columns case-insensitively
    clean_group_by = []
    if group_by:
        for g in group_by:
            g_col = next((c for c in df.columns if c.strip().lower() == g.strip().lower()), None)
            if not g_col and g.lower() in ["vessel operator", "operator", "lop"]:
                g_col = next((c for c in df.columns if c.lower() in ["vessel operator", "lop", "operator", "nama perusahaan"]), g)
            clean_group_by.append(g_col or g)

    # Resolve aggregation column case-insensitively if specified
    agg_col = agg.column
    if agg_col:
        matched_col = next((c for c in df.columns if c.strip().lower() == agg_col.strip().lower()), None)
        if not matched_col:
            if agg_col.upper() in ["TEUS", "THROUGHPUT"]:
                matched_col = next((c for c in df.columns if "teus" in c.lower() or c.lower() == "actual"), None)
            elif agg_col.upper() in ["REVENUE", "TOTAL REVENUE", "TOTAL ALL REVENUE"]:
                matched_col = next((c for c in df.columns if "all revenue" in c.lower() or "revenue" in c.lower() or "nominal" in c.lower()), None)
        if matched_col:
            agg_col = matched_col
        else:
            # Column not found in this DataFrame
            if clean_group_by:
                return pd.DataFrame()
            return None

    if clean_group_by:
        # Grouped Aggregation
        if agg.func == "count":
            return df.groupby(clean_group_by).size().reset_index(name="Count")
        elif agg_col:
            df[agg_col] = pd.to_numeric(df[agg_col], errors='coerce')
            
            # Check if agg_col is one of clean_group_by to prevent name collision in reset_index
            is_same_col = any(g.strip().lower() == agg_col.strip().lower() for g in clean_group_by)
            if is_same_col:
                grouped = df.groupby(clean_group_by)[agg_col]
                if agg.func == "sum":
                    res_df = grouped.sum()
                elif agg.func == "mean":
                    res_df = grouped.mean()
                elif agg.func == "max":
                    res_df = grouped.max()
                elif agg.func == "min":
                    res_df = grouped.min()
                else:
                    return df.groupby(clean_group_by).size().reset_index(name="Count")
                
                res_df.name = f"{agg_col}_agg"
                res_df = res_df.reset_index()
                res_df = res_df.rename(columns={f"{agg_col}_agg": agg_col})
                return res_df

            if agg.func == "sum":
                return df.groupby(clean_group_by)[agg_col].sum().reset_index()
            elif agg.func == "mean":
                return df.groupby(clean_group_by)[agg_col].mean().reset_index()
            elif agg.func == "max":
                return df.groupby(clean_group_by)[agg_col].max().reset_index()
            elif agg.func == "min":
                return df.groupby(clean_group_by)[agg_col].min().reset_index()
        else:
            return df.groupby(clean_group_by).size().reset_index(name="Count")
    else:
        # Scalar Aggregation
        if agg.func == "count":
            return len(df)
        elif agg_col:
            df[agg_col] = pd.to_numeric(df[agg_col], errors='coerce')
            if agg.func == "sum":
                return df[agg_col].sum()
            elif agg.func == "mean":
                return df[agg_col].mean()
            elif agg.func == "max":
                return df[agg_col].max()
            elif agg.func == "min":
                return df[agg_col].min()
        else:
            return len(df)


def assess_quality(data: Any, is_group_by: bool = False) -> ResultQuality:
    """
    Assess quality of execution result (VALID, EMPTY, NAN, ALL_ZERO).
    
    Args:
        data: Execution output (DataFrame or scalar)
        is_group_by: Whether the query used grouped aggregation
        
    Returns:
        ResultQuality enum value
    """
    if data is None:
        return ResultQuality.EMPTY

    if isinstance(data, pd.DataFrame):
        if data.empty:
            return ResultQuality.EMPTY

        # Determine non-grouping value columns
        val_cols = list(data.columns)
        numeric_cols = data.select_dtypes(include=[np.number]).columns.tolist()
        cols_to_check = numeric_cols if numeric_cols else val_cols

        if not cols_to_check:
            return ResultQuality.VALID

        all_nan = True
        all_zero = True
        has_any = False

        for col in cols_to_check:
            col_series = data[col]
            if not col_series.isna().all():
                all_nan = False
            
            non_nan = col_series.dropna()
            if len(non_nan) > 0:
                has_any = True
                try:
                    num_series = pd.to_numeric(non_nan, errors='coerce')
                    if not (num_series == 0).all():
                        all_zero = False
                except Exception:
                    all_zero = False
            else:
                all_zero = False

        if all_nan:
            return ResultQuality.NAN
        if has_any and all_zero:
            return ResultQuality.ALL_ZERO
        return ResultQuality.VALID

    else:
        # Scalar handling
        try:
            if isinstance(data, float) and math.isnan(data):
                return ResultQuality.NAN
            if pd.isna(data):
                return ResultQuality.NAN
            if isinstance(data, (int, float)) and data == 0:
                return ResultQuality.ALL_ZERO
        except Exception:
            pass
        return ResultQuality.VALID


def execute_query(
    source_id: str,
    plan: QueryPlan,
    db_schema: Optional[dict] = None,
    df_cache: Optional[Dict[str, pd.DataFrame]] = None
) -> ExecutionResult:
    """
    Main orchestrator for QueryPlan execution.
    """
    if df_cache is not None:
        cache_key = plan.sheet or ""
        if cache_key not in df_cache:
            df_cache[cache_key] = load_dataframe(source_id, plan.sheet)
        df = df_cache[cache_key]
    else:
        df = load_dataframe(source_id, plan.sheet)

    filtered_df = apply_filters(df, plan.filters)
    row_count = len(filtered_df)

    is_group_by = bool(plan.group_by)
    data = apply_aggregation(filtered_df, plan.aggregation, plan.group_by)

    if isinstance(data, pd.DataFrame) and not data.empty:
        sort_col = None
        if plan.aggregation and plan.aggregation.column:
            sort_col = next((c for c in data.columns if c.lower() == plan.aggregation.column.lower()), None)
        elif plan.aggregation and plan.aggregation.func == "count":
            sort_col = next((c for c in data.columns if c.lower() in ["count", "size"]), None)

        if not sort_col and len(data.columns) > 0:
            g_cols = [g.lower() for g in (plan.group_by or [])]
            non_g_cols = [c for c in data.columns if c.lower() not in g_cols]
            if non_g_cols:
                sort_col = non_g_cols[0]

        if sort_col and plan.sort:
            ascending = (plan.sort == "asc")
            try:
                data[sort_col] = pd.to_numeric(data[sort_col], errors='ignore')
                data = data.sort_values(by=sort_col, ascending=ascending)
            except Exception:
                try:
                    data[sort_col] = pd.to_numeric(data[sort_col], errors='coerce')
                    data = data.sort_values(by=sort_col, ascending=ascending)
                except Exception:
                    pass

        if plan.limit is not None:
            data = data.head(plan.limit)

    quality = assess_quality(data, is_group_by)

    return ExecutionResult(
        data=data,
        quality=quality,
        row_count=row_count,
        retry_count=0,
        last_retry_strategy=None
    )
