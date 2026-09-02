from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from backend.core.auth import get_current_user, require_user
from backend.services.db_chat_store import (
    list_user_conversations,
    get_user_conversation,
    create_user_conversation,
    rename_user_conversation,
    toggle_user_pin,
    delete_user_conversation,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])

class PatchConversationRequest(BaseModel):
    title:  Optional[str]  = None
    pinned: Optional[bool] = None

@router.get("")
def list_convs(user: Optional[dict] = Depends(get_current_user)):
    """List all conversations for the authenticated user, ordered by pinned then updated_at."""
    if not user:
        # Guests don't store private history in database
        return []
    return list_user_conversations(user["id"])

@router.post("", status_code=201)
def create_conv(user: dict = Depends(require_user)):
    """Create a new empty conversation for the authenticated user."""
    return create_user_conversation(user["id"])

@router.get("/{conv_id}")
def get_conv(conv_id: str, user: dict = Depends(require_user)):
    """Return full conversation detail including messages for the authenticated user."""
    try:
        return get_user_conversation(conv_id, user["id"])
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/{conv_id}")
def patch_conv(conv_id: str, body: PatchConversationRequest, user: dict = Depends(require_user)):
    """Update title and/or pinned status of a conversation, validating ownership."""
    try:
        if body.title is not None:
            rename_user_conversation(conv_id, user["id"], body.title)
        if body.pinned is not None:
            toggle_user_pin(conv_id, user["id"], body.pinned)
        return get_user_conversation(conv_id, user["id"])
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{conv_id}", status_code=204)
def delete_conv(conv_id: str, user: dict = Depends(require_user)):
    """Delete a conversation, validating ownership."""
    try:
        delete_user_conversation(conv_id, user["id"])
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
