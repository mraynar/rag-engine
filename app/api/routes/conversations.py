"""
Conversations API — CRUD endpoints for persistent chat conversations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.chat_store import (
    list_conversations,
    get_conversation,
    create_conversation,
    rename_conversation,
    toggle_pin,
    delete_conversation,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class PatchConversationRequest(BaseModel):
    title:  Optional[str]  = None
    pinned: Optional[bool] = None


@router.get("")
def list_convs():
    """List all conversations (summaries, pinned-first then newest-first)."""
    return list_conversations()


@router.post("", status_code=201)
def create_conv():
    """Create a new empty conversation. Returns the full conversation record."""
    return create_conversation()


@router.get("/{conv_id}")
def get_conv(conv_id: str):
    """Return full conversation detail including all messages."""
    try:
        return get_conversation(conv_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{conv_id}")
def patch_conv(conv_id: str, body: PatchConversationRequest):
    """Update title and/or pinned status of a conversation."""
    try:
        if body.title is not None:
            rename_conversation(conv_id, body.title)
        if body.pinned is not None:
            toggle_pin(conv_id, body.pinned)
        return get_conversation(conv_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{conv_id}", status_code=204)
def delete_conv(conv_id: str):
    """Delete a conversation. Returns 204 No Content."""
    try:
        delete_conversation(conv_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
