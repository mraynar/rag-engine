from fastapi import APIRouter, HTTPException

from app.schemas.config import ConfigCreateRequest, ConfigUpdateRequest
from app.services.config_store import (
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
    return list_config()


@router.post("/config", status_code=201)
def create_config_entry(request: ConfigCreateRequest) -> dict:
    new_entry = create_config(
        group=request.group,
        description=request.description,
        value=request.value,
        is_secret=request.is_secret,
    )
    msg = f"New candidate '{new_entry['key']}' added to group '{request.group}'."
    return {"message": msg, "entry": new_entry}


@router.put("/config/{key}")
def update_config_entry(key: str, request: ConfigUpdateRequest) -> dict:
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
def activate_config_entry(key: str) -> dict:
    try:
        set_active(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"message": f"Entry '{key}' is now active in its group."}


@router.delete("/config/{key}")
def delete_config_entry(key: str) -> dict:
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
def get_revealed_config(key: str) -> dict:
    try:
        val = reveal_config(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"value": val}


from app.services.reset_service import reset_all_data

@router.post("/config/reset")
def reset_system_data() -> dict:
    try:
        reset_all_data()
        return {"message": "System data reset successfully. All categories, documents, chat histories, and ChromaDB vector indices have been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset data: {str(e)}")
