from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.chat import router as chat_router
from app.api.routes.config import router as config_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.documents import router as documents_router


def _migrate_legacy_documents() -> None:
    """One-time migration: daftarkan dokumen lama (dari index_documents.py) ke document store.

    Dipanggil saat startup. Jika document store sudah berisi data, langsung keluar
    (migration hanya jalan sekali). Jika kosong, scan ChromaDB untuk menemukan
    chunk-chunk yang sudah ada dan daftarkan sumber-sumbernya secara otomatis.
    """
    import chromadb
    from pathlib import Path

    from app.core.config import VECTOR_STORE_DIR
    from app.services.document_store import (
        _load_store,
        get_active_filenames,
        register_document,
    )

    store = _load_store()
    if store:
        # Sudah ada data — tidak perlu migrate
        return

    try:
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = chroma_client.get_or_create_collection(name="tps_docs")

        # Ambil semua metadata dari koleksi untuk hitung chunk per source
        all_items = collection.get(include=["metadatas"])
        if not all_items["metadatas"]:
            return  # ChromaDB juga kosong — tidak ada yang perlu dimigrasikan

        # Hitung jumlah chunk per source filename
        chunk_counts: dict[str, int] = {}
        for meta in all_items["metadatas"]:
            source = meta.get("source", "")
            if source:
                chunk_counts[source] = chunk_counts.get(source, 0) + 1

        documents_dir = Path(VECTOR_STORE_DIR).parent / "documents"
        for filename, count in chunk_counts.items():
            # Deteksi file_type dari ekstensi
            ext = Path(filename).suffix.lstrip(".").lower() or "txt"
            register_document(
                filename=filename,
                label=filename,  # label = filename sebagai default
                file_type=ext,
                chunk_count=count,
                is_active=True,
            )
            print(f"[migration] Terdaftar: {filename} ({count} chunk)")

    except Exception as e:
        print(f"[migration] Warning: gagal migrate dokumen lama — {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Jalankan migration saat startup
    _migrate_legacy_documents()
    yield


app = FastAPI(title="RAG Engine", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(config_router)
app.include_router(documents_router)
app.include_router(conversations_router)