from typing import Optional
from pydantic import BaseModel, Field


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