"""
Modul store terpusat untuk penanganan data access_tokens, config, documents, dan sources.
"""
import json
import secrets
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from sqlalchemy import text

from app.services.db import get_db_conn

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONFIG_STORE_PATH = DATA_DIR / "config_store.json"
CONFIG_STORE_EXAMPLE_PATH = DATA_DIR / "config_store.json.example"
DOCUMENTS_STORE_PATH = DATA_DIR / "documents_store.json"
SOURCES_STORE_PATH = DATA_DIR / "sources_store.json"

MASKED_VALUE = "••••••••"


# ── Access Tokens Store ───────────────────────────────────────────────────────

def create_token(category_name: str, label: Optional[str] = None) -> dict:
    with get_db_conn() as conn:
        with conn.begin():
            source = conn.execute(
                text("SELECT id FROM public.data_sources WHERE category_name = :category_name"),
                {"category_name": category_name}
            ).fetchone()
            if not source:
                raise ValueError("Kategori ini belum di-sync sebagai data tabular, token deep-link cuma bisa dibuat untuk kategori tabular")

            token_str = secrets.token_urlsafe(16)
            conn.execute(
                text("""
                    INSERT INTO public.access_tokens (token, category_name, label)
                    VALUES (:token, :category_name, :label)
                """),
                {"token": token_str, "category_name": category_name, "label": label}
            )
            row = conn.execute(
                text("SELECT id, token, category_name, label, created_at, revoked_at FROM public.access_tokens WHERE token = :token"),
                {"token": token_str}
            ).fetchone()
        
    return {
        "id": str(row[0]),
        "token": row[1],
        "category_name": row[2],
        "label": row[3],
        "created_at": row[4].isoformat() if row[4] else None,
        "revoked_at": row[5].isoformat() if row[5] else None
    }


def list_tokens() -> list[dict]:
    with get_db_conn() as conn:
        rows = conn.execute(
            text("""
                SELECT id, token, category_name, label, created_at, revoked_at 
                FROM public.access_tokens
                ORDER BY created_at DESC
            """)
        ).fetchall()
    return [
        {
            "id": str(r[0]),
            "token": r[1],
            "category_name": r[2],
            "label": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
            "revoked_at": r[5].isoformat() if r[5] else None
        }
        for r in rows
    ]


def revoke_token(token_id: str) -> None:
    with get_db_conn() as conn:
        with conn.begin():
            exists = conn.execute(
                text("SELECT id FROM public.access_tokens WHERE id = :id"),
                {"id": token_id}
            ).fetchone()
            if not exists:
                raise KeyError(f"Token '{token_id}' not found.")
            conn.execute(
                text("UPDATE public.access_tokens SET revoked_at = now() WHERE id = :id"),
                {"id": token_id}
            )


def resolve_token(token: str) -> Optional[dict]:
    with get_db_conn() as conn:
        row = conn.execute(
            text("""
                SELECT category_name, label 
                FROM public.access_tokens 
                WHERE token = :token AND revoked_at IS NULL
            """),
            {"token": token}
        ).fetchone()
    if not row:
        return None
    return {"category_name": row[0], "label": row[1]}


# ── Config Store ──────────────────────────────────────────────────────────────

def _ensure_config_store_exists() -> None:
    if not CONFIG_STORE_PATH.exists():
        if CONFIG_STORE_EXAMPLE_PATH.exists():
            shutil.copy(CONFIG_STORE_EXAMPLE_PATH, CONFIG_STORE_PATH)


