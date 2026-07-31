from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str
    category: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []