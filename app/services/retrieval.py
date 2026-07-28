"""
Retrieval Agent — urus embedding pertanyaan & pencarian similarity di ChromaDB.
Sesuai AGENTS.md: logic retrieval HANYA di sini, tidak boleh bocor ke routes/.

Versi ini menambahkan filter by active documents:
- Hanya chunk dari dokumen yang is_active=True yang dicari
- Jika tidak ada dokumen aktif, langsung return kosong
"""

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


def retrieve_relevant_chunks(question: str) -> tuple[list[str], list[str]]:
    active_sources = get_active_filenames()
    if not active_sources:
        # Tidak ada dokumen aktif — chat.py sudah handle empty chunks dengan graceful message
        return [], []

    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = chroma_client.get_or_create_collection(name="tps_docs")

    query_embedding = embed_query(question)

    # ChromaDB throws if n_results > number of matching chunks — cap it safely
    try:
        total_in_filter = collection.count()
    except Exception:
        total_in_filter = TOP_N
    safe_n = min(TOP_N, max(1, total_in_filter))

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=safe_n,
        where={"source": {"$in": active_sources}},
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
