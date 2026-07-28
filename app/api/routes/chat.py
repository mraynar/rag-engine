from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_store import append_messages
from app.services.generation import build_prompt, generate_answer
from app.services.retrieval import retrieve_relevant_chunks

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    chunks, sources = retrieve_relevant_chunks(request.message)

    if not chunks:
        answer = "Maaf, saya tidak menemukan informasi ini di dokumen."
        sources = []
    else:
        prompt = build_prompt(request.message, chunks)
        answer = generate_answer(prompt)
        sources = list(dict.fromkeys(sources))

    # Persist both turns to the conversation store
    try:
        append_messages(
            conv_id=request.conversation_id,
            user_content=request.message,
            assistant_content=answer,
            sources=sources,
        )
    except KeyError:
        # conversation_id tidak ditemukan — jangan batalkan respons, cukup log
        print(f"[chat] WARNING: conversation '{request.conversation_id}' tidak ditemukan, pesan tidak disimpan")

    return ChatResponse(answer=answer, sources=sources)
