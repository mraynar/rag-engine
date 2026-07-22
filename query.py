"""
Script belajar RAG - Tahap 2 & 3: RETRIEVAL + AUGMENTED + GENERATION

Jalankan: python query.py "pertanyaan Anda di sini"
"""

import sys
from pathlib import Path

import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

VECTOR_STORE_DIR = Path(__file__).parent / "data" / "vector_store"
EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "gemini-2.5-flash"
TOP_N = 3
DISTANCE_THRESHOLD = 0.65  


def embed_query(text):
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
    contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values


def retrieve_relevant_chunks(question):
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = chroma_client.get_or_create_collection(name="tps_docs")

    query_embedding = embed_query(question)
    results = collection.query(query_embeddings=[query_embedding], n_results=TOP_N)

    all_chunks = results["documents"][0]
    all_sources = [meta["source"] for meta in results["metadatas"][0]]
    all_distances = results["distances"][0]

    print("Distance tiap chunk (untuk kalibrasi threshold):")
    for src, dist in zip(all_sources, all_distances):
        print(f"  [{src}] distance={dist:.4f}")

    chunks, sources = [], []
    for chunk, source, distance in zip(all_chunks, all_sources, all_distances):
        if distance <= DISTANCE_THRESHOLD:
            chunks.append(chunk)
            sources.append(source)

    return chunks, sources


def build_prompt(question, chunks):
    context = "\n\n".join(chunks)
    return f"""Jawab pertanyaan berikut HANYA berdasarkan konteks di bawah ini.
Kalau jawabannya tidak ada di konteks, katakan tidak tahu, jangan mengarang.

Konteks:
{context}

Pertanyaan: {question}

Jawaban:"""


def generate_answer(prompt):
    response = client.models.generate_content(model=GENERATION_MODEL, contents=prompt)
    return response.text


def main():
    if len(sys.argv) < 2:
        print('Cara pakai: python query.py "pertanyaan Anda"')
        sys.exit(1)

    question = sys.argv[1]
    print(f"Pertanyaan: {question}\n")

    chunks, sources = retrieve_relevant_chunks(question)

    if not chunks:
        print("\nTidak ada chunk yang cukup relevan (semua di atas threshold).")
        print("Jawaban:\nMaaf, saya tidak menemukan informasi ini di dokumen.")
        return

    print("\nChunk yang lolos threshold (RETRIEVAL):")
    for chunk, source in zip(chunks, sources):
        print(f"  [{source}] {chunk[:60]}...")

    prompt = build_prompt(question, chunks)
    answer = generate_answer(prompt)
    print(f"\nJawaban:\n{answer}")


if __name__ == "__main__":
    main()