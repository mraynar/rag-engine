"""
Executor module for executing Tabular QueryPlans against database-loaded DataFrames.
Part of the Phase 2F implementation (TDD Green Phase).
"""
import json
import math
from typing import Optional, List, Dict, Any

import numpy as np
import pandas as pd
from sqlalchemy import text

from app.services.db import get_db_conn
from app.services.tabular.domain_models import (
    QueryPlan,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    ExecutionResult,
    ResultQuality,
)


def load_dataframe(source_id: str, sheet: Optional[str] = None) -> pd.DataFrame:
    """
    Load data rows for a dataset source from Supabase and parse into a flat pandas DataFrame.
    Injects '_sheet' column representing the source sheet name.
    
    Args:
        source_id: Unique identifier for the data source
        sheet: Optional target sheet name (case-insensitive)
        
    Returns:
        pd.DataFrame containing flat records, or an empty DataFrame if no data found.
    """
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
        return pd.DataFrame()

    records = []
    for r in rows:
        r_data = r[1]
        if isinstance(r_data, str):
            r_data = json.loads(r_data)
        row_dict = dict(r_data)
        # _sheet is now stored inside row_data by the ingestion pipeline.
        # Fall back to the DB sheet_name column for legacy rows.
        if "_sheet" not in row_dict:
            row_dict["_sheet"] = r[0]
        records.append(row_dict)

    return pd.DataFrame(records)


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
            else:
                continue

        if isinstance(val, (int, float)):
            df[col] = pd.to_numeric(df[col], errors='coerce')
        elif "date" in col.lower() or "tanggal" in col.lower():
            df[col] = pd.to_datetime(df[col], errors='coerce')
            val = pd.to_datetime(val, errors='coerce')

        # Operator translation to pandas query operations
        if op == FilterOperator.EQ or op.value == "==":
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
    
    Args:
        df: Filtered pandas DataFrame
        agg: Optional AggregationSpec
        group_by: Optional list of columns to group by
        
    Returns:
        Any scalar result, pd.DataFrame of grouped values, or the DataFrame itself if no aggregation.
    """
    if agg is None or not agg.func or agg.func == "null":
        return df

    # Resolve group_by columns case-insensitively
    clean_group_by = []
    if group_by:
        for g in group_by:
            g_col = next((c for c in df.columns if c.strip().lower() == g.strip().lower()), g)
            clean_group_by.append(g_col)

    # Resolve aggregation column case-insensitively if specified
    agg_col = agg.column
    if agg_col:
        matched_col = next((c for c in df.columns if c.strip().lower() == agg_col.strip().lower()), None)
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
            data = data.sort_values(by=sort_col, ascending=ascending)

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
