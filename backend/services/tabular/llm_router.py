"""
LLM-driven semantic dataset routing.

Instead of hardcoded keyword scores, this module:
1. Reads ALL available datasets + their actual column schemas from the DB
2. Passes them as context to the LLM
3. Asks the LLM to pick the most relevant dataset AND sheet for the question

This is fully automatic — adding a new datasource to the DB requires ZERO code changes.
"""
import json
from typing import Optional

from backend.core.config import get_gemini_client, get_generation_model


DATASET_DESCRIPTIONS = {
    "Overview Vessel": (
        "Data produktivitas kapal per operator pelayaran (LOP), meliputi: TEUS, Boxes (BOX), "
        "BCH (Box Crane per Hour), BSH (Box Ship per Hour). "
        "Sheet: DOMESTIC (pelayaran domestik) dan INTERNATIONAL (pelayaran internasional)."
    ),
    "Overview Box": (
        "Data volume box/TEUS per operator pelayaran, dibagi berdasarkan rute DOMESTIK dan INTERNATIONAL. "
        "Berisi kolom BOX, BOXES, TEUS, LOP/VESSEL OPERATOR."
    ),
    "Container Throughput": (
        "Data throughput kontainer total TPS (ACTUAL vs BUDGET), per bulan, per tahun. "
        "Sheet: Domestik dan Internasional. Kolom utama: ACTUAL, BUDGET, ACTUAL VS BUDGET."
    ),
    "Market Share": (
        "Data pangsa pasar (market share / persentase %) operator pelayaran per bulan. "
        "Sheet: V.OPR DOM (domestik) dan V.OPR INT (internasional). Kolom: LOP, %."
    ),
    "Transhipment": (
        "Data transhipment: VESSEL REVENUE, jumlah kontainer 20', 40', 45' (loading dan discharge), "
        "per vessel operator, per bulan/tahun. "
        "Sheet 'new vr': VESSEL REVENUE dan KATEGORI (LOADING/DISCHARGE). "
        "Sheet 'Transhipment': container counts (20', 40'). "
        "Sheet 'VR': ringkasan volume. "
        "Gunakan dataset ini untuk pertanyaan tentang vessel revenue, loading, discharge, atau transhipment."
    ),
    "Realisasi UC": (
        "Data realisasi Unit Cost (UC) per status (Full/Empty/Restow) per bulan. "
        "Kolom: 20', 40', 45', TOTAL BOX, TOTAL TEUs, TOTAL REVENUE, TOTAL DISCOUNT. "
        "Sheet: SUMMARY, OH OW OL, TREND UC."
    ),
    "Komersial Dashboard": (
        "Data dashboard komersial: total revenue per operator, TEUS full/empty, BOX, per bulan. "
        "Kolom utama: TOTAL ALL REVENUE, TOTAL TEUS, TEUS FULL, TEUS EMPTY, BOX, VESSEL OPERATOR. "
        "Gunakan dataset ini untuk pertanyaan tentang ranking revenue operator, pendapatan total."
    ),
    "Vessel Service": (
        "Data service/rute kapal per operator, per bulan: SERVICE (nama rute), ROUTES, "
        "TOTAL CALL, BMPH (Box Moves Per Hour), GMPH, AVERAGE BMPH/GMPH, STATUS. "
        "Gunakan untuk pertanyaan tentang jadwal service, produktivitas crane, atau jumlah call."
    ),
    "RestNDisc": (
        "Data permohonan rest & discount: status permohonan, nama perusahaan, aktivitas, "
        "NOMINAL PERSETUJUAN KERINGANAN, nomor surat, tanggal. "
        "Gunakan untuk pertanyaan tentang keringanan tarif atau persetujuan diskon."
    ),
}

