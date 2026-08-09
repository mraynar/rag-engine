from typing import Optional
from pydantic import BaseModel, Field


class SourceCreateRequest(BaseModel):
    category_name: str = Field(
        ...,
        min_length=1,
        description="Nama kategori sinkronisasi baru",
        examples=["Overview Box"],
    )
    onedrive_url: str = Field(
        ...,
        min_length=1,
        description="Tautan berbagi (Share URL) file OneDrive, SharePoint, atau Google Drive",
        examples=["https://pelindo-my.sharepoint.com/:x:/g/personal/..."],
    )


class SourceUpdateRequest(BaseModel):
    category_name: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Nama kategori baru",
    )
    onedrive_url: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Tautan berbagi baru",
    )
