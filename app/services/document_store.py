import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DOCUMENTS_STORE_PATH = DATA_DIR / "documents_store.json"


def _ensure_store_exists() -> None:
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


def list_documents() -> list[dict]:
    return _load_store()


def register_document(
    filename: str,
    label: str,
    file_type: str,
    chunk_count: int,
    is_active: bool = True,
) -> dict:
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
    """Toggle is_active for one document; other documents are unaffected."""
    store = _load_store()
    entry = _find_by_filename(store, filename)
    if entry is None:
        raise KeyError(f"Document '{filename}' not found in document store")
    entry["is_active"] = is_active
    _save_store(store)
    return entry


def delete_document(filename: str) -> None:
    store = _load_store()
    new_store = [e for e in store if e["filename"] != filename]
    if len(new_store) == len(store):
        raise KeyError(f"Document '{filename}' not found in document store")
    _save_store(new_store)


def get_active_filenames() -> list[str]:
    store = _load_store()
    return [e["filename"] for e in store if e.get("is_active", False)]
