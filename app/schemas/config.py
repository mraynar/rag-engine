from typing import Optional

from pydantic import BaseModel


class ConfigCreateRequest(BaseModel):
    """Request body for POST /config — add a new candidate entry."""
    group: str
    description: str
    value: str
    is_secret: bool

class ConfigUpdateRequest(BaseModel):
    """Request body for PUT /config/{key} — patch description and/or value.
    
    Both fields are optional; at least one must be provided (enforced in the
    route handler).
    """
    description: Optional[str] = None
    value: Optional[str] = None
