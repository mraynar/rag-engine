from typing import Optional
import chromadb
from google.genai import types

from app.core.config import (
    DISTANCE_THRESHOLD,
    TOP_N,
    VECTOR_STORE_DIR,
    get_embedding_model,
    get_gemini_client,
)
from app.services.document_store import get_active_filenames


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
            from app.services.sources_store import list_sources
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
        from app.services.sources_store import list_sources
        active_categories = []
        try:
            active_categories = [s["category_name"] for s in list_sources() if s.get("sync_status") == "success"]
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

    # n_results must not exceed the collection size or ChromaDB raises
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

