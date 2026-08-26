from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.auth import get_current_user, require_user
from app.services.access_tokens_store import (
    create_token,
    list_tokens,
    revoke_token,
    resolve_token
)
from app.services.db_chat_store import (
    find_conversation_by_category,
    create_user_conversation_with_category
)

router = APIRouter(tags=["access-tokens"])

class CreateTokenRequest(BaseModel):
    category_name: str
    label: Optional[str] = None

@router.get("/access-tokens")
def get_all_tokens(user: dict = Depends(require_user)):
    """List all deep-link access tokens for admin dashboard."""
    return list_tokens()

@router.post("/access-tokens", status_code=201)
def generate_new_token(body: CreateTokenRequest, user: dict = Depends(require_user)):
    """Generate a new secure deep-link access token for a tabular category."""
    try:
        return create_token(body.category_name, body.label)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/access-tokens/{token_id}", status_code=204)
def delete_token_by_id(token_id: str, user: dict = Depends(require_user)):
    """Revoke a deep-link access token."""
    try:
        revoke_token(token_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/access/{token}")
def resolve_access_token(token: str, user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Resolve a deep-link token and retrieve or create the associated category conversation."""
    resolved = resolve_token(token)
    if not resolved:
        raise HTTPException(status_code=404, detail="Link tidak valid atau sudah dicabut.")

    category_name = resolved["category_name"]
    user_id = user["id"] if user else None

    existing = find_conversation_by_category(user_id, category_name)
    if existing:
        conv_id = existing["id"]
    else:
        new_conv = create_user_conversation_with_category(user_id, category_name)
        conv_id = new_conv["id"]

    return {"conversation_id": conv_id, "category_name": category_name}