def _load_config_store() -> list[dict]:
    _ensure_config_store_exists()
    if not CONFIG_STORE_PATH.exists():
        return []
    with open(CONFIG_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_config_store(store: list[dict]) -> None:
    CONFIG_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _mask_config(entry: dict) -> dict:
    result = dict(entry)
    if result.get("is_secret"):
        result["value"] = MASKED_VALUE
    return result


def list_config() -> list[dict]:
    store = _load_config_store()
    return [_mask_config(e) for e in store]


def create_config(group: str, description: str, value: str, is_secret: bool) -> dict:
    store = _load_config_store()
    group_entries = [e for e in store if e["group"] == group]
    is_first_in_group = len(group_entries) == 0
    short_id = uuid.uuid4().hex[:8]
    new_entry = {
        "key": f"{group}_{short_id}",
        "group": group,
        "description": description,
        "value": value,
        "is_secret": is_secret,
        "is_active": is_first_in_group,
    }
    store.append(new_entry)
    _save_config_store(store)
    return _mask_config(new_entry)


def update_config(key: str, description: Optional[str] = None, value: Optional[str] = None) -> dict:
    store = _load_config_store()
    entry = next((e for e in store if e["key"] == key), None)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found")
    if description is not None:
        entry["description"] = description
    if value is not None:
        entry["value"] = value
    _save_config_store(store)
    return _mask_config(entry)


def delete_config(key: str) -> dict:
    store = _load_config_store()
    entry = next((e for e in store if e["key"] == key), None)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found")
    group = entry["group"]
    group_entries = [e for e in store if e["group"] == group]
    if len(group_entries) <= 1:
        raise ValueError(f"Cannot delete '{key}': only entry in group '{group}'")
    was_active = entry.get("is_active", False)
    store = [e for e in store if e["key"] != key]
    promoted_key, promoted_label = None, None
    if was_active:
        remaining = [e for e in store if e["group"] == group]
        if remaining:
            remaining[0]["is_active"] = True
            promoted_key = remaining[0]["key"]
            promoted_label = remaining[0].get("description") or remaining[0]["value"]
    _save_config_store(store)
    return {"promoted_key": promoted_key, "promoted_label": promoted_label}


def set_active(key: str) -> None:
    store = _load_config_store()
    entry = next((e for e in store if e["key"] == key), None)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found")
    group = entry["group"]
    for e in store:
        if e["group"] == group:
            e["is_active"] = (e["key"] == key)
    _save_config_store(store)


def reveal_config(key: str) -> str:
    store = _load_config_store()
    entry = next((e for e in store if e["key"] == key), None)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found")
    return entry["value"]


def get_active_value(group: str) -> str:
    store = _load_config_store()
    for entry in store:
        if entry["group"] == group and entry.get("is_active"):
            return entry["value"]
    raise RuntimeError(f"No active entry found in group '{group}'")


# ── Document Store ────────────────────────────────────────────────────────────

def _ensure_doc_store_exists() -> None:
    if not DOCUMENTS_STORE_PATH.exists():
        DOCUMENTS_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_doc_store([])


def _load_doc_store() -> list[dict]:
    _ensure_doc_store_exists()
    with open(DOCUMENTS_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_doc_store(store: list[dict]) -> None:
    with open(DOCUMENTS_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def list_documents() -> list[dict]:
    return _load_doc_store()


def register_document(filename: str, label: str, file_type: str, chunk_count: int, is_active: bool = True) -> dict:
    store = _load_doc_store()
    new_entry = {
        "filename": filename,
        "label": label,
        "file_type": file_type,
        "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "is_active": is_active,
        "chunk_count": chunk_count,
    }
    store.append(new_entry)
    _save_doc_store(store)
    return new_entry


def toggle_active(filename: str, is_active: bool) -> dict:
    store = _load_doc_store()
    entry = next((e for e in store if e["filename"] == filename), None)
    if entry is None:
        raise KeyError(f"Document '{filename}' not found")
    entry["is_active"] = is_active
    _save_doc_store(store)
    return entry


def delete_document(filename: str) -> None:
    store = _load_doc_store()
    new_store = [e for e in store if e["filename"] != filename]
    if len(new_store) == len(store):
        raise KeyError(f"Document '{filename}' not found")
    _save_doc_store(new_store)


def get_active_filenames() -> list[str]:
    store = _load_doc_store()
    return [e["filename"] for e in store if e.get("is_active", False)]


# ── Sources Store ─────────────────────────────────────────────────────────────

def _ensure_sources_store_exists() -> None:
    if not SOURCES_STORE_PATH.exists():
        SOURCES_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _save_sources_store([])


def _load_sources_store() -> list[dict]:
    _ensure_sources_store_exists()
    with open(SOURCES_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_sources_store(store: list[dict]) -> None:
    with open(SOURCES_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def list_sources() -> list[dict]:
    return _load_sources_store()


def get_source(id: str) -> Optional[dict]:
    store = _load_sources_store()
    return next((e for e in store if e["id"] == id), None)


def create_source(category_name: str, onedrive_url: str) -> dict:
    store = _load_sources_store()
    for entry in store:
        if entry["category_name"].lower() == category_name.lower():
            raise ValueError(f"Category '{category_name}' is already registered.")
    new_entry = {
        "id": f"src_{uuid.uuid4().hex[:8]}",
        "category_name": category_name.strip(),
        "onedrive_url": onedrive_url.strip(),
        "last_synced_at": None,
        "sync_status": "never_synced",
        "last_error": None,
        "chunk_count": 0,
        "fetch_method": None
    }
    store.append(new_entry)
    _save_sources_store(store)
    return new_entry


def update_source(id: str, category_name: Optional[str] = None, onedrive_url: Optional[str] = None) -> dict:
    store = _load_sources_store()
    found = next((e for e in store if e["id"] == id), None)
    if found is None:
        raise KeyError(f"Source ID '{id}' not found.")
    if category_name is not None:
        cname = category_name.strip()
        for entry in store:
            if entry["id"] != id and entry["category_name"].lower() == cname.lower():
                raise ValueError(f"Category '{cname}' is already registered.")
        found["category_name"] = cname
    if onedrive_url is not None:
        ourl = onedrive_url.strip()
        if found["onedrive_url"] != ourl:
            found["onedrive_url"] = ourl
            found["sync_status"] = "never_synced"
            found["last_synced_at"] = None
            found["last_error"] = None
            found["chunk_count"] = 0
    _save_sources_store(store)
    return found


def delete_source(id: str) -> None:
    store = _load_sources_store()
    new_store = [e for e in store if e["id"] != id]
    if len(new_store) == len(store):
        raise KeyError(f"Source ID '{id}' not found.")
    _save_sources_store(new_store)


def mark_synced(id: str, chunk_count: int, fetch_method: str = "graph_api") -> dict:
    store = _load_sources_store()
    found = next((e for e in store if e["id"] == id), None)
    if found is None:
        raise KeyError(f"Source ID '{id}' not found.")
    found["sync_status"] = "success"
    found["last_synced_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    found["chunk_count"] = chunk_count
    found["last_error"] = None
    found["fetch_method"] = fetch_method
    _save_sources_store(store)
    return found


def mark_failed(id: str, error_message: str) -> dict:
    store = _load_sources_store()
    found = next((e for e in store if e["id"] == id), None)
    if found is None:
        raise KeyError(f"Source ID '{id}' not found.")
    found["sync_status"] = "failed"
    found["last_error"] = error_message
    _save_sources_store(store)
    return found
