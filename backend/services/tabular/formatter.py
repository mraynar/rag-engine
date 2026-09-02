"""
Formatter module for rendering query results into natural-language responses.
Part of the Phase 2H implementation (TDD Green Phase).
"""
import math
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd

from backend.services.tabular.domain_models import (
    QueryAST,
    QueryPlan,
    QueryType,
    UserIntent,
    ExecutionResult,
    ResultQuality,
    ResolvedEntities,
)


def get_metric_label(col: str) -> str:
    """Resolve physical column name to readable metric name."""
    return "market share" if col == "%" else col


def format_data_compact(query_result: list[dict], max_rows: int = 25) -> str:
    """Convert list of dicts to compact CSV string representation (80% token savings)."""
    if not query_result:
        return "Tidak ada data"
    
    headers = list(query_result[0].keys())
    lines = [",".join(headers)]
    
    for row in query_result[:max_rows]:
        vals = [str(row.get(h, '')).replace(',', ';') for h in headers]
        lines.append(",".join(vals))
        
    if len(query_result) > max_rows:
        lines.append(f"... (dan {len(query_result) - max_rows} baris data lainnya dipotong)")
        
    return "\n".join(lines)


def format_number(val: Any) -> str:
    """
    Format numeric values to Indonesian standard representation (dot for thousands, comma for decimals).
    
    Args:
        val: Any value (int, float, or string)
        
    Returns:
        Formatted string representation of the value
    """
    if isinstance(val, (int, float, np.integer, np.floating)):
        if pd.isna(val) or (isinstance(val, float) and math.isnan(val)):
            return "kosong"
        val_float = float(val)
        is_negative = val_float < 0
        val_abs = abs(val_float)
        
        if val_abs.is_integer():
            formatted = f"{int(val_abs):,}".replace(",", ".")
        else:
            val_rounded = round(val_abs, 2)
            if val_rounded.is_integer():
                formatted = f"{int(val_rounded):,}".replace(",", ".")
            else:
                parts = f"{val_rounded:.2f}".split(".")
                integer_part = f"{int(parts[0]):,}".replace(",", ".")
                dec = parts[1]
                if dec.endswith("0"):
                    dec = dec[:-1]
                formatted = f"{integer_part},{dec}"
        
        return f"-{formatted}" if is_negative else formatted
    return str(val)


def is_monetary_metric(metric_name: str) -> bool:
    """Check if metric refers to money, revenue, nominal, or discount."""
    if not metric_name:
        return False
    m = str(metric_name).upper()
    return any(k in m for k in ["REVENUE", "NOMINAL", "KERINGANAN", "PENDAPATAN", "RUPIAH", "IDR", "DISCOUNT"])


def format_currency(val: Any) -> str:
    """
    Format numeric monetary values into Indonesian Rupiah (Rp) with standard Indonesian number formatting and human readable scale.
    Example: 15250000000 -> "Rp 15.250.000.000 (15,25 Miliar)"
    """
    if isinstance(val, (int, float, np.integer, np.floating)):
        if pd.isna(val) or (isinstance(val, float) and math.isnan(val)):
            return "Rp 0"
        val_float = float(val)
        if val_float == 0:
            return "Rp 0"
        
        is_neg = val_float < 0
        val_abs = abs(val_float)
        prefix = "Rp " if not is_neg else "-Rp "
        
        num_full = format_number(val_abs)
        if val_abs >= 1_000_000_000_000:
            num_short = format_number(val_abs / 1_000_000_000_000)
            return f"{prefix}{num_full} ({num_short} Triliun)"
        elif val_abs >= 1_000_000_000:
            num_short = format_number(val_abs / 1_000_000_000)
            return f"{prefix}{num_full} ({num_short} Miliar)"
        elif val_abs >= 1_000_000:
            num_short = format_number(val_abs / 1_000_000)
            return f"{prefix}{num_full} ({num_short} Juta)"
        else:
            return f"{prefix}{num_full}"
    return str(val)


def format_value_with_metric(val: Any, metric_name: str, is_percentage: bool = False) -> str:
    """Format numeric values according to metric context (Currency, Percentage, or Number)."""
    if is_percentage:
        return f"{format_number(val)}%"
    if is_monetary_metric(metric_name):
        return format_currency(val)
    return format_number(val)


EMPTY_SUGGESTION_RESPONSE = (
    "Data yang Anda cari tidak ditemukan pada database untuk periode/kriteria tersebut.\n\n"
    "Saran:\n"
    "• Periksa kembali penulisan nama operator/layanan.\n"
    "• Perjelas atau perlebar rentang tahun/bulan yang dianalisis."
)


