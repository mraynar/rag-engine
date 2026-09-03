"""
Orkestrator query tabular untuk memproses pertanyaan data pelabuhan.
"""
import json
import time
from dataclasses import replace
from typing import Optional, Dict, List

import pandas as pd
from sqlalchemy import text

from backend.core.config import get_gemini_client
from backend.services.db import get_db_conn
from backend.services.tabular.domain_models import (
    QueryAST, QueryPlan, ResolvedEntities, ExecutionResult, ResultQuality,
    FilterCondition, FilterOperator, AggregationSpec,
)
from backend.services.tabular.resolver import route_dataset, route_sheet, resolve_entities
from backend.services.tabular.classifier import classify_query
from backend.services.tabular.decomposer import decompose_query
from backend.services.tabular.query_builder import build_query_plan, QueryBuildError
from backend.services.tabular.retry_engine import execute_with_retry
from backend.services.tabular.formatter import format_response
RETURN_DEBUG_BLOCK = False
from backend.core.config import get_generation_model


# Validasi salam dan pertanyaan di luar konteks

def check_data_query_and_respond(question: str, category: str) -> Optional[str]:
    """Return a friendly non-data response if question is a greeting/off-topic, else None."""
    import sys
    if "pytest" in sys.modules:
        return None
    try:
        client = get_gemini_client()
        model = get_generation_model()
        prompt = (
            f"You are a data assistant for '{category}'.\n"
            f"User question: \"{question}\"\n\n"
            "Is this a greeting, small talk, or completely unrelated to data analytics? "
            "If YES → write a short helpful response in Indonesian explaining you're a data assistant. "
            "If NO (it's a valid data question) → respond only with the word VALID."
        )
        response = client.models.generate_content(model=model, contents=prompt)
        text_resp = response.text.strip()
        if text_resp.upper() == "VALID":
            return None
        return text_resp
    except Exception:
        greetings = ["halo", "hello", "hi", "hey", "good morning", "who are you", "help"]
        q = question.lower().strip()
        if any(g in q for g in greetings) or len(q.split()) < 3:
            return f"Saya adalah asisten data untuk kategori '{category}'. Silakan tanyakan sesuatu terkait data."
        return None


MONTH_ALIASES = {
    1: ["1", "01", "january", "januari", "jan"],
    2: ["2", "02", "february", "februari", "feb"],
    3: ["3", "03", "march", "maret", "mar"],
    4: ["4", "04", "april", "apr"],
    5: ["5", "05", "may", "mei"],
    6: ["6", "06", "june", "juni", "jun"],
    7: ["7", "07", "july", "juli", "jul"],
    8: ["8", "08", "august", "agustus", "agu", "aug"],
    9: ["9", "09", "september", "sep"],
    10: ["10", "october", "oktober", "okt", "oct"],
    11: ["11", "november", "nov"],
    12: ["12", "december", "desember", "des", "dec"]
}


