"""
Chat Store — manages data/conversations.json.

Auto-bootstraps as [] if the file is missing (same pattern as other stores).
All mutations are atomic: load → mutate → save.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONVERSATIONS_PATH = DATA_DIR / "conversations.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> list[dict]:
    if not CONVERSATIONS_PATH.exists():
        return []
    with open(CONVERSATIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(conversations: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONVERSATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)


def _find(conversations: list[dict], conv_id: str) -> Optional[dict]:
    for c in conversations:
        if c["id"] == conv_id:
            return c
    return None


def _summary(conv: dict) -> dict:
    """Lightweight summary — no message bodies (for sidebar list performance)."""
    return {
        "id":            conv["id"],
        "title":         conv["title"],
        "pinned":        conv.get("pinned", False),
        "created_at":    conv["created_at"],
        "updated_at":    conv["updated_at"],
        "message_count": len(conv.get("messages", [])),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_conversations() -> list[dict]:
    """Return summaries sorted pinned-first, then by updated_at descending."""
    convs = _load()
    summaries = [_summary(c) for c in convs]
    summaries.sort(key=lambda s: (not s["pinned"], s["updated_at"]), reverse=False)
    # pinned=True sorts before pinned=False; within each group, newer first
    summaries.sort(key=lambda s: (0 if s["pinned"] else 1, s["updated_at"]), reverse=False)
    summaries.sort(key=lambda s: s["updated_at"], reverse=True)
    pinned   = [s for s in summaries if s["pinned"]]
    unpinned = [s for s in summaries if not s["pinned"]]
    return pinned + unpinned


def get_conversation(conv_id: str) -> dict:
    """Return full conversation including messages. Raises KeyError if not found."""
    convs = _load()
    conv = _find(convs, conv_id)
    if conv is None:
        raise KeyError(f"Conversation '{conv_id}' tidak ditemukan")
    return conv


def create_conversation() -> dict:
    """Create a new empty conversation and persist it. Returns the full record."""
    conv = {
        "id":         f"conv_{uuid.uuid4().hex[:8]}",
        "title":      "Percakapan baru",
        "pinned":     False,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "messages":   [],
    }
    convs = _load()
    convs.append(conv)
    _save(convs)
    return conv


def append_messages(
    conv_id: str,
    user_content: str,
    assistant_content: str,
    sources: list[str] | None = None,
) -> None:
    """Append a user+assistant message pair and update updated_at.

    If this is the first message pair, auto-derive a title from the user message
    (first 40 characters, trimmed).
    """
    convs = _load()
    conv = _find(convs, conv_id)
    if conv is None:
        raise KeyError(f"Conversation '{conv_id}' tidak ditemukan")

    now = _now_iso()
    is_first = len(conv.get("messages", [])) == 0

    conv.setdefault("messages", []).append({
        "role":      "user",
        "content":   user_content,
        "timestamp": now,
    })
    conv["messages"].append({
        "role":      "assistant",
        "content":   assistant_content,
        "sources":   sources or [],
        "timestamp": now,
    })
    conv["updated_at"] = now

    if is_first:
        # Auto-title from the first user message
        conv["title"] = user_content[:40].strip() + ("…" if len(user_content) > 40 else "")

    _save(convs)


def rename_conversation(conv_id: str, new_title: str) -> dict:
    """Update the conversation title. Returns the updated summary."""
    convs = _load()
    conv = _find(convs, conv_id)
    if conv is None:
        raise KeyError(f"Conversation '{conv_id}' tidak ditemukan")
    conv["title"] = new_title.strip() or "Percakapan baru"
    conv["updated_at"] = _now_iso()
    _save(convs)
    return _summary(conv)


def toggle_pin(conv_id: str, pinned: bool) -> dict:
    """Set pinned status. Returns the updated summary."""
    convs = _load()
    conv = _find(convs, conv_id)
    if conv is None:
        raise KeyError(f"Conversation '{conv_id}' tidak ditemukan")
    conv["pinned"] = pinned
    _save(convs)
    return _summary(conv)


def delete_conversation(conv_id: str) -> None:
    """Delete a conversation by id. Raises KeyError if not found."""
    convs = _load()
    if not _find(convs, conv_id):
        raise KeyError(f"Conversation '{conv_id}' tidak ditemukan")
    _save([c for c in convs if c["id"] != conv_id])
