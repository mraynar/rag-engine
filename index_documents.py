"""
Script belajar RAG - Tahap 1: INDEXING

Alur di file ini:
1. Baca semua file .txt di data/documents/
2. Pecah tiap dokumen jadi potongan kecil (chunk)
3. Ubah tiap chunk jadi embedding (vektor angka) pakai Gemini
4. Simpan embedding + teks aslinya ke ChromaDB (vector store lokal)

Jalankan: python index_documents.py
"""

from pathlib import Path
import re

import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

DOCUMENTS_DIR = Path(__file__).parent / "data" / "documents"
VECTOR_STORE_DIR = Path(__file__).parent / "data" / "vector_store"

EMBEDDING_MODEL = "gemini-embedding-001"
CHUNK_SIZE = 300


def read_documents():
    docs = []
    for file_path in DOCUMENTS_DIR.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8")
        docs.append({"filename": file_path.name, "text": text})
    return docs


def split_sentences(text):
    # Pecah teks jadi kalimat berdasarkan tanda titik/tanya/seru diikuti spasi.
    # Baris kosong (antar paragraf) juga dianggap pemisah.
    text = text.strip()
    raw = re.split(r"(?<=[.!?])\s+|\n\s*\n", text)
    return [s.strip() for s in raw if s.strip()]


def chunk_text(text, chunk_size=CHUNK_SIZE):
    sentences = split_sentences(text)
    chunks = []
    current = ""

    for sentence in sentences: 
        # Kalau 1 kalimat saja sudah melebihi chunk_size, jadikan chunk sendiri
        # (kasus jarang, tapi harus ditangani supaya tidak infinite loop / hilang)
        if len(sentence) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.append(sentence)
            continue

        # Kalau nambah kalimat ini bikin current lewat batas, tutup chunk dulu
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > chunk_size and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = candidate

    if current:
        chunks.append(current.strip())

    return chunks


def embed_text(text):
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return result.embeddings[0].values


def main():
    print("Membaca dokumen...")
    docs = read_documents()
    print(f"Ditemukan {len(docs)} dokumen.")

    chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = chroma_client.get_or_create_collection(name="tps_docs")

    chunk_id = 0
    for doc in docs:
        chunks = chunk_text(doc["text"])
        print(f"\n{doc['filename']}: {len(chunks)} chunk")

        for chunk in chunks:
            embedding = embed_text(chunk)
            collection.add(
                ids=[f"chunk_{chunk_id}"],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": doc["filename"]}],
            )
            print(f"  chunk_{chunk_id} tersimpan ({chunk[:40]}...)")
            chunk_id += 1

    print(f"\nSelesai. Total {chunk_id} chunk tersimpan di {VECTOR_STORE_DIR}")


if __name__ == "__main__":
    main()