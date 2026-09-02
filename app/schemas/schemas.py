"""
Skema data Pydantic untuk request dan response API.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── Chat Schemas ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Pesan pertanyaan dari pengguna",
        examples=["Berapa total TEUS pada Januari 2023?"],
    )
    conversation_id: str = Field(
        ...,
        min_length=1,
        description="ID sesi percakapan obrolan aktif",
        examples=["conv_a1b2c3d4"],
    )
    category: Optional[str] = Field(
        default=None,
        description="Filter lingkup kategori pencarian dokumen (opsional)",
        examples=["Overview Box"],
    )


class ChatResponse(BaseModel):
    answer: str = Field(
        ...,
        description="Jawaban teks yang digenerasi oleh AI berdasarkan konteks dokumen",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Daftar nama berkas sumber dokumen yang relevan",
        examples=[["OVERVIEW_VESSEL.xlsx"]],
    )
    debug: Optional[Any] = Field(
        default=None,
        description="Debug info (dataset routing, query plan, filters) untuk collapsible panel di UI",
    )


# ── Config Schemas ────────────────────────────────────────────────────────────

class ConfigCreateRequest(BaseModel):
    """Body request POST /config."""
    group: str = Field(
        ...,
        min_length=1,
        description="Nama grup konfigurasi (contoh: gemini_api_key, azure_graph)",
        examples=["gemini_api_key"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Deskripsi atau label entri konfigurasi",
        examples=["Kunci API Gemini Cadangan"],
    )
    value: str = Field(
        ...,
        min_length=1,
        description="Nilai mentah konfigurasi",
        examples=["AIzaSyD-xxxxxxxxxxxx"],
    )
    is_secret: bool = Field(
        default=False,
        description="True jika nilai konfigurasi harus disamarkan",
    )


class ConfigUpdateRequest(BaseModel):
    """Body request PUT /config/{key}."""
    description: Optional[str] = Field(
        default=None,
        description="Deskripsi baru entri konfigurasi",
    )
    value: Optional[str] = Field(
        default=None,
        description="Nilai baru entri konfigurasi",
    )


# ── Document Schemas ──────────────────────────────────────────────────────────

class DocumentToggleRequest(BaseModel):
    is_active: bool = Field(
        ...,
        description="Status keaktifan dokumen manual untuk pencarian RAG",
        examples=[True],
    )


# ── Source Schemas ────────────────────────────────────────────────────────────

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
