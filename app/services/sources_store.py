import json
import uuid
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SOURCES_STORE_PATH = DATA_DIR / "sources_store.json"


def _ensure_store_exists() -> None:
    if not SOURCES_STORE_PATH.exists():
        SOURCES_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_store([])


def _load_store() -> list[dict]:
    _ensure_store_exists()
    with open(SOURCES_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_store(store: list[dict]) -> None:
    with open(SOURCES_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def list_sources() -> list[dict]:
    return _load_store()


def get_source(id: str) -> Optional[dict]:
    store = _load_store()
    for entry in store:
        if entry["id"] == id:
            return entry
    return None


def create_source(category_name: str, onedrive_url: str) -> dict:
    store = _load_store()

    for entry in store:
        if entry["category_name"].lower() == category_name.lower():
            raise ValueError(f"Kategori '{category_name}' sudah terdaftar.")

    new_entry = {
        "id": f"src_{uuid.uuid4().hex[:8]}",
        "category_name": category_name.strip(),
        "onedrive_url": onedrive_url.strip(),
        "last_synced_at": None,
        "sync_status": "never_synced",
        "last_error": None,
        "chunk_count": 0
    }
    store.append(new_entry)
    _save_store(store)
    return new_entry


def update_source(
    id: str,
    category_name: Optional[str] = None,
    onedrive_url: Optional[str] = None
) -> dict:
    store = _load_store()
    found = None
    for entry in store:
        if entry["id"] == id:
            found = entry
            break

    if found is None:
        raise KeyError(f"Source ID '{id}' tidak ditemukan.")

    if category_name is not None:
        category_name_stripped = category_name.strip()
        for entry in store:
            if entry["id"] != id and entry["category_name"].lower() == category_name_stripped.lower():
                raise ValueError(f"Kategori '{category_name_stripped}' sudah terdaftar.")
        found["category_name"] = category_name_stripped

    if onedrive_url is not None:
        onedrive_url_stripped = onedrive_url.strip()
        if found["onedrive_url"] != onedrive_url_stripped:
            found["onedrive_url"] = onedrive_url_stripped
            found["sync_status"] = "never_synced"
            found["last_synced_at"] = None
            found["last_error"] = None
            found["chunk_count"] = 0

    _save_store(store)
    return found


def delete_source(id: str) -> None:
    store = _load_store()
    new_store = [e for e in store if e["id"] != id]
    if len(new_store) == len(store):
        raise KeyError(f"Source ID '{id}' tidak ditemukan.")
    _save_store(new_store)


def mark_synced(id: str, chunk_count: int) -> dict:
    from datetime import datetime, timezone
    store = _load_store()
    found = None
    for entry in store:
        if entry["id"] == id:
            found = entry
            break
    if found is None:
        raise KeyError(f"Source ID '{id}' tidak ditemukan.")
    found["sync_status"] = "success"
    found["last_synced_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    found["chunk_count"] = chunk_count
    found["last_error"] = None
    _save_store(store)
    return found


def mark_failed(id: str, error_message: str) -> dict:
    store = _load_store()
    found = None
    for entry in store:
        if entry["id"] == id:
            found = entry
            break
    if found is None:
        raise KeyError(f"Source ID '{id}' tidak ditemukan.")
    found["sync_status"] = "failed"
    found["last_error"] = error_message
    _save_store(store)
    return found
