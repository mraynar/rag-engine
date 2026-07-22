from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.generation import build_prompt, generate_answer
from app.services.retrieval import retrieve_relevant_chunks

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    chunks, sources = retrieve_relevant_chunks(request.message)

    if not chunks:
        return ChatResponse(
            answer="Maaf, saya tidak menemukan informasi ini di dokumen.",
            sources=[],
        )

    prompt = build_prompt(request.message, chunks)
    answer = generate_answer(prompt)
    return ChatResponse(answer=answer, sources=sources)
