from pydantic import BaseModel, Field


class DocumentToggleRequest(BaseModel):
    is_active: bool = Field(
        ...,
        description="Status keaktifan dokumen manual untuk pencarian RAG",
        examples=[True],
    )
