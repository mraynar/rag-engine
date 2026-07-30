"""
Documents API — endpoint untuk manajemen dokumen yang diupload.

Sesuai AGENTS.md: route handler tetap tipis — logic sepenuhnya di services.
POST   /documents              — upload & index dokumen baru
GET    /documents              — list semua dokumen terdaftar
PATCH  /documents/{filename}   — toggle is_active satu dokumen
DELETE /documents/{filename}   — hapus file + chunks ChromaDB + registry
"""

import chromadb
from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.core.config import VECTOR_STORE_DIR
from app.schemas.document import DocumentToggleRequest
from app.services.document_store import (
    delete_document,
    list_documents,
    register_document,
    toggle_active,
)
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])

DOCUMENTS_DIR_NAME = "documents"


def _get_documents_dir():
    """Resolve path ke data/documents/ dan pastikan ada."""
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent.parent.parent / "data" / "documents"
    base.mkdir(parents=True, exist_ok=True)
    return base


# ---------------------------------------------------------------------------
# POST /documents — upload & index
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def upload_document(
    file: UploadFile,
    label: str = Form(default=""),
) -> dict:
    """Upload dokumen baru, indeks ke ChromaDB, dan daftarkan ke document store.

    Alur tiga fase — jika salah satu fase gagal, semua perubahan fase sebelumnya
    di-rollback supaya tidak ada file/chunk yatim piatu:
      1. Simpan file ke disk   → gagal: tidak ada yang perlu dibersihkan
      2. Ingest ke ChromaDB    → gagal: hapus file yang baru disimpan
      3. Daftar ke store       → gagal: hapus file + hapus chunks dari ChromaDB

    HTTP status codes:
      - 409 jika nama file sudah ada di disk
      - 400 jika format tidak didukung atau parsing gagal
      - 500 untuk error tak terduga
    """
    from pathlib import Path

    filename = file.filename or "unknown"
    documents_dir = _get_documents_dir()
    dest_path = documents_dir / filename

    # ---- Pre-flight checks (sebelum menyentuh disk) -------------------------

    # 409 — jangan overwrite diam-diam
    if dest_path.exists():
        raise HTTPException(
            status_code=409,
            detail=(
                f"File '{filename}' sudah ada. Hapus dokumen lama terlebih dahulu "
                "sebelum mengunggah ulang."
            ),
        )

    # 400 — tolak ekstensi yang tidak didukung sebelum menyimpan ke disk
    suffix = Path(filename).suffix.lower()
    _SUPPORTED = {".txt", ".csv", ".xlsx", ".xls", ".docx", ".pdf", ".pptx", ".jpg", ".jpeg", ".png", ".webp"}
    if suffix not in _SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Format file '{suffix}' belum didukung. "
                f"Format yang didukung: .txt, .csv, .xlsx, .xls, .docx, .pdf, .pptx, .jpg, .jpeg, .png, .webp"
            ),
        )

    # ---- Fase 1: simpan file ke disk ----------------------------------------
    content = await file.read()
    dest_path.write_bytes(content)

    # ---- Fase 2: ingest ke ChromaDB -----------------------------------------
    # Jika gagal → hapus file yang baru disimpan (rollback fase 1)
    try:
        chunk_count = ingest_document(dest_path, filename)
    except ValueError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memproses dokumen: {e}",
        )

    # ---- Fase 3: daftarkan ke document store --------------------------------
    # Jika gagal → rollback fase 1 (hapus file) + rollback fase 2 (hapus chunks)
    file_type = suffix.lstrip(".")
    used_label = label.strip() if label.strip() else filename
    try:
        entry = register_document(
            filename=filename,
            label=used_label,
            file_type=file_type,
            chunk_count=chunk_count,
        )
    except Exception as e:
        # Rollback file
        dest_path.unlink(missing_ok=True)
        # Rollback ChromaDB chunks
        try:
            chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
            collection = chroma_client.get_or_create_collection(name="tps_docs")
            collection.delete(where={"source": filename})
        except Exception:
            pass  # Best-effort rollback — jangan sembunyikan error asli
        raise HTTPException(
            status_code=500,
            detail=f"Gagal mendaftarkan dokumen ke store: {e}",
        )

    return {"message": f"Dokumen '{filename}' berhasil diupload dan diindeks.", "document": entry}


# ---------------------------------------------------------------------------
# GET /documents — list semua dokumen
# ---------------------------------------------------------------------------

@router.get("")
def get_documents() -> list:
    """Kembalikan semua dokumen yang terdaftar di document store."""
    return list_documents()


# ---------------------------------------------------------------------------
# PATCH /documents/{filename} — toggle is_active
# ---------------------------------------------------------------------------

@router.patch("/{filename}")
def toggle_document_active(filename: str, request: DocumentToggleRequest) -> dict:
    """Set is_active untuk satu dokumen. Tidak mempengaruhi dokumen lain."""
    try:
        entry = toggle_active(filename, request.is_active)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    status = "diaktifkan" if request.is_active else "dinonaktifkan"
    return {"message": f"Dokumen '{filename}' berhasil {status}.", "document": entry}


# ---------------------------------------------------------------------------
# DELETE /documents/{filename} — hapus file + chunks + registry
# ---------------------------------------------------------------------------

@router.delete("/{filename}")
def delete_document_entry(filename: str) -> dict:
    """Hapus dokumen: file fisik, chunks di ChromaDB, dan entri di document store."""
    documents_dir = _get_documents_dir()
    file_path = documents_dir / filename

    # Hapus file fisik (jika masih ada)
    if file_path.exists():
        file_path.unlink()

    # Hapus chunks dari ChromaDB
    try:
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = chroma_client.get_or_create_collection(name="tps_docs")
        collection.delete(where={"source": filename})
    except Exception as e:
        # Jangan gagal total hanya karena ChromaDB error — tetap hapus registry
        pass

    # Hapus entri dari document store
    try:
        delete_document(filename)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"message": f"Dokumen '{filename}' berhasil dihapus."}