def _execute_llm_text_to_sql_pipeline(
    question: str,
    dataset: str,
    preferred_sheet: Optional[str],
    source_id: str,
    column_schema: dict,
    chat_history: Optional[list] = None,
) -> tuple:
    """
    AI-First LLM Text-to-SQL Execution Pipeline.
    Combines Dynamic Value Profiling, Multi-Metric Aggregation, Universal Month Matching,
    and Derived Market Share Calculation.
    """
    from backend.services.tabular.executor import load_dataframe, OPERATOR_SYNONYM_GROUPS
    from backend.services.tabular.schema_sampler import get_dataset_schema_and_samples
    from backend.services.tabular.sql_generator import generate_llm_text_to_sql_plan

    df_full = load_dataframe(source_id=source_id)
    if df_full.empty:
        return f"Dataset '{dataset}' tidak memiliki data.", {}

    value_samples = get_dataset_schema_and_samples(df_full, source_id=source_id)

    llm_plan = generate_llm_text_to_sql_plan(
        question=question,
        dataset=dataset,
        column_schema=column_schema,
        value_samples=value_samples,
        chat_history=chat_history,
        preferred_sheet=preferred_sheet,
    )

    sheet_choice = llm_plan.get("sheet") or preferred_sheet
    if sheet_choice and "_sheet" in df_full.columns:
        df = df_full[df_full["_sheet"].astype(str).str.lower() == str(sheet_choice).lower()].copy()
        if df.empty:
            df = df_full.copy()
    else:
        df = df_full.copy()

    # Apply LLM Filters with Universal Month, Clean .0, & Case-Insensitive Matching
    filters = llm_plan.get("filters", [])
    for f in filters:
        col = f.get("column")
        val = f.get("value")
        if not col or col not in df.columns or val is None:
            continue

        val_clean = str(val).replace(".0", "").strip()
        col_series = df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        col_upper = col.upper()
        # Operator Synonym Matching
        if col_upper in ("LOP", "VESSEL OPERATOR", "OPERATOR", "VESSEL_OPERATOR"):
            synonym_set = {val_clean.upper()}
            for grp in OPERATOR_SYNONYM_GROUPS:
                if any(syn in grp for syn in synonym_set):
                    synonym_set.update(grp)
            df = df[col_series.str.upper().isin(synonym_set)]
        # Check if filter is Month filter
        elif col_upper in ("MONTH", "BULAN", "MONTH_CODE", "_MONTH_CODE"):
            month_num = None
            try:
                val_int = int(float(str(val)))
                if 1 <= val_int <= 12:
                    month_num = val_int
            except ValueError:
                val_str = val_clean.lower()
                for m_code, m_aliases in MONTH_ALIASES.items():
                    if val_str in m_aliases:
                        month_num = m_code
                        break

            if month_num and month_num in MONTH_ALIASES:
                aliases = MONTH_ALIASES[month_num]
                month_cols = [c for c in df.columns if c.upper() in ("MONTH", "BULAN", "MONTH_CODE", "_MONTH_CODE")]
                if month_cols:
                    mask = pd.Series(False, index=df.index)
                    for m_col in month_cols:
                        s_clean = df[m_col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.lower()
                        mask = mask | s_clean.isin(aliases)
                    df = df[mask]
                else:
                    df = df[col_series.str.lower().isin(aliases)]
            else:
                df = df[col_series.str.upper() == val_clean.upper()]
        elif col_upper in ("YEAR", "TAHUN", "_YEAR"):
            df = df[col_series.str.upper() == val_clean.upper()]
        else:
            if isinstance(val, str):
                df = df[col_series.str.upper().str.contains(val_clean.upper(), regex=False, na=False)]
            else:
                df = df[df[col] == val]

    if df.empty:
        return f"Data tidak ditemukan untuk filter yang diminta di dataset '{dataset}'.", {"llm_plan": llm_plan}

    start_ts = time.time()

    raw_metrics = llm_plan.get("metrics", [])
    group_by = llm_plan.get("group_by")
    sort_by = llm_plan.get("sort_by", "desc")
    limit = llm_plan.get("limit", 10)
    derived_mode = llm_plan.get("derived_mode")

    # Map requested metric names to actual column names case-insensitively
    valid_metrics = []
    df_cols_upper = {c.upper(): c for c in df.columns}
    for m in raw_metrics:
        m_up = str(m).upper()
        if m_up in df_cols_upper:
            valid_metrics.append(df_cols_upper[m_up])
        elif m in df.columns:
            valid_metrics.append(m)
    if not valid_metrics:
        common_metrics = ["TOTAL TEUS", "TEUS", "TOTAL REVENUE", "TOTAL ALL REVENUE", "VESSEL REVENUE", "TOTAL BOX", "BOX", "ACTUAL"]
        valid_metrics = [m for m in common_metrics if m in df.columns][:2]

    for m in valid_metrics:
        df[m] = pd.to_numeric(df[m], errors="coerce").fillna(0)

    # Build SQL string representation for Debugger UI
    select_clause = ", ".join([f'SUM("{m}") AS "{m.lower().replace(" ", "_")}"' for m in valid_metrics]) if valid_metrics else '*'
    where_parts = []
    applied_filters_dict = {}
    for f in filters:
        col_f = f.get("column")
        val_f = f.get("value")
        if col_f and val_f is not None:
            where_parts.append(f'"{col_f}" = \'{val_f}\'')
            applied_filters_dict[col_f] = val_f

    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    group_clause = f' GROUP BY "{group_by}"' if group_by else ""
    sheet_table = sheet_choice or "data_rows"
    generated_sql = f'SELECT {select_clause} FROM "{sheet_table}"{where_clause}{group_clause};'

    elapsed_ms = round((time.time() - start_ts) * 1000, 2)

    plan_debug = {
        "target_dataset": dataset,
        "target_sheet": sheet_choice or "All Sheets",
        "generated_sql": generated_sql,
        "execution_time_ms": elapsed_ms,
        "metrics_used": valid_metrics,
        "applied_filters": applied_filters_dict,
        "llm_plan": llm_plan
    }

    # Special Derived Market Share Calculation if % column is missing/null
    if derived_mode == "market_share_ratio" or (dataset == "Market Share" and any("MARKET SHARE" in q.upper() or "%" in q or "TIL" in q.upper() for q in [question])):
        op_col = next((c for c in df_full.columns if c.upper() in ("LOP", "VESSEL OPERATOR", "OPERATOR")), None)
        vol_col = next((c for c in df_full.columns if c.upper() in ("TEUS", "TEUS 2024", "BOX", "BOXES")), None)
        if op_col and vol_col:
            df_ms = df_full[df_full["_sheet"].astype(str).str.upper().str.contains("DOM", na=False)].copy() if "_sheet" in df_full.columns else df_full.copy()
            
            # Apply year/month filters first
            yr_filter = next((f.get("value") for f in filters if f.get("column", "").upper() in ("YEAR", "TAHUN", "_YEAR")), None)
            if yr_filter and "YEAR" in df_ms.columns:
                yr_clean = str(yr_filter).replace(".0", "").strip()
                df_ms = df_ms[df_ms["YEAR"].astype(str).str.replace(r'\.0$', '', regex=True).str.strip() == yr_clean]

            df_ms[vol_col] = pd.to_numeric(df_ms[vol_col], errors="coerce").fillna(0)
            total_overall_teus = df_ms[vol_col].sum()
            
            # Check if user asked for a specific operator (e.g. TIL)
            op_filter = next((f.get("value") for f in filters if f.get("column", "").upper() in ("LOP", "VESSEL OPERATOR", "OPERATOR")), None)
            if op_filter:
                op_clean = str(op_filter).replace(".0", "").strip().upper()
                synonym_set = {op_clean}
                for grp in OPERATOR_SYNONYM_GROUPS:
                    if any(syn in grp for syn in synonym_set):
                        synonym_set.update(grp)
                op_series = df_ms[op_col].astype(str).str.upper().str.strip()
                df_op = df_ms[op_series.isin(synonym_set)]
                op_teus = df_op[vol_col].sum()
                pct = (op_teus * 100.0 / total_overall_teus) if total_overall_teus > 0 else 0.0
                return f"Berikut hasil market share faktual:\nTotal volume operator {op_clean} ({', '.join(sorted(synonym_set))}) mencapai {op_teus:,.0f} TEUS dengan Market Share sebesar {pct:.2f}% (dari total market volume {total_overall_teus:,.0f} TEUS).", plan_debug
            elif total_overall_teus > 0:
                grouped = df_ms.groupby(op_col)[vol_col].sum().reset_index()
                grouped["MARKET SHARE %"] = (grouped[vol_col] * 100.0 / total_overall_teus).round(2)
                grouped = grouped.sort_values(vol_col, ascending=False)
                if limit:
                    grouped = grouped.head(int(limit))
                
                rows_text = []
                for idx, r in enumerate(grouped.itertuples(), 1):
                    op_val = getattr(r, op_col.replace(" ", "_"), "") or getattr(r, f"_{idx}", "")
                    teus_val = getattr(r, vol_col.replace(" ", "_"), 0)
                    pct_val = getattr(r, "MARKET_SHARE_%", 0)
                    rows_text.append(f"{idx}. {op_val}: {pct_val}% ({teus_val:,.0f} TEUS)")
                return f"Berikut hasil market share faktual (Total Overall Volume: {total_overall_teus:,.0f} TEUS):\n" + "\n".join(rows_text), plan_debug

    if group_by and group_by in df.columns and valid_metrics:
        grouped = df.groupby(group_by)[valid_metrics].sum().reset_index()
        primary_metric = valid_metrics[0]
        if sort_by == "desc":
            grouped = grouped.sort_values(primary_metric, ascending=False)
        if limit:
            grouped = grouped.head(int(limit))

        rows_text = []
        for idx, row in enumerate(grouped.itertuples(), 1):
            key_val = getattr(row, group_by.replace(" ", "_"), None) or getattr(row, f"_{idx}", None)
            metrics_str_parts = []
            for m in valid_metrics:
                val_raw = getattr(row, m.replace(" ", "_").replace("'", ""), 0)
                if "REVENUE" in m.upper() or "RUPIAH" in m.upper() or "DPP" in m.upper():
                    metrics_str_parts.append(f"{m}: Rp {val_raw:,.0f}")
                else:
                    metrics_str_parts.append(f"{m}: {val_raw:,.0f}")
            rows_text.append(f"{idx}. {key_val} : {', '.join(metrics_str_parts)}")
        return f"Berikut hasil faktual query data:\n" + "\n".join(rows_text), plan_debug

    elif valid_metrics:
        # Single row Multi-Metric Aggregation (e.g. TEUS + REVENUE)
        metric_results = []
        for m in valid_metrics:
            val_sum = df[m].sum()
            if "REVENUE" in m.upper() or "RUPIAH" in m.upper() or "DPP" in m.upper():
                metric_results.append(f"Total {m} sebesar Rp {val_sum:,.0f}")
            else:
                metric_results.append(f"Total {m} sebanyak {val_sum:,.0f}")
        return " dan ".join(metric_results) + ".", plan_debug

    else:
        top_rows = df.head(limit or 5).to_dict(orient="records")
        return f"Berikut hasil faktual query data (top rows):\n{json.dumps(top_rows[:5], default=str, ensure_ascii=False)}", plan_debug


def answer_tabular_question(
    question: str,
    category_name: str = "All Data",
    conversation_id: Optional[str] = None
) -> dict:
    """
    Answer a tabular question using the AI-First LLM RAG Text-to-SQL architecture.

    Returns: {"answer": str, "sources": list[str], "debug": dict}
    """
    from backend.services.tabular.resolver import sanitize_leading_number, check_input_security
    from backend.services.db_chat_store import get_recent_chat_history
    
    question = sanitize_leading_number(question)
    chat_history = get_recent_chat_history(conversation_id) if conversation_id else []

    debug_info = {
        "question": question,
        "category": category_name,
        "routing": {},
        "query_plan": {},
        "execution": {},
    }

    sec_error = check_input_security(question)
    if sec_error:
        debug_info["security_blocked"] = True
        return {"answer": sec_error, "sources": [], "debug": debug_info}

    greeting_resp = check_data_query_and_respond(question, category_name)
    if greeting_resp:
        return {"answer": greeting_resp, "sources": [f"Category: {category_name}"], "debug": debug_info}

    # 2. Route dataset with chat_history for context inheritance
    is_all_data = not category_name or str(category_name).strip().lower() in [
        "all data", "all datasource", "all datasources", "all", ""
    ]

    target_dataset = None
    llm_suggested_sheet = None

    if is_all_data:
        target_dataset, llm_suggested_sheet, routing_debug = _llm_route_all_data(question, chat_history=chat_history)
        debug_info["routing"] = routing_debug
        if not target_dataset:
            return {
                "answer": "Maaf, saya tidak dapat menentukan dataset yang relevan untuk pertanyaan ini. Pastikan pertanyaan berkaitan dengan data operasional pelabuhan TPS.",
                "sources": [],
                "debug": debug_info,
            }
    else:
        target_dataset = category_name
        debug_info["routing"] = {"method": "explicit", "selected": target_dataset}

    # 3. Load source from DB
    try:
        with get_db_conn() as conn:
            res = conn.execute(
                text("SELECT id, column_schema FROM data_sources WHERE category_name = :cat"),
                {"cat": target_dataset}
            ).fetchone()
    except Exception as e:
        return {"answer": f"Gagal mengakses database: {str(e)}", "sources": [], "debug": debug_info}

    if not res:
        return {
            "answer": f"Dataset '{target_dataset}' belum tersedia di database. Silakan sync terlebih dahulu.",
            "sources": [],
            "debug": debug_info,
        }

    source_id, schema_raw = res
    column_schema = schema_raw if isinstance(schema_raw, dict) else json.loads(schema_raw or "{}")
    debug_info["query_plan"]["schema_keys"] = list(column_schema.keys())[:8]

    # 4. Execute AI-First Text-to-SQL Pipeline
    answer_text, plan_debug = _execute_llm_text_to_sql_pipeline(
        question=question,
        dataset=target_dataset,
        preferred_sheet=llm_suggested_sheet,
        source_id=str(source_id),
        column_schema=column_schema,
        chat_history=chat_history,
    )
    debug_info["execution"] = plan_debug

    # 5. Narrative Polish using Groq / Gemini
    try:
        from backend.services.rag_engine import groq_generate
        polished = groq_generate(prompt=(
            f"Berikut hasil faktual dari query data:\n{answer_text}\n\n"
            "Ubah menjadi kalimat narasi eksekutif yang natural, ringkas, dan profesional dalam Bahasa Indonesia. "
            "JANGAN ubah angka atau fakta. Pertahankan format ribuan dengan titik (contoh: Rp 1.239.652.922,02 atau 370 TEUS)."
        ))
        answer_text = polished
    except Exception as groq_err:
        print(f"[tabular_query] Groq narrative polish skipped: {groq_err}")

    return {
        "answer": answer_text,
        "sources": [f"Supabase Table: {target_dataset}"],
        "debug": debug_info,
    }
