from typing import Optional
from pydantic import BaseModel


class SourceCreateRequest(BaseModel):
    category_name: str
    onedrive_url: str


class SourceUpdateRequest(BaseModel):
    category_name: Optional[str] = None
    onedrive_url: Optional[str] = None
