"""
Config Agent — sesuai AGENTS.md poin 3, ini satu-satunya file yang boleh
mengubah skema config store.

Fase belajar: disimpan sebagai file JSON lokal (data/config_store.json).
File ini SENGAJA tidak ikut di-push ke git (berisi API key asli) — yang
di-push adalah data/config_store.json.example (placeholder, struktur sama).

Supaya orang lain yang pull repo (misal mentor) tidak perlu copy file
manual, saat config store pertama kali diakses dan filenya belum ada,
otomatis dibuat dari .example — lalu diisi lewat endpoint /config
(app/api/routes/config.py), bukan edit file manual.

Struktur store (list of entry objects):
  [
    {
      "key":         str  — identifier unik, bisa berupa "{group}_{uuid8}"
      "group":       str  — kategori, misal "generation_model"
      "description": str  — keterangan singkat
      "value":       str  — isi konfigurasi
      "is_secret":   bool — true → value disamarkan di API response
      "is_active":   bool — true → entry ini yang dipakai oleh sistem
    },
    ...
  ]

Setiap group boleh punya beberapa kandidat (is_active=False) dan
tepat satu yang aktif (is_active=True). Fungsi get_active_value(group)
dipakai oleh app/core/config.py.

Fase lanjut (nanti): pindah ke tabel database, tapi fungsi-fungsi di
bawah ini tetap dipakai sama seperti sekarang.
"""

import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONFIG_STORE_PATH = DATA_DIR / "config_store.json"
CONFIG_STORE_EXAMPLE_PATH = DATA_DIR / "config_store.json.example"

MASKED_VALUE = "••••••••"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_store_exists() -> None:
    """Copy .example to live file if the live file doesn't exist yet."""
    if not CONFIG_STORE_PATH.exists():
        if not CONFIG_STORE_EXAMPLE_PATH.exists():
            raise FileNotFoundError(
                "config_store.json maupun config_store.json.example tidak ditemukan"
            )
        shutil.copy(CONFIG_STORE_EXAMPLE_PATH, CONFIG_STORE_PATH)


def _load_store() -> list[dict]:
    _ensure_store_exists()
    with open(CONFIG_STORE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_store(store: list[dict]) -> None:
    with open(CONFIG_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _mask(entry: dict) -> dict:
    """Return a copy of the entry with value masked if is_secret."""
    result = dict(entry)
    if result.get("is_secret"):
        result["value"] = MASKED_VALUE
    return result


def _find_by_key(store: list[dict], key: str) -> Optional[dict]:
    for entry in store:
        if entry["key"] == key:
            return entry
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_config() -> list[dict]:
    """Return all entries.  Secret values are masked."""
    store = _load_store()
    return [_mask(e) for e in store]


def create_config(
    group: str,
    description: str,
    value: str,
    is_secret: bool,
) -> dict:
    """Add a new candidate entry to a group.

    The key is auto-generated as ``{group}_{uuid8}``.
    is_active defaults to False, unless this is the first entry in the group
    (in that case it becomes the active one automatically).
    """
    store = _load_store()

    # Check if the group already has at least one entry
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
    _save_store(store)
    return _mask(new_entry)


def update_config(
    key: str,
    description: Optional[str] = None,
    value: Optional[str] = None,
) -> dict:
    """Patch description and/or value of an existing entry by key.

    At least one of description or value must be provided.
    Returns the updated entry (masked if secret).
    Raises KeyError if the key does not exist.
    """
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' tidak ditemukan di config store")

    if description is not None:
        entry["description"] = description
    if value is not None:
        entry["value"] = value

    _save_store(store)
    return _mask(entry)


def delete_config(key: str) -> dict:
    """Remove an entry by key.

    Rules:
    - Cannot delete the last remaining entry in a group (returns ValueError).
    - If the deleted entry was active, the first remaining entry in the group
      is auto-promoted to active.

    Returns a dict with:
      - "promoted_key": key of the newly active entry, or None
      - "promoted_description": description/value of promoted entry, or None
    """
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' tidak ditemukan di config store")

    group = entry["group"]
    group_entries = [e for e in store if e["group"] == group]

    if len(group_entries) <= 1:
        raise ValueError(
            f"Tidak bisa menghapus — '{key}' adalah satu-satunya entri di "
            f"grup '{group}'. Tambahkan kandidat lain sebelum menghapus ini."
        )

    was_active = entry.get("is_active", False)

    # Remove the entry
    store = [e for e in store if e["key"] != key]

    # Auto-promote if the deleted entry was active
    promoted_key = None
    promoted_label = None
    if was_active:
        remaining = [e for e in store if e["group"] == group]
        if remaining:
            remaining[0]["is_active"] = True
            promoted_key = remaining[0]["key"]
            # Use description as label, fall back to value
            promoted_label = remaining[0].get("description") or remaining[0]["value"]

    _save_store(store)
    return {"promoted_key": promoted_key, "promoted_label": promoted_label}


def set_active(key: str) -> None:
    """Deactivate all entries in the same group, then activate this one.

    Raises KeyError if the key does not exist.
    """
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' tidak ditemukan di config store")

    group = entry["group"]
    for e in store:
        if e["group"] == group:
            e["is_active"] = e["key"] == key

    _save_store(store)


def reveal_config(key: str) -> str:
    """Return the real, unmasked value of an entry by key.

    Used by GET /config/{key}/reveal so the frontend can fetch the true value
    on demand (the regular list_config() always masks secrets).
    Raises KeyError if the key does not exist.
    """
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' tidak ditemukan di config store")
    return entry["value"]


def get_active_value(group: str) -> str:
    """Return the value of the active entry in a group.

    Raises RuntimeError if no active entry is found (prevents silent failures).
    """
    store = _load_store()
    for entry in store:
        if entry["group"] == group and entry.get("is_active"):
            return entry["value"]
    raise RuntimeError(
        f"Tidak ada entri aktif di grup '{group}'. "
        f"Aktifkan salah satu kandidat lewat endpoint PATCH /config/{{key}}/activate."
    )