ROUTING_PROMPT_TEMPLATE = """Anda adalah router cerdas untuk sistem RAG analitik data pelabuhan TPS.

## Dataset yang tersedia:
{dataset_list}

## Skema kolom aktual per dataset (dari database):
{schema_context}

## Pertanyaan user:
"{question}"

## Tugas:
1. Pilih SATU dataset yang paling relevan untuk menjawab pertanyaan di atas.
2. Jika ada petunjuk sheet (domestik/internasional/loading/discharge), sebutkan sheet yang relevan.
3. Jika pertanyaan sama sekali tidak relevan dengan data TPS/pelabuhan → jawab dengan "NONE".

## Aturan pemilihan:
- Pertanyaan tentang vessel revenue / loading / discharge → Transhipment
- Pertanyaan tentang ranking revenue operator / total pendapatan per operator → Komersial Dashboard  
- Pertanyaan tentang BCH/BSH/produktivitas kapal per call → Overview Vessel
- Pertanyaan tentang market share / persentase pasar → Market Share
- Pertanyaan tentang throughput ACTUAL vs BUDGET → Container Throughput
- Pertanyaan tentang TEUS domestik/internasional per operator dengan kolom BOX/BOXES → Overview Box
- Pertanyaan tentang unit cost / UC / realisasi → Realisasi UC
- Pertanyaan tentang service/rute kapal/BMPH/GMPH → Vessel Service
- Pertanyaan tentang keringanan tarif / diskon / rest → RestNDisc

## Response format (JSON only, no markdown):
{{
  "dataset": "<nama dataset persis>",
  "sheet": "<nama sheet atau null>",
  "confidence": <0.0-1.0>,
  "reason": "<1 kalimat alasan singkat>"
}}
"""


def llm_route_dataset(question: str, available_datasets: list, db_schemas: dict, chat_history: Optional[list] = None) -> dict:
    """
    Use LLM to semantically select the best dataset for the question.
    Accepts chat_history to handle multi-turn context inheritance ("sebutkan rinciannya", "bagaimana trennya").
    
    Args:
        question: User's natural language question
        available_datasets: List of dataset names from DB
        db_schemas: Dict of {dataset_name: column_schema_dict}
        chat_history: Optional list of recent chat turn dicts
    
    Returns:
        {"dataset": str, "sheet": str|None, "confidence": float, "reason": str}
        or {"dataset": None} if no match
    """
    # Check if question is a follow-up query requiring context inheritance
    history_formatted = "Tidak ada riwayat percakapan sebelumnya."
    if chat_history:
        recent = chat_history[-3:]
        history_lines = []
        for h in recent:
            role = h.get("role", "user")
            content = h.get("content", "")
            history_lines.append(f"{role.upper()}: {content}")
        history_formatted = "\n".join(history_lines)

    # Build dataset list string
    dataset_list_parts = []
    for i, ds in enumerate(available_datasets, 1):
        desc = DATASET_DESCRIPTIONS.get(ds, f"Dataset {ds}")
        dataset_list_parts.append(f"{i}. **{ds}**: {desc}")
    dataset_list = "\n".join(dataset_list_parts)

    # Build concise schema context (top columns per dataset)
    schema_parts = []
    for ds in available_datasets:
        schema = db_schemas.get(ds, {})
        if not schema:
            continue
        # Get all columns (excluding internal _ columns)
        all_cols = schema.get("_all_sheets", [])
        visible_cols = [c for c in all_cols if not c.startswith("_")][:20]
        sheets = [k for k in schema.keys() if k != "_all_sheets"]
        schema_parts.append(
            f"- {ds}: sheets={sheets[:5]}, columns={visible_cols[:15]}"
        )
    schema_context = "\n".join(schema_parts) if schema_parts else "Schema tidak tersedia"

    prompt = f"""Anda adalah router cerdas & context inheritance agent untuk sistem RAG analitik data pelabuhan TPS.

## Dataset yang tersedia:
{dataset_list}

## Skema kolom aktual per dataset (dari database):
{schema_context}

## Riwayat Percakapan (3 Turn Terakhir):
{history_formatted}

## Pertanyaan user saat ini:
"{question}"

## Tugas:
1. Analisis apakah pertanyaan saat ini adalah pertanyaan lanjutan / follow-up (seperti "sebutkan rinciannya", "bagaimana rinciannya", "bagaimana trennya", "siapa yang tertinggi?"). Jika YA, warisi nama dataset dari percakapan sebelumnya.
2. Jika pertanyaan baru, pilih SATU dataset yang paling relevan untuk menjawab pertanyaan di atas.
3. Jika ada petunjuk sheet (domestik/internasional/loading/discharge/summary), sebutkan sheet yang relevan.
4. Jika pertanyaan sama sekali tidak relevan dengan data TPS/pelabuhan → jawab dengan "NONE".

## Response format (JSON only, no markdown):
{{
  "dataset": "<nama dataset persis>",
  "sheet": "<nama sheet atau null>",
  "confidence": 0.9,
  "reason": "<1 kalimat alasan singkat>"
}}
"""

    try:
        client = get_gemini_client()
        model = get_generation_model()
        response = client.models.generate_content(model=model, contents=prompt)
        raw = response.text.strip()
        # Remove markdown code fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        dataset = result.get("dataset")
        if dataset == "NONE" or not dataset:
            return {"dataset": None, "sheet": None, "confidence": 0.0, "reason": "No match"}
        return {
            "dataset": dataset,
            "sheet": result.get("sheet"),
            "confidence": float(result.get("confidence", 0.7)),
            "reason": result.get("reason", ""),
        }
    except Exception as e:
        print(f"[llm_router] LLM routing failed: {e}")
        return {"dataset": None, "sheet": None, "confidence": 0.0, "reason": str(e)}



