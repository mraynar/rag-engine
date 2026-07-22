"""
Retrieval Agent — urus embedding pertanyaan & pencarian similarity di ChromaDB.
Sesuai AGENTS.md: logic retrieval HANYA di sini, tidak boleh bocor ke routes/.
"""

import chromadb
from google.genai import types

from app.core.config import (
    DISTANCE_THRESHOLD,
    EMBEDDING_MODEL,
    TOP_N,
    VECTOR_STORE_DIR,
    gemini_client,
)


def embed_query(text: str) -> list[float]:
    result = gemini_client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def retrieve_relevant_chunks(question: str) -> tuple[list[str], list[str]]:
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = chroma_client.get_or_create_collection(name="tps_docs")

    query_embedding = embed_query(question)
    results = collection.query(query_embeddings=[query_embedding], n_results=TOP_N)

    all_chunks = results["documents"][0]
    all_sources = [meta["source"] for meta in results["metadatas"][0]]
    all_distances = results["distances"][0]

    chunks, sources = [], []
    for chunk, source, distance in zip(all_chunks, all_sources, all_distances):
        if distance <= DISTANCE_THRESHOLD:
            chunks.append(chunk)
            sources.append(source)

    return chunks, sources
