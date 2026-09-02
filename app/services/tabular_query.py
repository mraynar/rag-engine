"""
Orkestrator query tabular untuk memproses pertanyaan data pelabuhan.
"""
import json
from dataclasses import replace
from typing import Optional, Dict, List

import pandas as pd
from sqlalchemy import text

from app.core.config import get_gemini_client
from app.services.db import get_db_conn
from app.services.tabular.domain_models import (
    QueryAST, QueryPlan, ResolvedEntities, ExecutionResult, ResultQuality,
    FilterCondition, FilterOperator, AggregationSpec,
)
from app.services.tabular.resolver import route_dataset, route_sheet, resolve_entities
from app.services.tabular.classifier import classify_query
from app.services.tabular.decomposer import decompose_query
from app.services.tabular.query_builder import build_query_plan, QueryBuildError
from app.services.tabular.retry_engine import execute_with_retry
from app.services.tabular.formatter import format_response
from app.services.tabular.settings import RETURN_DEBUG_BLOCK
from app.core.config import get_generation_model


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


# Routing dataset berbasis LLM untuk mode All Data
def _llm_route_all_data(question: str) -> tuple:
    """
    Use LLM to pick the best dataset + sheet from all available sources in DB.
    Returns (dataset_name, sheet_name, routing_debug_info).
    """
    from app.services.tabular.llm_router import llm_route_dataset

    # Load all datasets + schemas from DB
    available = []
    db_schemas = {}
    try:
        with get_db_conn() as conn:
            rows = conn.execute(
                text("SELECT category_name, column_schema FROM data_sources WHERE sync_status IN ('synced', 'success')")
            ).fetchall()
            for row in rows:
                cat = row[0]
                schema_raw = row[1]
                available.append(cat)
                db_schemas[cat] = schema_raw if isinstance(schema_raw, dict) else json.loads(schema_raw or "{}")
    except Exception as e:
        print(f"[tabular_query] Failed to load datasets for LLM routing: {e}")
        return None, None, {"error": str(e)}

    if not available:
        return None, None, {"error": "No synced datasets found"}

    result = llm_route_dataset(question, available, db_schemas)
    routing_debug = {
        "method": "llm_semantic",
        "candidates": available,
        "selected": result.get("dataset"),
        "sheet": result.get("sheet"),
        "confidence": result.get("confidence"),
        "reason": result.get("reason"),
    }
    return result.get("dataset"), result.get("sheet"), routing_debug


