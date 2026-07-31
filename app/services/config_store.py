import json
import shutil
import uuid
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONFIG_STORE_PATH = DATA_DIR / "config_store.json"
CONFIG_STORE_EXAMPLE_PATH = DATA_DIR / "config_store.json.example"

MASKED_VALUE = "••••••••"

def _ensure_store_exists() -> None:
    if not CONFIG_STORE_PATH.exists():
        if not CONFIG_STORE_EXAMPLE_PATH.exists():
            raise FileNotFoundError(
                "Neither config_store.json nor config_store.json.example was found"
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
    result = dict(entry)
    if result.get("is_secret"):
        result["value"] = MASKED_VALUE
    return result


def _find_by_key(store: list[dict], key: str) -> Optional[dict]:
    for entry in store:
        if entry["key"] == key:
            return entry
    return None


def list_config() -> list[dict]:
    store = _load_store()
    return [_mask(e) for e in store]


def create_config(
    group: str,
    description: str,
    value: str,
    is_secret: bool,
) -> dict:
    """Add a candidate entry; auto-activates if it is the first in its group."""
    store = _load_store()

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
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found in config store")

    if description is not None:
        entry["description"] = description
    if value is not None:
        entry["value"] = value

    _save_store(store)
    return _mask(entry)


def delete_config(key: str) -> dict:
    """Remove an entry; auto-promotes the next entry if the deleted one was active."""
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found in config store")

    group = entry["group"]
    group_entries = [e for e in store if e["group"] == group]

    if len(group_entries) <= 1:
        raise ValueError(
            f"Cannot delete '{key}': it is the only entry in group '{group}'. "
            f"Add another candidate before deleting this one."
        )

    was_active = entry.get("is_active", False)

    store = [e for e in store if e["key"] != key]

    promoted_key = None
    promoted_label = None
    if was_active:
        remaining = [e for e in store if e["group"] == group]
        if remaining:
            remaining[0]["is_active"] = True
            promoted_key = remaining[0]["key"]
            # prefer description; fall back to raw value
            promoted_label = remaining[0].get("description") or remaining[0]["value"]

    _save_store(store)
    return {"promoted_key": promoted_key, "promoted_label": promoted_label}


def set_active(key: str) -> None:
    """Deactivate all entries in a group, then activate this one."""
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found in config store")

    group = entry["group"]
    for e in store:
        if e["group"] == group:
            e["is_active"] = e["key"] == key

    _save_store(store)


def reveal_config(key: str) -> str:
    store = _load_store()
    entry = _find_by_key(store, key)
    if entry is None:
        raise KeyError(f"Config key '{key}' not found in config store")
    return entry["value"]


def get_active_value(group: str) -> str:
    store = _load_store()
    for entry in store:
        if entry["group"] == group and entry.get("is_active"):
            return entry["value"]
    raise RuntimeError(
        f"No active entry found in group '{group}'. "
        f"Activate a candidate via PATCH /config/{{key}}/activate."
    )
