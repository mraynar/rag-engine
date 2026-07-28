from pydantic import BaseModel


class DocumentToggleRequest(BaseModel):
    is_active: bool