def format_response(
    question: str,
    results: Dict[int, ExecutionResult],
    ast: QueryAST,
    resolved: ResolvedEntities,
    dataset: str,
    original_plan: QueryPlan,
) -> str:
    """
    Generate natural-language response based on query execution results and semantic context.
    """
    if not results:
        return EMPTY_SUGGESTION_RESPONSE

    if original_plan and original_plan.aggregation and original_plan.aggregation.column:
        raw_metric = original_plan.aggregation.column
    else:
        filtered_metrics = [m for m in (resolved.metrics or []) if m.upper().strip() not in ["BULAN", "MONTH", "YEAR", "TAHUN", "_MONTH_CODE", "_YEAR"]]
        raw_metric = filtered_metrics[0] if filtered_metrics else (resolved.metrics[0] if resolved.metrics else "nilai")

    metric_label = get_metric_label(raw_metric).lower()
    year = resolved.month.year if resolved.month else None
    year_str = f"pada tahun {year}" if year else ""

    # 1. Quality-based early exit handlers (prioritizing worst-quality signal first)
    qualities = [r.quality for r in results.values()]
    if ResultQuality.EMPTY in qualities:
        return EMPTY_SUGGESTION_RESPONSE
    if ResultQuality.NAN in qualities:
        return "Data tersedia, tetapi nilai yang diminta tidak dapat dihitung."
    if ResultQuality.ALL_ZERO in qualities:
        r_first = list(results.values())[0]
        if r_first.row_count == 0:
            if year:
                return f"Data {metric_label} pada tahun {year} tidak tersedia pada dataset '{dataset}'."
            return "Data tidak ditemukan untuk kriteria pencarian tersebut."
        if ast.query_type not in [QueryType.RANKING, QueryType.TREND, QueryType.COMPARISON] \
           and ast.intent not in [UserIntent.TOP_N, UserIntent.BOTTOM_N, UserIntent.COMPARISON, UserIntent.TREND_ANALYSIS]:
            return "Berdasarkan data yang ditemukan, nilainya adalah 0."

    # 2. Extract common context elements
    operator = resolved.operators[0] if resolved.operators else None

    # Handle Percentage lookup intent suffix
    is_percentage = False
    if original_plan and original_plan.aggregation and original_plan.aggregation.column:
        is_percentage = original_plan.aggregation.column == "%"
    elif resolved.metrics:
        is_percentage = "%" in resolved.metrics
    else:
        is_percentage = ast.intent == UserIntent.PERCENTAGE_LOOKUP or "%" in question or "market share" in question.lower()

    # 3. Multi-Hop / Chained results formatting
    if len(results) > 1:
        if 1 in results and 2 in results and isinstance(results[2].data, pd.DataFrame):
            annual_total = results[1].data
            monthly_data = results[2].data
            numeric_columns = monthly_data.select_dtypes(include=[np.number]).columns
            value_column = next((column for column in numeric_columns if column.upper() not in ["YEAR", "MONTH", "MONTH_CODE"]), None)
            if value_column and isinstance(annual_total, (int, float, np.integer, np.floating)):
                monthly_total = pd.to_numeric(monthly_data[value_column], errors="coerce").sum()
                difference = float(annual_total) - float(monthly_total)
                fmt_ann = format_value_with_metric(annual_total, raw_metric, is_percentage)
                fmt_mth = format_value_with_metric(monthly_total, raw_metric, is_percentage)
                fmt_diff = format_value_with_metric(abs(difference), raw_metric, is_percentage)
                return (
                    f"Total tahunan {metric_label} adalah {fmt_ann}, "
                    f"sedangkan penjumlahan data bulanan adalah {fmt_mth}. "
                    f"Selisihnya {fmt_diff}; selisih ini muncul karena cakupan atau pengelompokan baris tahunan dan bulanan berbeda."
                )

        # Check if difference calculation requested
        if any(w in question.lower() for w in ["selisih", "beda", "perbedaan", "difference"]):
            if 1 in results and 2 in results:
                val1 = results[1].data
                val2 = results[2].data
                if isinstance(val1, (int, float, np.integer, np.floating)) and isinstance(val2, (int, float, np.integer, np.floating)):
                    diff = abs(val2 - val1)
                    formatted_diff = format_value_with_metric(diff, raw_metric, is_percentage)
                    return f"Selisih {metric_label} adalah {formatted_diff}."

        # Check if percentage contribution requested
        if any(w in question.lower() for w in ["persentase", "kontribusi", "percentage", "contribution"]):
            if 1 in results and 2 in results:
                val1 = results[1].data
                val2 = results[2].data
                if isinstance(val1, (int, float, np.integer, np.floating)) and isinstance(val2, (int, float, np.integer, np.floating)):
                    if val2 != 0:
                        pct = (val1 / val2) * 100
                        formatted_pct = format_number(pct)
                        sheet_word = "internasional" if any(w in question.lower() for w in ["internasional", "international"]) else "domestik"
                        return f"Persentase kontribusi {metric_label} {sheet_word} adalah {formatted_pct}%."

        # Fallback for multi-hop: present step results sequentially
        output_parts = []
        for step, res in sorted(results.items()):
            output_parts.append(f"Langkah {step}: {format_value_with_metric(res.data, raw_metric, is_percentage)}")
        return " | ".join(output_parts)

    # 4. Single execution result formatting
    exec_result = results[1]
    data = exec_result.data

    # Formatting pandas.Series result
    if isinstance(data, pd.Series):
        lines = []
        for idx, val in data.items():
            lines.append(f"{idx}: {format_value_with_metric(val, raw_metric, is_percentage)}")
        return "\n".join(lines)

    # Formatting pandas.DataFrame result
    if isinstance(data, pd.DataFrame):
        if data.empty:
            return "Data tidak ditemukan untuk kriteria pencarian tersebut."

        # Formatting text column / company entity listing
        text_cols = [c for c in data.columns if c.upper() in ["NAMA PERUSAHAAN", "OPERATOR", "VESSEL OPERATOR", "CUSTOMER", "_OPERATOR", "NAMA PELANGGAN"]]
        if text_cols:
            is_pure_text_query = not any(
                c.upper() in ["TEUS", "BOXES", "TOTAL BOX", "TOTAL TEUS", "TOTAL ALL REVENUE", "VESSEL REVENUE", "NOMINAL PERSETUJUAN KERINGANAN"]
                for c in data.columns
            ) or ast.query_type == QueryType.SIMPLE
            if is_pure_text_query:
                col_name = text_cols[0]
                items = [str(x).strip() for x in data[col_name].dropna().unique() if str(x).strip()]
                if items:
                    formatted_items = "\n".join([f"{i+1}. **{item}**" for i, item in enumerate(items)])
                    status_str = ""
                    if original_plan and original_plan.filters:
                        status_filter = next((f for f in original_plan.filters if f.column.upper() == "STATUS"), None)
                        if status_filter:
                            status_str = f" yang memiliki status **{status_filter.value}**"
                    return f"Berdasarkan data {dataset}, berikut adalah {col_name.lower()}{status_str}:\n\n{formatted_items}"

        if ast.query_type == QueryType.SIMPLE or ast.intent in [UserIntent.VALUE_LOOKUP, UserIntent.PERCENTAGE_LOOKUP]:
            metric_cols = [c for c in data.columns if resolved.metrics and any(m.lower() == c.lower() for m in resolved.metrics)]
            if metric_cols:
                metric_col = metric_cols[0]
                series_numeric = pd.to_numeric(data[metric_col], errors='coerce')
                if len(data) == 1:
                    val = series_numeric.iloc[0]
                    if pd.isna(val):
                        val = data[metric_col].iloc[0]
                else:
                    if metric_col.upper() in ["TEUS", "BOXES", "20'", "40'", "ACTUAL", "BUDGET"]:
                        val = series_numeric.sum()
                    else:
                        val = series_numeric.mean()

                formatted_val = format_value_with_metric(val, metric_col, is_percentage)
                op_str = f" {operator}" if operator else ""
                month_str = resolved.month.month_str if resolved.month and resolved.month.month_str else ""
                if month_str and year:
                    period_str = f" pada bulan {month_str} {year}"
                elif year:
                    period_str = f" pada tahun {year}"
                else:
                    period_str = ""
                metric_name = get_metric_label(resolved.metrics[0]) if resolved.metrics else "nilai"
                return f"{metric_name}{op_str}{period_str} adalah {formatted_val}."

        # Trend analysis formatting
        if ast.query_type == QueryType.TREND or ast.intent == UserIntent.TREND_ANALYSIS:
            temporal_col = next((c for c in data.columns if c.upper() in ["MONTH", "YEAR", "MONTH_CODE", "BULAN"]), None)
            val_cols = [c for c in data.columns if c != temporal_col]
            val_col = val_cols[0] if val_cols else None

            if temporal_col and val_col:
                lines = []
                for _, row in data.iterrows():
                    temp_val = row[temporal_col]
                    if temporal_col.upper() == "YEAR":
                        if isinstance(temp_val, (int, float, np.integer, np.floating)):
                            temp_str = str(int(float(temp_val)))
                        else:
                            temp_str = str(temp_val)
                    else:
                        temp_str = format_number(temp_val)
                    val_str = format_value_with_metric(row[val_col], str(val_col), is_percentage)
                    lines.append(f"- {temp_str}: {val_str}")
                return "\n".join(lines)

        # Ranking formatting (TOP_N / BOTTOM_N)
        if ast.query_type == QueryType.RANKING or ast.intent in [UserIntent.TOP_N, UserIntent.BOTTOM_N]:
            group_cols = [c for c in data.columns if c.upper() in ["LOP", "OPERATOR", "VESSEL OPERATOR", "MONTH", "YEAR", "BULAN"]]
            group_col = group_cols[0] if group_cols else data.columns[0]
            val_cols = [c for c in data.columns if c != group_col]
            val_col = val_cols[0] if val_cols else data.columns[1] if len(data.columns) > 1 else group_col

            rank_word = "terendah" if ast.intent == UserIntent.BOTTOM_N or (original_plan.sort == "asc") else "tertinggi"
            lines = []
            for rank, (_, row) in enumerate(data.iterrows(), start=1):
                formatted_val = format_value_with_metric(row[val_col], str(val_col), is_percentage)
                lines.append(f"{rank}. {format_number(row[group_col])}: {formatted_val}")
            group_label = "Customer" if "customer" in question.lower() else group_col
            return f"{len(lines)} besar {group_label} berdasarkan {metric_label} ({rank_word}):\n" + "\n".join(lines)

        if ast.query_type == QueryType.COMPARISON or ast.intent == UserIntent.COMPARISON or (ast.query_type == QueryType.MULTI_HOP and len(results) == 1):
            group_cols = [c for c in data.columns if c.upper() in ["LOP", "OPERATOR", "VESSEL OPERATOR", "MONTH", "YEAR", "BULAN", "_SHEET"]]
            group_col = group_cols[0] if group_cols else data.columns[0]
            val_cols = [c for c in data.columns if c != group_col]
            val_col = val_cols[0] if val_cols else data.columns[1] if len(data.columns) > 1 else group_col

            lines = []
            for _, row in data.iterrows():
                group_val = row[group_col]
                if group_col.upper() in ["YEAR", "TANGGAL", "DATE"] and isinstance(group_val, (int, float, np.integer, np.floating)):
                    formatted_group = str(int(float(group_val)))
                else:
                    formatted_group = str(group_val)
                val_str = format_number(row[val_col])
                if is_percentage:
                    val_str = f"{val_str}%"
                lines.append(f"{formatted_group}: {val_str}")
            return "\n".join(lines)

        # General DataFrame fallback - format as markdown table instead of raw string to prevent raw data dump
        if data.empty:
            return "Data tidak ditemukan."
        
        headers = list(data.columns)
        lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for _, row in data.head(15).iterrows():
            lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
            
        rows_str = "\n".join(lines)
        more_rows = len(data) - 15
        suffix = f"\n\n*(dan {more_rows} baris data lainnya)*" if more_rows > 0 else ""
        return f"Berikut adalah data yang relevan:\n\n{rows_str}{suffix}"

    # Scalar formatting (single lookup or aggregation)
    formatted_val = format_value_with_metric(data, raw_metric, is_percentage)

    if ast.query_type == QueryType.AGGREGATION:
        agg_word = "total"
        if original_plan.aggregation:
            func = original_plan.aggregation.func.lower()
            if func == "mean":
                agg_word = "rata-rata"
            elif func == "max":
                agg_word = "tertinggi"
            elif func == "min":
                agg_word = "terendah"
            elif func == "count":
                agg_word = "jumlah"
        
        op_str = f" untuk {operator}" if operator else ""
        month_str = resolved.month.month_str if resolved.month and resolved.month.month_str else ""
        if month_str and year:
            period_str = f" pada bulan {month_str} {year}"
        elif month_str:
            period_str = f" pada bulan {month_str}"
        elif year:
            period_str = f" pada tahun {year}"
        else:
            period_str = ""

        metric_name = get_metric_label(raw_metric)
        return f"{agg_word.capitalize()} {metric_name}{op_str}{period_str} adalah {formatted_val}."

    # Simple lookup default
    op_str = f" {operator}" if operator else ""
    month_str = resolved.month.month_str if resolved.month and resolved.month.month_str else ""
    if month_str and year:
        period_str = f" pada bulan {month_str} {year}"
    elif month_str:
        period_str = f" pada bulan {month_str}"
    elif year:
        period_str = f" pada tahun {year}"
    else:
        period_str = ""

    metric_name = get_metric_label(raw_metric)
    return f"{metric_name}{op_str}{period_str} adalah {formatted_val}."