# Eksekusi query plan berbasis LLM
def _execute_llm_query_plan(
    question: str,
    dataset: str,
    sheet: Optional[str],
    source_id: str,
    column_schema: dict,
) -> tuple:
    """
    Build and execute a query plan via LLM when deterministic path fails.
    Returns (answer_text, debug_dict).
    """
    from app.services.tabular.llm_router import llm_build_query_plan
    from app.services.tabular.executor import load_dataframe, apply_filters

    # Get sample data from DB
    sample_data = []
    try:
        with get_db_conn() as conn:
            sample_rows = conn.execute(
                text("SELECT row_data FROM data_rows WHERE source_id = :sid LIMIT 5"),
                {"sid": source_id}
            ).fetchall()
            for row in sample_rows:
                d = row[0]
                if isinstance(d, dict):
                    sample_data.append(d)
                elif isinstance(d, str):
                    sample_data.append(json.loads(d))
    except Exception as e:
        print(f"[tabular_query] Could not load sample data: {e}")

    llm_plan = llm_build_query_plan(
        question=question,
        dataset=dataset,
        sheet=sheet,
        schema=column_schema,
        sample_data=sample_data,
    )

    plan_debug = {"llm_plan": llm_plan}

    if llm_plan.get("not_found"):
        return (
            f"Maaf, data yang Anda cari tidak ditemukan di dataset '{dataset}'. "
            f"{llm_plan.get('explanation', '')}",
            plan_debug,
        )

    # Execute plan using pandas
    try:
        df = load_dataframe(source_id=source_id, sheet=sheet)
        if df is None or df.empty:
            return f"Tidak ada data yang ditemukan di sheet '{sheet}' dataset '{dataset}'.", plan_debug

        # Apply filters from LLM plan
        filters_raw = llm_plan.get("filters", [])
        for f in filters_raw:
            col = f.get("column", "")
            op = f.get("op", "==")
            val = f.get("value")
            if col not in df.columns:
                continue
            if op == "==" or op == "eq":
                if isinstance(val, str):
                    df = df[df[col].astype(str).str.upper().str.strip() == str(val).upper().strip()]
                else:
                    df = df[df[col] == val]
            elif op == ">" :
                df = df[pd.to_numeric(df[col], errors="coerce") > val]
            elif op == "<":
                df = df[pd.to_numeric(df[col], errors="coerce") < val]
            elif op == ">=":
                df = df[pd.to_numeric(df[col], errors="coerce") >= val]
            elif op == "<=":
                df = df[pd.to_numeric(df[col], errors="coerce") <= val]

        metric = llm_plan.get("metric")
        agg = llm_plan.get("aggregation")
        group_by = llm_plan.get("group_by")
        sort_by = llm_plan.get("sort_by")
        limit = llm_plan.get("limit")
        explanation = llm_plan.get("explanation", "")

        plan_debug["rows_after_filter"] = len(df)

        if df.empty:
            return (
                f"Data tidak ditemukan untuk filter yang diminta di dataset '{dataset}'.\n"
                f"_{explanation}_",
                plan_debug,
            )

        # Aggregate
        if metric and metric in df.columns:
            df[metric] = pd.to_numeric(df[metric], errors="coerce")
            if group_by and group_by in df.columns:
                grouped = df.groupby(group_by)[metric]
                if agg == "sum":
                    result_series = grouped.sum()
                elif agg == "mean":
                    result_series = grouped.mean()
                elif agg == "max":
                    result_series = grouped.max()
                elif agg == "min":
                    result_series = grouped.min()
                elif agg == "count":
                    result_series = grouped.count()
                else:
                    result_series = grouped.sum()

                result_df = result_series.reset_index()
                result_df.columns = [group_by, metric]
                if sort_by == "desc" or agg in ("sum", "max"):
                    result_df = result_df.sort_values(metric, ascending=False)
                if limit:
                    result_df = result_df.head(int(limit))

                # Format as table
                rows_text = []
                for idx, row in enumerate(result_df.itertuples(), 1):
                    val_raw = getattr(row, metric.replace(" ", "_").replace("'", ""), None) or getattr(row, f"_{idx}", None)
                    try:
                        val_raw = float(str(getattr(row, 2)).replace(",", ""))
                        val_fmt = f"{val_raw:,.0f}"
                    except Exception:
                        val_fmt = str(getattr(row, 2))
                    rows_text.append(f"{idx}. {getattr(row, 1)} : {val_fmt}")
                answer_text = f"Berikut hasil faktual query data:\n" + "\n".join(rows_text)
                return answer_text, plan_debug
            else:
                # Single value aggregation
                if agg == "sum":
                    val = df[metric].sum()
                elif agg == "mean":
                    val = df[metric].mean()
                elif agg == "max":
                    val = df[metric].max()
                elif agg == "min":
                    val = df[metric].min()
                elif agg == "count":
                    val = df[metric].count()
                else:
                    val = df[metric].sum()
                try:
                    val_fmt = f"{float(val):,.0f}"
                except Exception:
                    val_fmt = str(val)
                return f"Berikut hasil faktual query data: {metric} = {val_fmt}", plan_debug

        elif agg == "count":
            return f"Berikut hasil faktual query data: jumlah baris = {len(df):,}", plan_debug
        else:
            # No metric/agg — return top rows
            top = df.head(limit or 5).to_dict(orient="records")
            return f"Berikut hasil faktual query data (top rows):\n{json.dumps(top[:5], default=str, ensure_ascii=False)}", plan_debug

    except Exception as e:
        print(f"[tabular_query] LLM plan execution failed: {e}")
        return f"Gagal mengeksekusi query plan: {str(e)}", plan_debug


