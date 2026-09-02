from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from backend.schemas.chat import ChatRequest, ChatResponse
from backend.core.auth import get_current_user
from backend.services.db_chat_store import append_user_messages
from backend.services.rag_engine import build_prompt, generate_answer, format_user_friendly_error, retrieve_relevant_chunks

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user: Optional[dict] = Depends(get_current_user)) -> ChatResponse:
    try:
        tabular_category = request.category
        if not tabular_category:
            from backend.services.tabular.resolver import route_dataset
            route = route_dataset(request.message)
            if route.score > 0:
                tabular_category = route.dataset

        is_supabase_category = False
        if tabular_category:
            try:
                from backend.services.db import get_db_conn
                from sqlalchemy import text
                with get_db_conn() as conn:
                    res = conn.execute(
                        text("SELECT id FROM data_sources WHERE category_name = :category"),
                        {"category": tabular_category}
                    ).fetchone()
                    if res:
                        is_supabase_category = True
            except Exception as e:
                print(f"[chat] Warning: failed to check data_sources: {e}")

        if is_supabase_category:
            # Use Supabase + pandas + Gemini function calling query pipeline
            from backend.services.tabular_query import answer_tabular_question
            result = answer_tabular_question(request.message, tabular_category)
            answer = result["answer"]
            sources = result["sources"]
            debug_info = result.get("debug")
        else:
            # Fall back to ChromaDB semantic vector search pipeline
            chunks, sources = retrieve_relevant_chunks(request.message, request.category)
            if not chunks:
                answer = "Maaf, saya tidak menemukan informasi ini di dokumen."
                sources = []
            else:
                prompt = build_prompt(request.message, chunks)
                answer = generate_answer(prompt)
                sources = list(dict.fromkeys(sources))
            debug_info = None

    except Exception as err:
        print(f"[chat] Error in processing chat request: {err}")
        answer = format_user_friendly_error(err)
        sources = []
        debug_info = None

    # Persist the message only if user is logged in
    if user:
        try:
            append_user_messages(
                conv_id=request.conversation_id,
                user_id=user["id"],
                user_content=request.message,
                assistant_content=answer,
                sources=sources,
            )
        except KeyError:
            print(f"[chat] WARNING: conversation '{request.conversation_id}' not found, message not persisted")
    else:
        print(f"[chat] Guest session chat processed: conversation_id={request.conversation_id}")

    return ChatResponse(answer=answer, sources=sources, debug=debug_info)