LLM_QUERY_PLAN_PROMPT = """Anda adalah query planner untuk sistem analitik data pelabuhan TPS.

## Dataset: {dataset}
## Sheet yang digunakan: {sheet}

## Skema kolom yang tersedia (PERHATIKAN kolom _YEAR, _MONTH_CODE, _MONTH_EN, _OPERATOR yang dinormalisasi):
{schema}

## Sample data (5 baris pertama):
{sample_data}

## Pertanyaan:
"{question}"

## Tugas:
Buat query plan untuk menjawab pertanyaan di atas berdasarkan skema kolom yang ada.

## ATURAN PENTING:
1. Gunakan kolom `_YEAR` (integer) untuk filter tahun — BUKAN kolom YEAR/TAHUN asli
2. Gunakan kolom `_MONTH_CODE` (integer 1-12) untuk filter bulan — BUKAN MONTH/BULAN asli
3. Gunakan kolom `_OPERATOR` (uppercase) untuk filter operator — atau kolom asli VESSEL OPERATOR/LOP
4. Jika data TIDAK ADA di skema (misalnya kolom yang disebutkan tidak ada), kembalikan "not_found": true
5. Gunakan hanya kolom yang BENAR-BENAR ADA dalam skema
6. Jangan pernah mengarang kolom yang tidak ada

## Response format (JSON only, no markdown):
{{
  "not_found": false,
  "filters": [
    {{"column": "_YEAR", "op": "==", "value": 2024}},
    {{"column": "_MONTH_CODE", "op": "==", "value": 1}},
    {{"column": "KATEGORI", "op": "==", "value": "LOADING"}}
  ],
  "metric": "VESSEL REVENUE",
  "aggregation": "sum",
  "group_by": null,
  "sort_by": null,
  "limit": null,
  "explanation": "Saya menjumlahkan VESSEL REVENUE dengan filter tahun 2024, bulan Januari, kategori LOADING"
}}

Nilai aggregation yang valid: "sum", "count", "mean", "max", "min", null (jika hanya lookup nilai)
Nilai group_by: nama kolom string atau null
"""


def llm_build_query_plan(
    question: str,
    dataset: str,
    sheet: Optional[str],
    schema: dict,
    sample_data: list,
) -> dict:
    """
    Ask LLM to build a structured query plan from schema + sample data.
    
    Returns dict with: not_found, filters, metric, aggregation, group_by, sort_by, limit, explanation
    """
    # Format schema nicely
    all_cols = schema.get("_all_sheets", schema.get(sheet, list(schema.keys())))
    visible_cols = [c for c in all_cols if not c.startswith("_")]
    norm_cols = [c for c in all_cols if c.startswith("_") and c != "_sheet"]
    schema_str = f"Kolom data asli: {visible_cols}\nKolom normalisasi: {norm_cols}"
    
    # Format sample data (show first 3 rows, limit columns)
    sample_str = "Tidak ada sample"
    if sample_data:
        sample_rows = sample_data[:3]
        rows_str = []
        for row in sample_rows:
            filtered = {k: v for k, v in row.items() 
                       if not k.startswith("_") or k in ["_YEAR", "_MONTH_CODE", "_MONTH_EN", "_OPERATOR"]}
            rows_str.append(str({k: filtered[k] for k in list(filtered.keys())[:12]}))
        sample_str = "\n".join(rows_str)

    prompt = LLM_QUERY_PLAN_PROMPT.format(
        dataset=dataset,
        sheet=sheet or "semua sheet",
        schema=schema_str,
        sample_data=sample_str,
        question=question,
    )

    try:
        client = get_gemini_client()
        model = get_generation_model()
        response = client.models.generate_content(model=model, contents=prompt)
        raw = response.text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        plan = json.loads(raw)
        return plan
    except Exception as e:
        print(f"[llm_router] LLM query plan failed: {e}")
        return {"not_found": True, "explanation": str(e)}
