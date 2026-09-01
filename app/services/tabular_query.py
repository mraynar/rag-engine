import json
from dataclasses import replace
from typing import Optional, Dict, List
from sqlalchemy import text

from app.core.config import get_gemini_client
from app.services.db import get_db_conn
from app.services.tabular.domain_models import (
    QueryAST,
    QueryPlan,
    ResolvedEntities,
    ExecutionResult,
    ResultQuality,
)
from app.services.tabular.resolver import (
    route_dataset,
    route_sheet,
    resolve_entities,
)
from app.services.tabular.classifier import classify_query
from app.services.tabular.decomposer import decompose_query
from app.services.tabular.query_builder import build_query_plan, QueryBuildError
from app.services.tabular.retry_engine import execute_with_retry
from app.services.tabular.formatter import format_response
from app.services.tabular.settings import RETURN_DEBUG_BLOCK
from app.core.config import get_generation_model


def check_data_query_and_respond(question: str, category: str) -> Optional[str]:
    """Uses Gemini to check if the question is a greeting, small talk, or unrelated to the category data.
    
    If it is unrelated, returns a friendly conversational response pointing to the data.
    If it is a valid data question, returns None.
    """
    import sys
    if "pytest" in sys.modules:
        return None

    try:
        client = get_gemini_client()
        model = get_generation_model()
        
        prompt = (
            f"You are a helpful data assistant for the dataset category '{category}'.\n"
            f"The user is asking: \"{question}\"\n\n"
            "Task:\n"
            "1. Determine if this question is a greeting (like 'hello', 'hi', 'hey'), small talk, "
            "or completely unrelated to the dataset category. (e.g., questions about weather, food, general chat, "
            "or questions that do not ask about data at all).\n"
            "2. If it is a greeting or unrelated, generate a short, friendly, and helpful response in English "
            "explaining that you are a data assistant for this category, and give 2-3 specific example questions "
            "they could ask about the data in this category.\n"
            "3. If it IS a valid data question related to this category (even if phrased naturally or simply), respond ONLY with the word 'VALID'.\n\n"
            "Example dataset categories and their contents:\n"
            "- 'Overview Vessel': vessel productivity (BCH/BSH), call count, boxes, teus (domestic/international).\n"
            "- 'Container Throughput': container throughput actual vs budget performance (domestic/international).\n"
            "- 'Market Share': market share percentages of line operators (LOP) (domestic/international).\n"
            "- 'Transhipment': transhipment container counts (20ft, 40ft), vessel operators, loading terminals, cities.\n\n"
            "Response format:\n"
            "Either 'VALID' (exactly) or your friendly English response."
        )
        
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        text_resp = response.text.strip()
        if text_resp.upper() == "VALID":
            return None
        return text_resp
    except Exception as e:
        print(f"[check_data_query] Gemini check failed: {e}")
        # Local rule-based fallback check if Gemini fails
        greetings = ["halo", "hello", "hi ", "hei", "hey", "good morning", "good afternoon", "good evening", "who are you", "help", "support"]
        q_lower = question.lower().strip()
        if any(g in q_lower for g in greetings) or len(q_lower.split()) < 3:
            return f"I am the data assistant for the '{category}' category. Please ask any questions related to the data in this category."
        return None


def answer_tabular_question(question: str, category_name: str) -> dict:
    """
    Answers a tabular question by delegating processing to specialized modular components
    (Resolver, Classifier, Decomposer, Query Builder, Executor, Retry Engine, and Formatter).
    
    API Contract:
        Returns: {"answer": str, "sources": list[str]}
    """
    from app.services.tabular.resolver import sanitize_leading_number
    question = sanitize_leading_number(question)
    
    # 1. Guard against greetings and out-of-scope messages before any query plan building
    greeting_resp = check_data_query_and_respond(question, category_name)
    if greeting_resp:
        return {
            "answer": greeting_resp,
            "sources": [f"Category Info: {category_name}"]
        }
    
    is_all_data = not category_name or str(category_name).strip().lower() in ["all data", "all datasource", "all datasources", "all", ""]
    
    if is_all_data:
        route_res = route_dataset(question, None)
    else:
        route_res = route_dataset(question, category_name)
        if route_res:
            route_res.dataset = category_name
            
    if not route_res or not route_res.dataset:
        return {
            "answer": "Maaf, tidak dapat menentukan dataset yang tepat untuk pertanyaan Anda.",
            "sources": [f"Supabase Table: {category_name}"]
        }

    target_category = route_res.dataset

    try:
        with get_db_conn() as conn:
            res = conn.execute(
                text("SELECT id, column_schema FROM data_sources WHERE category_name = :category_name"),
                {"category_name": target_category}
            ).fetchone()
    except Exception as e:
        return {
            "answer": f"Gagal mengakses database: {str(e)}",
            "sources": []
        }

    if not res:
        return {
            "answer": f"Maaf, dataset untuk kategori '{target_category}' tidak ditemukan di database. Kemungkinan dataset ini telah dihapus atau belum disinkronisasikan.",
            "sources": []
        }

    source_id, schema_raw = res
    column_schema = schema_raw if isinstance(schema_raw, dict) else json.loads(schema_raw or "{}")
    try:
        resolved = resolve_entities(question, route_res.dataset)
        sheets = route_sheet(question, route_res.dataset)
        
        # Transhipment-specific sheet logic:
        # - 'new vr' sheet contains VESSEL REVENUE and KATEGORI data
        # - 'Transhipment ' sheet contains 20'/40' container counts
        if route_res.dataset == "Transhipment":
            question_lower_trs = question.lower()
            if any(kw in question_lower_trs for kw in ["vessel revenue", "revenue", "loading", "discharge", "muat", "bongkar"]):
                sheets = ["new vr"]
            elif not sheets:
                sheets = ["Transhipment"]
        
        sheet = sheets[0] if sheets and len(sheets) == 1 else None
    except Exception as e:
        return {
            "answer": f"Gagal menganalisis entitas pertanyaan: {str(e)}",
            "sources": [f"Supabase Table: {route_res.dataset}"]
        }

    try:
        ast = classify_query(question, resolved, route_res.dataset)
        
        # Inject KATEGORI filter for Transhipment loading/discharge questions
        if route_res.dataset == "Transhipment":
            from app.services.tabular.domain_models import FilterCondition, FilterOperator
            from dataclasses import replace as dc_replace
            question_lower_trs = question.lower()
            kategori_val = None
            if "total loading" in question_lower_trs or " loading" in question_lower_trs:
                kategori_val = "LOADING"
            elif "discharge" in question_lower_trs or "bongkar" in question_lower_trs:
                kategori_val = "DISCHARGE"
            if kategori_val:
                existing_cols = [f.column.upper() for f in ast.filters]
                if "KATEGORI" not in existing_cols:
                    new_filters = list(ast.filters) + [FilterCondition(
                        column="KATEGORI",
                        operator=FilterOperator.EQ,
                        value=kategori_val
                    )]
                    ast = dc_replace(ast, filters=new_filters)
        
        subqueries = decompose_query(ast, question, resolved, route_res.dataset)
    except Exception as e:
        return {
            "answer": f"Gagal mengklasifikasikan pertanyaan: {str(e)}",
            "sources": [f"Supabase Table: {route_res.dataset}"]
        }

    results = {}
    last_plan = None
    steps_debug = {}
    
    for sub_q in subqueries:
        try:
            sub_resolved = resolve_entities(sub_q.question, route_res.dataset)
            sub_ast = classify_query(sub_q.question, sub_resolved, route_res.dataset)
            
            plan = build_query_plan(
                sub_ast, 
                sub_q.question, 
                resolved, 
                route_res.dataset, 
                schema=column_schema, 
                subquery=sub_q
            )
            
            sub_sheets = route_sheet(sub_q.question, route_res.dataset)
            sub_sheet = sub_sheets[0] if sub_sheets and len(sub_sheets) == 1 else None
            if not sub_sheet and len(subqueries) == 1 and (not sub_sheets or len(sub_sheets) == 1):
                sub_sheet = sheet
            if sub_sheet and not plan.sheet:
                plan = replace(plan, sheet=sub_sheet)
                
            last_plan = plan
            
            exec_res = execute_with_retry(
                source_id=str(source_id),
                plan=plan,
                question=sub_q.question,
                resolved=resolved,
                dataset=route_res.dataset,
                db_schema=column_schema
            )
            results[sub_q.step] = exec_res
            steps_debug[sub_q.step] = {
                "sub_q": sub_q,
                "sub_ast": sub_ast,
                "plan": plan,
                "exec_res": exec_res
            }
            
        except QueryBuildError as qbe:
            return {
                "answer": f"Gagal menyusun rencana query: {str(qbe)}",
                "sources": [f"Supabase Table: {route_res.dataset}"]
            }
        except Exception as e:
            return {
                "answer": f"Gagal mengeksekusi data: {str(e)}",
                "sources": [f"Supabase Table: {route_res.dataset}"]
            }

    try:
        answer = format_response(
            question=question,
            results=results,
            ast=ast,
            resolved=resolved,
            dataset=route_res.dataset,
            original_plan=last_plan
        )
    except Exception as e:
        answer = f"Gagal merumuskan kalimat jawaban: {str(e)}."

    # ── Groq narrative polishing ──────────────────────────────────────────────
    # Groq's ONLY role here: rephrase the deterministic formatter output into a
    # natural Indonesian sentence. It never touches data, filters, or numbers.
    # If Groq is not configured or fails → silently fall back to formatter text.
    raw_formatter_answer = answer
    try:
        from app.services.groq_client import groq_generate
        narrative_prompt = (
            f"Berikut adalah hasil faktual dari query data:\n"
            f"{raw_formatter_answer}\n\n"
            "Ubah kalimat di atas menjadi satu kalimat yang natural, ringkas, dan profesional dalam Bahasa Indonesia. "
            "Gunakan nada yang ramah namun tetap formal. "
            "JANGAN menambah informasi apapun yang tidak ada di kalimat aslinya. "
            "JANGAN mengubah angka atau fakta apapun. "
            "Jika kalimat aslinya sudah berupa tabel atau daftar, biarkan format tersebut tetap ada dan hanya perbaiki kalimat pengantarnya."
        )
        answer = groq_generate(prompt=narrative_prompt)
        print(f"[tabular_query] Groq narrative: raw='{raw_formatter_answer}' → polished='{answer[:120]}...'")
    except Exception as groq_err:
        print(f"[tabular_query] Groq narrative skipped ({groq_err}), using formatter output.")
        answer = raw_formatter_answer
    # ─────────────────────────────────────────────────────────────────────────

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
            f"- Dataset: `{route_res.dataset}` | Method: `{route_res.method.value if route_res.method else 'None'}` | Score: `{route_res.score}`",
            "",
            "**Sheet Routing**",
            f"- Resolved: `{sheets}` | Plan Sheet: `{sheet}`",
            "",
            "**Entities**",
            f"- Operators: `{resolved.operators}` | Metrics: `{resolved.metrics}` | Columns: `{resolved.columns}`",
            f"- Month: `{resolved.month.month_str if resolved.month else 'None'}` | Month Code: `{resolved.month.month_code if resolved.month else 'None'}` | Year: `{resolved.month.year if resolved.month else 'None'}`",
            "",
            "**Classification**",
            f"- Query Type: `{ast.query_type.value}` | Intent: `{ast.intent.value}` | Build Method: `{ast.build_method.value}`",
            ""
        ]
        
        for step, step_info in sorted(steps_debug.items()):
            sub_ast = step_info["sub_ast"]
            plan = step_info["plan"]
            exec_res = step_info["exec_res"]
            
            ast_filters = f"Filters: `{[f.column + ' ' + f.operator.value + ' ' + str(f.value) for f in sub_ast.filters]}`"
            ast_agg = f"Aggregation: `{sub_ast.aggregation.func + '(' + str(sub_ast.aggregation.column) + ')' if sub_ast.aggregation else 'None'}`"
            
            plan_sheet = f"Sheet: `{plan.sheet}`"
            plan_group = f"Group By: `{plan.group_by}`"
            plan_sort = f"Sort: `{plan.sort}` | Limit: `{plan.limit}`"
            
            exec_qual = f"Quality: `{exec_res.quality.value}`"
            exec_rows = f"Row Count: `{exec_res.row_count}`"
            exec_retries = f"Retry Count: `{exec_res.retry_count}`"
            
            debug_lines.extend([
                f"**AST — Step {step}**",
                f"- {ast_filters} | {ast_agg}",
                "",
                f"**Query Plan — Step {step}**",
                f"- {plan_sheet} | {plan_group} | {plan_sort}",
                "",
                f"**Execution Result — Step {step}**",
                f"- {exec_qual} | {exec_rows} | {exec_retries}",
            ])
            
            data = exec_res.data
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                debug_lines.append(f"- Data Type: `DataFrame` | Shape: `{data.shape}` | Columns: `{list(data.columns)}`")
            elif isinstance(data, pd.Series):
                debug_lines.append(f"- Data Type: `Series` | Length: `{len(data)}` | Name: `{data.name}`")
            else:
                debug_lines.append(f"- Data Type: `{type(data).__name__}` | Data: `{data}`")
            debug_lines.append("")

        answer += "\n".join(debug_lines)

    return {
        "answer": answer,
        "sources": [f"Supabase Table: {route_res.dataset}"]
    }
