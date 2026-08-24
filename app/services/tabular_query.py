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


def answer_tabular_question(question: str, category_name: str) -> dict:
    """
    Answers a tabular question by delegating processing to specialized modular components
    (Resolver, Classifier, Decomposer, Query Builder, Executor, Retry Engine, and Formatter).
    
    API Contract:
        Returns: {"answer": str, "sources": list[str]}
    """
    from app.services.tabular.resolver import sanitize_leading_number
    question = sanitize_leading_number(question)
    try:
        with get_db_conn() as conn:
            res = conn.execute(
                text("SELECT id, column_schema FROM data_sources WHERE category_name = :category_name"),
                {"category_name": category_name}
            ).fetchone()
    except Exception as e:
        return {
            "answer": f"Gagal mengakses database: {str(e)}",
            "sources": []
        }

    if not res:
        return {
            "answer": f"Maaf, dataset untuk kategori '{category_name}' tidak ditemukan di database. Kemungkinan dataset ini telah dihapus atau belum disinkronisasikan.",
            "sources": []
        }

    source_id, schema_raw = res
    column_schema = schema_raw if isinstance(schema_raw, dict) else json.loads(schema_raw or "{}")

    route_res = route_dataset(question, category_name)
    if category_name and route_res:
        route_res.dataset = category_name
        
    if not route_res or not route_res.dataset:
        return {
            "answer": f"Maaf, tidak dapat menentukan dataset yang tepat untuk pertanyaan Anda.",
            "sources": [f"Supabase Table: {category_name}"]
        }
    try:
        resolved = resolve_entities(question, route_res.dataset)
        sheets = route_sheet(question, route_res.dataset)
        if not sheets and route_res.dataset == "Transhipment":
            sheets = ["Transhipment"]
        sheet = sheets[0] if sheets and len(sheets) == 1 else None
    except Exception as e:
        return {
            "answer": f"Gagal menganalisis entitas pertanyaan: {str(e)}",
            "sources": [f"Supabase Table: {route_res.dataset}"]
        }

    try:
        ast = classify_query(question, resolved, route_res.dataset)
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
            f"- Dataset: `{route_res.dataset}`",
            f"- Method: `{route_res.method.value if route_res.method else 'None'}`",
            f"- Score: `{route_res.score}`",
            f"- Candidates: `{route_res.candidates}`",
            "",
            "**Sheet Routing**",
            f"- Resolved: `{sheets}`",
            f"- Plan Sheet: `{sheet}`",
            "",
            "**Entities**",
            f"- Operators: `{resolved.operators}`",
            f"- Metrics: `{resolved.metrics}`",
            f"- Columns: `{resolved.columns}`",
            f"- Month: `{resolved.month.month_str if resolved.month else 'None'}`",
            f"- Month Code: `{resolved.month.month_code if resolved.month else 'None'}`",
            f"- Year: `{resolved.month.year if resolved.month else 'None'}`",
            "",
            "**Classification**",
            f"- Query Type: `{ast.query_type.value}`",
            f"- Intent: `{ast.intent.value}`",
            f"- Build Method: `{ast.build_method.value}`",
            "",
            "**Decomposition**"
        ]
        
        for sq in subqueries:
            debug_lines.extend([
                f"- Step {sq.step}",
                f"  - Question: `{sq.question}`",
                f"  - Template: `{sq.template_type.value}`",
                f"  - Depends On: `{sq.depends_on}`"
            ])
            
        debug_lines.append("")
        
        for step, step_info in sorted(steps_debug.items()):
            sub_q = step_info["sub_q"]
            sub_ast = step_info["sub_ast"]
            plan = step_info["plan"]
            exec_res = step_info["exec_res"]
            
            debug_lines.extend([
                f"**AST — Step {step}**",
                f"- Query Type: `{sub_ast.query_type.value}`",
                f"- Intent: `{sub_ast.intent.value}`",
                f"- Filters: `{[f.column + ' ' + f.operator.value + ' ' + str(f.value) for f in sub_ast.filters]}`",
                f"- Aggregation: `{sub_ast.aggregation.func + '(' + str(sub_ast.aggregation.column) + ')' if sub_ast.aggregation else 'None'}`",
                f"- Build Method: `{sub_ast.build_method.value}`",
                "",
                f"**Query Plan — Step {step}**",
                f"- Sheet: `{plan.sheet}`",
                f"- Filters: `{[f.column + ' ' + f.operator.value + ' ' + str(f.value) for f in plan.filters]}`",
                f"- Aggregation: `{plan.aggregation.func + '(' + str(plan.aggregation.column) + ')' if plan.aggregation else 'None'}`",
                f"- Group By: `{plan.group_by}`",
                f"- Sort: `{plan.sort}`",
                f"- Limit: `{plan.limit}`",
                f"- Build Method: `{plan.build_method.value}`",
                "",
                f"**Execution Result — Step {step}**",
                f"- Quality: `{exec_res.quality.value}`",
                f"- Row Count: `{exec_res.row_count}`",
                f"- Retry Count: `{exec_res.retry_count}`",
                f"- Last Retry Strategy: `{exec_res.last_retry_strategy.value if exec_res.last_retry_strategy else 'None'}`"
            ])
            
            data = exec_res.data
            import pandas as pd
            if isinstance(data, pd.DataFrame):
                preview = data.head(5).to_string(index=False)
                debug_lines.extend([
                    "- Data Type: `DataFrame`",
                    f"- Shape: `{data.shape}`",
                    f"- Columns: `{list(data.columns)}`",
                    "- Preview:",
                    "```",
                    preview,
                    "```"
                ])
            elif isinstance(data, pd.Series):
                preview = data.head(5).to_string()
                debug_lines.extend([
                    "- Data Type: `Series`",
                    f"- Name: `{data.name}`",
                    f"- Length: `{len(data)}`",
                    "- Preview:",
                    "```",
                    preview,
                    "```"
                ])
            else:
                debug_lines.extend([
                    f"- Data Type: `{type(data).__name__}`",
                    f"- Data: `{data}`"
                ])
            debug_lines.append("")

        debug_lines.extend([
            "**Formatter**",
            f"- Result Steps: `{list(results.keys())}`",
            f"- Final Answer: `{answer}`"
        ])
        
        answer += "\n".join(debug_lines)

    return {
        "answer": answer,
        "sources": [f"Supabase Table: {route_res.dataset}"]
    }
