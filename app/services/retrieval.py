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

    if category and category != "Semua Data":
        where_filter = {"category": category}
    else:
        active_sources = get_active_filenames()
        if active_sources:
            where_filter = {"source": {"$in": active_sources}}
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

