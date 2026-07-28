from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []