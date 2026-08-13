import json
import os
from typing import Optional

import pandas as pd
from google.genai import types
from sqlalchemy import text

from app.core.config import get_gemini_client, get_generation_model
from app.services.db import get_db_conn


def answer_tabular_question(question: str, category_name: str) -> dict:
    """Answers a tabular question by querying the schema, translating to filter parameters with Gemini,

    executing pandas aggregation, and formatting the response.
    """
    # 1. Fetch source metadata from Supabase
    with get_db_conn() as conn:
        res = conn.execute(
            text("SELECT id, column_schema FROM data_sources WHERE category_name = :category_name"),
            {"category_name": category_name}
        ).fetchone()

    if not res:
        raise ValueError(f"Category '{category_name}' not found in data_sources database.")

    source_id, schema_raw = res
    column_schema = schema_raw if isinstance(schema_raw, dict) else json.loads(schema_raw or "{}")

    # 2. Call Gemini (Call 1) in JSON mode to translate question to filter parameters
    schema_context_str = json.dumps(column_schema, indent=2)
    prompt_p1 = f"""You are a database helper that translates natural language questions into structured pandas query parameters.
Based on the question and the column schemas provided below, you must output a JSON object with the following structure:
{{
  "sheet": "Name of the sheet to query",
  "filters": [
    {{"column": "Column Name", "operator": "==", "value": 4170}}
  ],
  "aggregation": {{
    "func": "sum" | "mean" | "max" | "min" | "count" | null,
    "column": "Column Name to aggregate"
  }},
  "group_by": ["Column Name"] | null
}}

Available operators: '==', '!=', '>', '<', '>=', '<=', 'contains', 'in'.
For string values in filters, use the exact match from the context if possible.
If the question requests an aggregation (like total, sum, average, max, highest, etc.), populate the 'aggregation' block.
Ensure that column names match the provided schema exactly (case-sensitive).

---
Column Schemas:
{schema_context_str}

---
Question: {question}
"""

    client = get_gemini_client()
    model = get_generation_model()

    # Retry loop for JSON generation and parsing
    parsed_params = None
    last_err = None
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt_p1,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                )
            )
            resp_text = response.text.strip()
            parsed_params = json.loads(resp_text)
            break
        except Exception as e:
            last_err = e
            prompt_p1 += f"\n\nRetry Notice: Your previous output failed to parse or was invalid: {e}. Please ensure it is strict JSON."

    if parsed_params is None:
        return {
            "answer": f"Saya tidak dapat menerjemahkan pertanyaan ke parameter query tabular (Error: {last_err}).",
            "sources": []
        }

    sheet = parsed_params.get("sheet")
    filters = parsed_params.get("filters") or []
    aggregation = parsed_params.get("aggregation") or {}
    group_by = parsed_params.get("group_by")

    # 3. Pull relevant row data from Supabase
    # If a specific sheet was identified, we limit loading to that sheet.
    with get_db_conn() as conn:
        if sheet:
            rows = conn.execute(
                text("""
                    SELECT sheet_name, row_data
                    FROM data_rows
                    WHERE source_id = :source_id AND LOWER(sheet_name) = :sheet
                """),
                {"source_id": source_id, "sheet": sheet.lower()}
            ).fetchall()
        else:
            rows = conn.execute(
                text("""
                    SELECT sheet_name, row_data
                    FROM data_rows
                    WHERE source_id = :source_id
                """),
                {"source_id": source_id}
            ).fetchall()

    if not rows:
        return {
            "answer": f"Tidak ditemukan data untuk kategori '{category_name}' (Sheet: '{sheet or 'Semua'}') di database.",
            "sources": []
        }

    # Normalize JSONB rows into a flat DataFrame
    records = []
    for r in rows:
        r_data = r[1]
        if isinstance(r_data, str):
            r_data = json.loads(r_data)
        # Include sheet name for reference
        r_data["_sheet"] = r[0]
        records.append(r_data)

    df = pd.DataFrame(records)

    # 4. Apply filters locally using pandas
    try:
        for f in filters:
            col = f.get("column")
            op = f.get("operator")
            val = f.get("value")

            if col not in df.columns:
                # Case-insensitive column matching fallback
                matched_col = next((c for c in df.columns if c.lower() == col.lower()), None)
                if matched_col:
                    col = matched_col
                else:
                    continue

            # Handle type coercion for numeric comparison
            if isinstance(val, (int, float)):
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Apply operator
            if op == "==":
                df = df[df[col] == val]
            elif op == "!=":
                df = df[df[col] != val]
            elif op == ">":
                df = df[df[col] > val]
            elif op == "<":
                df = df[df[col] < val]
            elif op == ">=":
                df = df[df[col] >= val]
            elif op == "<=":
                df = df[df[col] <= val]
            elif op == "contains":
                df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
            elif op == "in" and isinstance(val, list):
                df = df[df[col].isin(val)]
    except Exception as e:
        return {
            "answer": f"Gagal memproses filter data menggunakan pandas: {e}",
            "sources": []
        }

    # 5. Apply aggregation
    agg_func = aggregation.get("func")
    agg_col = aggregation.get("column")
    pandas_result_summary = ""

    try:
        if agg_func and agg_func != "null":
            if agg_col and agg_col not in df.columns:
                matched_col = next((c for c in df.columns if c.lower() == agg_col.lower()), None)
                if matched_col:
                    agg_col = matched_col

            if agg_func == "count":
                count_val = len(df)
                pandas_result_summary = f"Total Count (Rows matching): {count_val}"
            elif agg_col:
                # Coerce to numeric for calculation
                df[agg_col] = pd.to_numeric(df[agg_col], errors='coerce')
                if agg_func == "sum":
                    pandas_result_summary = f"Sum of {agg_col}: {df[agg_col].sum()}"
                elif agg_func == "mean":
                    pandas_result_summary = f"Average of {agg_col}: {df[agg_col].mean()}"
                elif agg_func == "max":
                    pandas_result_summary = f"Maximum value of {agg_col}: {df[agg_col].max()}"
                elif agg_func == "min":
                    pandas_result_summary = f"Minimum value of {agg_col}: {df[agg_col].min()}"
            else:
                pandas_result_summary = f"Rows matching filter count: {len(df)}"
        else:
            # If no aggregation, summarize filtered rows (max 30 rows to prevent blowing context)
            df_display = df.drop(columns=["_sheet"], errors="ignore")
            pandas_result_summary = df_display.head(30).to_string(index=False)
            if len(df) > 30:
                pandas_result_summary += f"\n\n... (Truncated. Total matching rows: {len(df)})"

    except Exception as e:
        return {
            "answer": f"Gagal menghitung agregasi data: {e}",
            "sources": []
        }

    # 6. Call Gemini (Call 2) to format the response naturally based on pandas result
    prompt_p2 = f"""You are a professional assistant for PT Terminal Petikemas Surabaya (TPS).
Answer the user's question naturally based on the pre-aggregated/pre-filtered data result from pandas below.
Your answer must be in Indonesian, formal, and accurate to the data provided.

---
Pandas Query Execution Results:
{pandas_result_summary}

---
Question: {question}
"""

    try:
        response2 = client.models.generate_content(
            model=model,
            contents=prompt_p2
        )
        answer = response2.text.strip()
    except Exception as e:
        answer = f"Gagal merumuskan jawaban akhir: {e}. Hasil mentah perhitungan: {pandas_result_summary}"

    return {
        "answer": answer,
        "sources": [f"Supabase Table: {category_name}"]
    }