# query tabular
def answer_tabular_question(question: str, category: str = "All Data") -> dict:
    """
    Answer a tabular question using the RAG-first pipeline.

    Returns: {"answer": str, "sources": list[str], "debug": dict}
    The 'debug' field contains routing + query plan info for the collapsible UI.
    """
    from app.services.tabular.resolver import sanitize_leading_number
    question = sanitize_leading_number(question)

    debug_info = {
        "question": question,
        "category": category_name,
        "routing": {},
        "query_plan": {},
        "execution": {},
    }

    # 1. Guard
    greeting_resp = check_data_query_and_respond(question, category_name)
    if greeting_resp:
        return {"answer": greeting_resp, "sources": [f"Category: {category_name}"], "debug": debug_info}

    # 2. Route dataset
    is_all_data = not category_name or str(category_name).strip().lower() in [
        "all data", "all datasource", "all datasources", "all", ""
    ]

    target_dataset = None
    llm_suggested_sheet = None

    if is_all_data:
        # LLM semantic routing
        target_dataset, llm_suggested_sheet, routing_debug = _llm_route_all_data(question)
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

    # 4. Resolve entities + route sheet
    try:
        resolved = resolve_entities(question, target_dataset)
        sheets = route_sheet(question, target_dataset)

        # If LLM routing already suggested a sheet, prioritize it
        if llm_suggested_sheet:
            sheets = [llm_suggested_sheet]
        elif not sheets and target_dataset == "Transhipment":
            # Transhipment default: revenue/loading → new vr, else Transhipment sheet
            ql = question.lower()
            if any(kw in ql for kw in ["revenue", "loading", "discharge", "muat", "bongkar"]):
                sheets = ["new vr"]
            else:
                sheets = ["Transhipment"]

        sheet = sheets[0] if sheets and len(sheets) == 1 else None
        debug_info["query_plan"]["sheet"] = sheet
        debug_info["query_plan"]["resolved_operators"] = resolved.operators
        debug_info["query_plan"]["resolved_metrics"] = resolved.metrics
        debug_info["query_plan"]["resolved_month"] = {
            "month_str": resolved.month.month_str if resolved.month else None,
            "month_code": resolved.month.month_code if resolved.month else None,
            "year": resolved.month.year if resolved.month else None,
        }
    except Exception as e:
        return {"answer": f"Gagal menganalisis pertanyaan: {str(e)}", "sources": [f"Supabase Table: {target_dataset}"], "debug": debug_info}

    # 5. Deterministic classify + build plan
    try:
        ast = classify_query(question, resolved, target_dataset)

        # Inject KATEGORI filter for Transhipment when loading/discharge mentioned
        if target_dataset == "Transhipment":
            from dataclasses import replace as dc_replace
            ql = question.lower()
            kat = None
            if "total loading" in ql or " loading" in ql:
                kat = "LOADING"
            elif "discharge" in ql or "bongkar" in ql:
                kat = "DISCHARGE"
            if kat:
                existing = [f.column.upper() for f in ast.filters]
                if "KATEGORI" not in existing:
                    ast = dc_replace(ast, filters=list(ast.filters) + [
                        FilterCondition(column="KATEGORI", operator=FilterOperator.EQ, value=kat)
                    ])

        subqueries = decompose_query(ast, question, resolved, target_dataset)
        debug_info["query_plan"]["query_type"] = ast.query_type.value
        debug_info["query_plan"]["intent"] = ast.intent.value
        debug_info["query_plan"]["filters"] = [
            f"{f.column} {f.operator.value} {f.value}" for f in ast.filters
        ]
        debug_info["query_plan"]["aggregation"] = (
            f"{ast.aggregation.func}({ast.aggregation.column})" if ast.aggregation else None
        )
        debug_info["query_plan"]["build_method"] = ast.build_method.value

    except Exception as e:
        return {"answer": f"Gagal mengklasifikasikan pertanyaan: {str(e)}", "sources": [f"Supabase Table: {target_dataset}"], "debug": debug_info}

    # 6. Execute deterministic plan
    results = {}
    last_plan = None
    steps_debug = {}
    deterministic_failed = False

    for sub_q in subqueries:
        try:
            sub_resolved = resolve_entities(sub_q.question, target_dataset)
            sub_ast = classify_query(sub_q.question, sub_resolved, target_dataset)
            plan = build_query_plan(sub_ast, sub_q.question, resolved, target_dataset, schema=column_schema, subquery=sub_q)

            sub_sheets = route_sheet(sub_q.question, target_dataset)
            sub_sheet = sub_sheets[0] if sub_sheets and len(sub_sheets) == 1 else None
            if not sub_sheet and sheet:
                sub_sheet = sheet
            if sub_sheet and not plan.sheet:
                plan = replace(plan, sheet=sub_sheet)

            last_plan = plan
            exec_res = execute_with_retry(
                source_id=str(source_id), plan=plan, question=sub_q.question,
                resolved=resolved, dataset=target_dataset, db_schema=column_schema
            )
            results[sub_q.step] = exec_res
            steps_debug[sub_q.step] = {"plan": plan, "exec_res": exec_res}

        except QueryBuildError as qbe:
            qbe_str = str(qbe)
            print(f"[tabular_query] Deterministic build error: {qbe_str}")
            if "tidak tersedia" in qbe_str or "bukan" in qbe_str or "tidak valid" in qbe_str:
                # Safe rejection error
                return {
                    "answer": qbe_str,
                    "sources": [f"Supabase Table: {target_dataset}"],
                    "debug": debug_info
                }
            deterministic_failed = True
            debug_info["query_plan"]["deterministic_error"] = qbe_str
            break
        except Exception as e:
            print(f"[tabular_query] Deterministic exec failed: {e} — falling back to LLM")
            deterministic_failed = True
            debug_info["query_plan"]["deterministic_error"] = str(e)
            break

    # 7. LLM fallback if deterministic failed or produced empty/low-quality results
    use_llm_fallback = deterministic_failed
    if not use_llm_fallback and results:
        primary = results.get(1)
        if primary and primary.quality.value in ["empty", "low_quality"]:
            print(f"[tabular_query] Deterministic returned {primary.quality.value} — trying LLM fallback")
            use_llm_fallback = True
            debug_info["query_plan"]["llm_fallback_reason"] = f"deterministic quality: {primary.quality.value}"

    if use_llm_fallback:
        debug_info["query_plan"]["path"] = "llm_fallback"
        llm_answer, llm_debug = _execute_llm_query_plan(
            question=question,
            dataset=target_dataset,
            sheet=sheet,
            source_id=str(source_id),
            column_schema=column_schema,
        )
        debug_info["execution"] = llm_debug

        # Groq narrative polish
        try:
            from app.services.groq_client import groq_generate
            polished = groq_generate(prompt=(
                f"Berikut hasil faktual dari query data:\n{llm_answer}\n\n"
                "Ubah menjadi kalimat natural, ringkas, dan profesional dalam Bahasa Indonesia. "
                "JANGAN ubah angka atau fakta. Jika ada daftar, pertahankan formatnya."
            ))
            llm_answer = polished
        except Exception:
            pass

        if RETURN_DEBUG_BLOCK:
            llm_answer += f"\n\n---\n### Debug Information\n\n**Input**\n- Question: `{question}`\n- Category: `{category_name}`\n\n**Dataset Routing**\n- Dataset: `{target_dataset}`\n\n**Sheet Routing**\n- Resolved: `{sheet}`\n\n**Entities**\n- Year: `{debug_info['query_plan'].get('resolved_month', {}).get('year')}`\n\n**Classification**\n- Path: `llm_fallback`\n"

        return {
            "answer": llm_answer,
            "sources": [f"Supabase Table: {target_dataset}"],
            "debug": debug_info,
        }

    # 8. Format deterministic results
    debug_info["query_plan"]["path"] = "deterministic"
    debug_info["execution"]["steps"] = {
        k: {
            "quality": v["exec_res"].quality.value,
            "row_count": v["exec_res"].row_count,
            "plan_sheet": v["plan"].sheet,
            "plan_agg": f"{v['plan'].aggregation.func}({v['plan'].aggregation.column})" if v["plan"].aggregation else None,
        }
        for k, v in steps_debug.items()
    }

    try:
        answer = format_response(
            question=question, results=results, ast=ast,
            resolved=resolved, dataset=target_dataset, original_plan=last_plan
        )
    except Exception as e:
        answer = f"Gagal merumuskan jawaban: {str(e)}."

    # Groq narrative polish
    raw_answer = answer
    try:
        from app.services.groq_client import groq_generate
        answer = groq_generate(prompt=(
            f"Berikut hasil faktual dari query data:\n{raw_answer}\n\n"
            "Ubah menjadi kalimat natural, ringkas, dan profesional dalam Bahasa Indonesia. "
            "JANGAN ubah angka atau fakta. Jika ada daftar/tabel, pertahankan formatnya."
        ))
    except Exception as groq_err:
        print(f"[tabular_query] Groq polish skipped: {groq_err}")
        answer = raw_answer

    if RETURN_DEBUG_BLOCK:
        debug_lines = [
            "\n",
            "---",
            "### Debug Information",
            "",
            "**Input**",
            f"- Question: `{question}`",
            f"- Category: `{category_name}`",
            "",
            "**Dataset Routing**",
            f"- Dataset: `{target_dataset}`",
            "",
            "**Sheet Routing**",
            f"- Resolved: `{sheet}` | Plan Sheet: `{sheet}`",
            "",
            "**Entities**",
            f"- Year: `{resolved.month.year if resolved.month else 'None'}`",
            "",
            "**Classification**",
            f"- Query Type: `{ast.query_type.value}` | Intent: `{ast.intent.value}` | Build Method: `{ast.build_method.value}`",
            "",
        ]
        for step, step_info in sorted(steps_debug.items()):
            sub_ast = classify_query(question, resolved, target_dataset)
            plan = step_info["plan"]
            exec_res = step_info["exec_res"]
            debug_lines.extend([
                f"**AST — Step {step}**",
                f"**Query Plan — Step {step}**",
                f"**Execution Result — Step {step}**",
                f"- Quality: `{exec_res.quality.value}` | Row Count: `{exec_res.row_count}`",
                f"- Data Type: `DataFrame` | Shape: `({exec_res.row_count}, {len(column_schema.get(sheet or '_all_sheets', []))})`",
                f"- Columns: `{list(column_schema.get(sheet or '_all_sheets', []))}`",
            ])
        answer += "\n".join(debug_lines)

    return {
        "answer": answer,
        "sources": [f"Supabase Table: {target_dataset}"],
        "debug": debug_info,
    }
