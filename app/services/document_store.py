"""
Document Store — menyimpan metadata dokumen yang diupload di data/documents_store.json.

Setiap entri merepresentasikan satu dokumen yang sudah diindeks ke ChromaDB.
is_active menentukan apakah dokumen ikut dicari saat retrieval.
Ini TERPISAH dari config_store.json — tidak ada data rahasia di sini.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DOCUMENTS_STORE_PATH = DATA_DIR / "documents_store.json"


def _ensure_store_exists() -> None:
    """Buat file kosong [] jika belum ada. Tidak perlu .example — tidak ada rahasia."""
    if not DOCUMENTS_STORE_PATH.exists():
        DOCUMENTS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_store([])


def _load_store() -> list[dict]:
    _ensure_store_exists()
    with open(DOCUMENTS_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_store(store: list[dict]) -> None:
    with open(DOCUMENTS_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _find_by_filename(store: list[dict], filename: str) -> Optional[dict]:
    for entry in store:
        if entry["filename"] == filename:
            return entry
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_documents() -> list[dict]:
    """Kembalikan semua entri dokumen."""
    return _load_store()


def register_document(
    filename: str,
    label: str,
    file_type: str,
    chunk_count: int,
    is_active: bool = True,
) -> dict:
    """Tambahkan entri dokumen baru. Default is_active=True supaya langsung bisa dipakai."""
    store = _load_store()
    new_entry = {
        "filename": filename,
        "label": label,
        "file_type": file_type,
        "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "is_active": is_active,
        "chunk_count": chunk_count,
    }
    store.append(new_entry)
    _save_store(store)
    return new_entry


def toggle_active(filename: str, is_active: bool) -> dict:
    """Set is_active untuk satu dokumen secara independen (tidak mengubah dokumen lain).

    Berbeda dengan config set_active() yang mematikan semua lalu mengaktifkan satu —
    di sini setiap dokumen bisa aktif/nonaktif sendiri-sendiri (multi-select, bukan radio).
    Raises KeyError jika filename tidak ditemukan.
    """
    store = _load_store()
    entry = _find_by_filename(store, filename)
    if entry is None:
        raise KeyError(f"Dokumen '{filename}' tidak ditemukan di document store")
    entry["is_active"] = is_active
    _save_store(store)
    return entry


def delete_document(filename: str) -> None:
    """Hapus entri metadata dari store. File fisik & chunk ChromaDB dihapus di route handler."""
    store = _load_store()
    new_store = [e for e in store if e["filename"] != filename]
    if len(new_store) == len(store):
        raise KeyError(f"Dokumen '{filename}' tidak ditemukan di document store")
    _save_store(new_store)


def get_active_filenames() -> list[str]:
    """Kembalikan list filename yang is_active=True. Dipakai oleh retrieval untuk filter."""
    store = _load_store()
    return [e["filename"] for e in store if e.get("is_active", False)]
