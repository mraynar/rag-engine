from fastapi import APIRouter, HTTPException, Depends

from backend.schemas.config import ConfigCreateRequest, ConfigUpdateRequest
from backend.core.auth import require_user
from backend.services.stores import (
    create_config,
    delete_config,
    list_config,
    reveal_config,
    set_active,
    update_config,
)

router = APIRouter()


@router.get("/config")
def get_all_config() -> list:
    """Public: returns masked config list (API keys are hidden with ••••••••)."""
    return list_config()


@router.post("/config", status_code=201)
def create_config_entry(request: ConfigCreateRequest, user: dict = Depends(require_user)) -> dict:
    new_entry = create_config(
        group=request.group,
        description=request.description,
        value=request.value,
        is_secret=request.is_secret,
    )
    msg = f"New candidate '{new_entry['key']}' added to group '{request.group}'."
    return {"message": msg, "entry": new_entry}


@router.put("/config/{key}")
def update_config_entry(key: str, request: ConfigUpdateRequest, user: dict = Depends(require_user)) -> dict:
    if request.description is None and request.value is None:
        raise HTTPException(
            status_code=422,
            detail="At least one field must be provided: 'description' or 'value'.",
        )
    try:
        updated = update_config(key, description=request.description, value=request.value)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"message": f"Config '{key}' updated.", "entry": updated}


@router.patch("/config/{key}/activate")
def activate_config_entry(key: str, user: dict = Depends(require_user)) -> dict:
    try:
        set_active(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"message": f"Entry '{key}' is now active in its group."}


@router.delete("/config/{key}")
def delete_config_entry(key: str, user: dict = Depends(require_user)) -> dict:
    try:
        result = delete_config(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result["promoted_key"]:
        msg = (
            f"Config '{key}' deleted. "
            f"Active entry automatically switched to: \"{result['promoted_label']}\"."
        )
    else:
        msg = f"Config '{key}' deleted."

    return {"message": msg, "promoted_key": result["promoted_key"]}


@router.get("/config/{key}/reveal")
def get_revealed_config(key: str, user: dict = Depends(require_user)) -> dict:
    """Requires authentication to reveal the real (unmasked) API key value."""
    try:
        val = reveal_config(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"value": val}


from backend.services.reset_service import reset_all_data

@router.post("/config/reset")
def reset_system_data(user: dict = Depends(require_user)) -> dict:
    try:
        reset_all_data()
        return {"message": "System data reset successfully. All categories, documents, chat histories, and ChromaDB vector indices have been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset data: {str(e)}")
