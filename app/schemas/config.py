from typing import Optional
from pydantic import BaseModel, Field


class ConfigCreateRequest(BaseModel):
    """Request body for POST /config — add a new candidate entry."""
    group: str = Field(
        ...,
        min_length=1,
        description="Nama grup konfigurasi (contoh: gemini_api_key, azure_graph)",
        examples=["gemini_api_key"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Deskripsi atau label untuk kandidat konfigurasi ini",
        examples=["Kunci API Gemini Cadangan"],
    )
    value: str = Field(
        ...,
        min_length=1,
        description="Nilai mentah konfigurasi (API key, JSON kredensial, dll)",
        examples=["AIzaSyD-xxxxxxxxxxxx"],
    )
    is_secret: bool = Field(
        default=False,
        description="Tentukan true jika nilai konfigurasi harus disamarkan di antarmuka",
    )


class ConfigUpdateRequest(BaseModel):
    """Request body for PUT /config/{key} — patch description and/or value."""
    description: Optional[str] = Field(
        default=None,
        description="Deskripsi baru untuk entri konfigurasi ini",
    )
    value: Optional[str] = Field(
        default=None,
        description="Nilai baru untuk entri konfigurasi ini",
    )
