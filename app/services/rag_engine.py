"""
Engine RAG (Retrieval-Augmented Generation) untuk pencarian vektor dan pemrosesan LLM.
"""
from datetime import datetime, timezone, timedelta
import logging
from typing import Optional
import threading
import chromadb
from google.genai import types
from groq import Groq

from app.core.config import (
    DISTANCE_THRESHOLD,
    TOP_N,
    VECTOR_STORE_DIR,
    get_embedding_model,
    get_generation_model,
    get_gemini_client,
)
from app.services.config_store import get_active_value
from app.services.stores import get_active_filenames, list_sources

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_MONTHS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

_thread_local = threading.local()


# ── Groq Client 
def get_groq_api_key() -> str:
    return get_active_value("groq_api_key")


def get_groq_model() -> str:
    try:
        return get_active_value("groq_model")
    except RuntimeError:
        return "llama-3.3-70b-versatile"


def get_groq_client() -> Groq:
    api_key = get_groq_api_key()
    if not hasattr(_thread_local, "groq_cache"):
        _thread_local.groq_cache = {}
    cache = _thread_local.groq_cache
    if api_key not in cache:
        cache[api_key] = Groq(api_key=api_key)
    return cache[api_key]


def groq_generate(prompt: str, system: str = "") -> str:
    client = get_groq_client()
    model = get_groq_model()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content


# ── Retrieval (Vector Store & Embeddings) ────────────────────────────────────

def embed_query(text: str) -> list[float]:
    result = get_gemini_client().models.embed_content(
        model=get_embedding_model(),
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def retrieve_relevant_chunks(question: str, category: Optional[str] = None) -> tuple[list[str], list[str]]:
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = chroma_client.get_or_create_collection(name="tps_docs")

    category_clean = category.strip() if category else None
    if category_clean and category_clean.lower() not in ("semua data", "all data", "all", ""):
        active_sources = get_active_filenames()
        matched_source = next((s for s in active_sources if s.lower() == category_clean.lower()), None)
        if matched_source:
            where_filter = {"source": matched_source}
        else:
            matched_cat = None
            try:
                for s in list_sources():
                    if s.get("category_name", "").strip().lower() == category_clean.lower():
                        matched_cat = s["category_name"]
                        break
            except Exception:
                pass
            where_filter = {"category": matched_cat if matched_cat else category_clean}
    else:
        active_sources = get_active_filenames()
        active_categories = []
        try:
            active_categories = [s["category_name"] for s in list_sources() if s.get("sync_status") in ("success", "synced")]
        except Exception:
            pass

        or_conditions = []
        if active_sources:
            or_conditions.append({"source": {"$in": active_sources}})
        if active_categories:
            or_conditions.append({"category": {"$in": active_categories}})

        if len(or_conditions) == 1:
            where_filter = or_conditions[0]
        elif len(or_conditions) > 1:
            where_filter = {"$or": or_conditions}
        else:
            where_filter = None

    query_embedding = embed_query(text=question)

    try:
        total_in_filter = collection.count()
    except Exception:
        total_in_filter = TOP_N
    safe_n = min(TOP_N, max(1, total_in_filter))

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=safe_n,
        where=where_filter,
    )

    all_chunks = results["documents"][0]
    all_sources = [meta["source"] for meta in results["metadatas"][0]]
    all_distances = results["distances"][0]

    chunks, sources = [], []
    for chunk, source, distance in zip(all_chunks, all_sources, all_distances):
        if distance <= DISTANCE_THRESHOLD:
            chunks.append(chunk)
            sources.append(source)

    return chunks, sources


# ── Generation & Prompt Builder ───────────────────────────────────────────────

def get_wib_formatted_date() -> str:
    wib_tz = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib_tz)
    day_name = _DAYS[now_wib.weekday()]
    month_name = _MONTHS[now_wib.month]
    return f"{day_name}, {month_name} {now_wib.day}, {now_wib.year}"


def build_prompt(question: str, chunks: list[str]) -> str:
    formatted_date = get_wib_formatted_date()
    context = "\n\n".join(chunks)

    return f"""You are an AI assistant that answers questions ONLY based on the provided document context.

Current date context: Today is {formatted_date} (WIB timezone).
Use this information to interpret relative time references in the user's question, such as "this year", "last year", "last month", "yesterday", etc.

MANDATORY RULES:
1. Use ONLY the data from the "Context" below — do not invent information or use external knowledge.
2. If the data is not in the context, respond with "I cannot find this information in the document."
3. Response format: use **bold** for key terms/names, bullet lists for enumeration, and standard paragraphs for explanation.

Context:
{context}

Question: {question}

Answer:"""


def generate_answer(prompt: str) -> str:
    try:
        return groq_generate(
            prompt=prompt,
            system="You are an AI assistant for PT Terminal Petikemas Surabaya (TPS). Respond in a clear, professional, and helpful manner."
        )
    except Exception as groq_err:
        logging.getLogger(__name__).warning(f"[generation] Groq failed ({groq_err}), falling back to Gemini.")
        client = get_gemini_client()
        response = client.models.generate_content(
            model=get_generation_model(), contents=prompt
        )
        return response.text
