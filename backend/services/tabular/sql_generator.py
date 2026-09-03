"""
AI Text-to-SQL Generator Specialist Agent Module.
AI-First / LLM-Driven RAG Query Specialist that builds precise query execution plans 
using Dynamic Schema Discovery, 5 Categorical Distinct Value Samples, and Multi-Turn Chat History.
"""

import json
import logging
from typing import Dict, List, Any, Optional

from backend.core.config import get_gemini_client, get_generation_model
from backend.services.tabular.schema_sampler import format_schema_samples_for_llm

logger = logging.getLogger(__name__)


def generate_llm_text_to_sql_plan(
    question: str,
    dataset: str,
    column_schema: Dict[str, List[str]],
    value_samples: Dict[str, List[str]],
    chat_history: Optional[List[Dict[str, Any]]] = None,
    preferred_sheet: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build an AI Text-to-SQL plan based on question, dynamic schema, value samples, and chat history.
    
    Returns a dict with structure:
    {
        "sheet": str or None,
        "metrics": list[str],
        "aggregations": list[str], # sum, mean, count, max, min
        "filters": list[dict],     # [{"column": str, "op": "=="|">"|"<"|"contains", "value": Any}]
        "group_by": str or None,
        "sort_by": "asc"|"desc"|None,
        "limit": int or None,
        "derived_mode": str or None # "market_share_ratio" or None
    }
    """
    # Format schema & samples for prompt
    schema_formatted = json.dumps(column_schema, ensure_ascii=False, indent=2)
    samples_formatted = format_schema_samples_for_llm(value_samples)
    
    # Format chat history (up to 3 turns)
    history_formatted = "None"
    if chat_history:
        recent = chat_history[-3:]
        history_lines = []
        for h in recent:
            role = h.get("role", "user")
            content = h.get("content", "")
            history_lines.append(f"{role.upper()}: {content}")
        history_formatted = "\n".join(history_lines)

    prompt = f"""You are an expert AI Data Specialist & Text-to-SQL Generator for port terminal operations database.
Target Dataset: '{dataset}'

DYNAMIC DB SCHEMA:
{schema_formatted}

CATEGORICAL COLUMN DISTINCT VALUE SAMPLES (5 Distinct Samples per Text Column):
{samples_formatted}

CHAT HISTORY (3 Recent Turns for Multi-Turn Context Inheritance):
{history_formatted}

CURRENT USER QUESTION:
"{question}"

PREFERRED SHEET (If determined by Router):
{preferred_sheet or 'Auto-detect best sheet'}

INSTRUCTIONS:
1. Examine the User Question, Chat History, Schema, and Value Samples.
2. If the user asks a follow-up question (e.g. "sebutkan rinciannya", "bagaimana trennya?", "siapa yang tertinggi?"), inherit the dataset, year, month, and filters from Chat History.
3. Identify ALL requested metrics in the question. If the user asks for BOTH TEUS and REVENUE, include BOTH in `metrics`.
4. Month Matching: If user mentions a month (e.g. "dibulan 2", "bulan 5", "Februari"), match the exact column values from Value Samples (e.g. 'February', '2', '02', 'Mei', '5').
5. Sheet Choice: Pick the sheet containing the requested metric columns. For example:
   - For 'Transhipment', 'VESSEL REVENUE' is in sheet 'new vr'.
   - For 'Overview Box', 'TEUS' is in sheet 'DOMESTIK' or 'INTERNATIONAL'.
   - For 'Realisasi UC', 'TOTAL BOX', 'TOTAL TEUS', 'TOTAL REVENUE' are in 'OH OW OL' or 'SUMMARY'.
6. Market Share %: If user asks for Market Share % or Market Share trend and percentage column is null, set `derived_mode`: "market_share_ratio".

RETURN ONLY VALID JSON WITH THIS EXACT STRUCTURE (no markdown fences, no explanation):
{{
    "sheet": "<exact sheet name string or null>",
    "metrics": ["<column_name_1>", "<column_name_2>"],
    "aggregations": ["sum"],
    "filters": [
        {{"column": "<exact_column_name>", "op": "==", "value": "<matched_value>"}}
    ],
    "group_by": "<exact_column_name or null>",
    "sort_by": "desc",
    "limit": 10,
    "derived_mode": null
}}
"""

    try:
        client = get_gemini_client()
        model = get_generation_model()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        text_resp = response.text.strip()
        parsed = json.loads(text_resp)
        logger.info(f"[sql_generator] Successfully generated plan: {parsed}")
        return parsed
    except Exception as e:
        logger.error(f"[sql_generator] Failed to generate plan via Gemini: {e}")
        # Fallback default plan structure
        return {
            "sheet": preferred_sheet,
            "metrics": [],
            "aggregations": ["sum"],
            "filters": [],
            "group_by": None,
            "sort_by": None,
            "limit": 10,
            "derived_mode": None
        }
