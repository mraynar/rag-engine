import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from app.services.db import get_db_conn
from app.core.config import get_gemini_client, get_generation_model

def _now_iso() -> datetime:
    return datetime.now(timezone.utc)

def list_user_conversations(user_id: str) -> list[dict]:
    """Lists summaries of all conversations for a specific authenticated user, ordered by pinned first, then updated_at desc."""
    with get_db_conn() as conn:
        rows = conn.execute(
            text("""
                SELECT id, title, title_source, pinned, created_at, updated_at, category_name
                FROM public.conversations
                WHERE user_id = :user_id
                ORDER BY pinned DESC, updated_at DESC
            """),
            {"user_id": user_id}
        ).fetchall()
    
    return [
        {
            "id": str(r[0]),
            "title": r[1],
            "title_source": r[2],
            "pinned": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
            "updated_at": r[5].isoformat() if r[5] else None,
            "category_name": r[6]
        }
        for r in rows
    ]

def get_user_conversation(conv_id: str, user_id: str) -> dict:
    """Returns the full conversation record and all its messages for a user, checking ownership."""
    with get_db_conn() as conn:
        conv = conn.execute(
            text("""
                SELECT id, title, pinned, created_at, updated_at, title_source, category_name
                FROM public.conversations
                WHERE id = :conv_id AND user_id = :user_id
            """),
            {"conv_id": conv_id, "user_id": user_id}
        ).fetchone()

        if not conv:
            raise KeyError(f"Conversation '{conv_id}' not found or access denied.")

        messages_rows = conn.execute(
            text("""
                SELECT role, content, sources, created_at
                FROM public.messages
                WHERE conversation_id = :conv_id
                ORDER BY created_at ASC
            """),
            {"conv_id": conv_id}
        ).fetchall()

    messages = []
    for m in messages_rows:
        sources_val = m[2]
        if isinstance(sources_val, str):
            sources_val = json.loads(sources_val)
        messages.append({
            "role": m[0],
            "content": m[1],
            "sources": sources_val or [],
            "timestamp": m[3].isoformat() if m[3] else None
        })

    return {
        "id": str(conv[0]),
        "title": conv[1],
        "pinned": conv[2],
        "created_at": conv[3].isoformat() if conv[3] else None,
        "updated_at": conv[4].isoformat() if conv[4] else None,
        "title_source": conv[5],
        "category_name": conv[6],
        "messages": messages
    }

def create_user_conversation(user_id: str) -> dict:
    """Creates a new empty conversation for a user in the Supabase database."""
    conv_id = str(uuid.uuid4())
    with get_db_conn() as conn:
        with conn.begin():
            conn.execute(
                text("""
                    INSERT INTO public.conversations (id, user_id, title, title_source, pinned)
                    VALUES (:id, :user_id, 'New conversation', 'auto', false)
                """),
                {"id": conv_id, "user_id": user_id}
            )
            
            # Fetch the newly created row
            conv = conn.execute(
                text("SELECT id, title, pinned, created_at, updated_at, title_source, category_name FROM public.conversations WHERE id = :id"),
                {"id": conv_id}
            ).fetchone()
            
    return {
        "id": str(conv[0]),
        "title": conv[1],
        "pinned": conv[2],
        "created_at": conv[3].isoformat(),
        "updated_at": conv[4].isoformat(),
        "title_source": conv[5],
        "category_name": conv[6],
        "messages": []
    }

def generate_conversation_title(first_message: str) -> str:
    """Generates a short, relevant conversation title (3-8 words) based on the first message using Gemini."""
    fallback_title = first_message[:40].strip() + ("…" if len(first_message) > 40 else "")
    try:
        client = get_gemini_client()
        model = get_generation_model()
        prompt = (
            "You are a helpful assistant. Generate a short, relevant, easy-to-read conversation title "
            "in 3 to 8 words based on this user message. Respond ONLY with the title itself. "
            "Do not include any quotes, markdown formatting, or introductory phrases (e.g. do not say 'Title: ...').\n\n"
            f"User message: {first_message}"
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        title = response.text.strip().replace('"', '').replace("'", "")
        # Limit generated title size
        if len(title) > 60:
            title = title[:60] + "…"
        return title or fallback_title
    except Exception as e:
        print(f"[db_chat_store] Title generation failed: {e}. Falling back to default.")
        return fallback_title

def append_user_messages(
    conv_id: str,
    user_id: str,
    user_content: str,
    assistant_content: str,
    sources: list[str] | None = None
) -> None:
    """Appends user and assistant messages to a conversation, updating the updated_at timestamp and title if it's the first message."""
    with get_db_conn() as conn:
        with conn.begin():
            # Check ownership
            conv = conn.execute(
                text("SELECT title, title_source FROM public.conversations WHERE id = :conv_id AND user_id = :user_id"),
                {"conv_id": conv_id, "user_id": user_id}
            ).fetchone()

            if not conv:
                raise KeyError(f"Conversation '{conv_id}' not found or access denied.")

            current_title, title_source = conv

            # Count current messages to determine if this is the first interaction
            msg_count = conn.execute(
                text("SELECT count(*) FROM public.messages WHERE conversation_id = :conv_id"),
                {"conv_id": conv_id}
            ).scalar()

            is_first = (msg_count == 0)

            # Insert user message
            conn.execute(
                text("""
                    INSERT INTO public.messages (conversation_id, role, content)
                    VALUES (:conv_id, 'user', :content)
                """),
                {"conv_id": conv_id, "content": user_content}
            )

            # Insert assistant message
            conn.execute(
                text("""
                    INSERT INTO public.messages (conversation_id, role, content, sources)
                    VALUES (:conv_id, 'assistant', :content, :sources)
                """),
                {
                    "conv_id": conv_id,
                    "content": assistant_content,
                    "sources": json.dumps(sources or [])
                }
            )

            # Update conversation timestamp
            conn.execute(
                text("UPDATE public.conversations SET updated_at = now() WHERE id = :conv_id"),
                {"conv_id": conv_id}
            )

            # Generate automatic title if this is the first message and title_source is 'auto'
            if is_first and title_source == 'auto':
                new_title = generate_conversation_title(user_content)
                conn.execute(
                    text("UPDATE public.conversations SET title = :title WHERE id = :conv_id"),
                    {"title": new_title, "conv_id": conv_id}
                )

def rename_user_conversation(conv_id: str, user_id: str, new_title: str) -> dict:
    """Renames a conversation and marks title_source as 'manual' to prevent automatic overwriting."""
    with get_db_conn() as conn:
        with conn.begin():
            # Check ownership
            conv = conn.execute(
                text("SELECT id FROM public.conversations WHERE id = :conv_id AND user_id = :user_id"),
                {"conv_id": conv_id, "user_id": user_id}
            ).fetchone()

            if not conv:
                raise KeyError(f"Conversation '{conv_id}' not found or access denied.")

            conn.execute(
                text("""
                    UPDATE public.conversations
                    SET title = :title, title_source = 'manual', updated_at = now()
                    WHERE id = :conv_id
                """),
                {"title": new_title.strip() or "Untitled", "conv_id": conv_id}
            )
            
            # Fetch updated row
            updated = conn.execute(
                text("SELECT id, title, pinned, created_at, updated_at, title_source, category_name FROM public.conversations WHERE id = :conv_id"),
                {"conv_id": conv_id}
            ).fetchone()

    return {
        "id": str(updated[0]),
        "title": updated[1],
        "pinned": updated[2],
        "created_at": updated[3].isoformat(),
        "updated_at": updated[4].isoformat(),
        "title_source": updated[5],
        "category_name": updated[6]
    }

def toggle_user_pin(conv_id: str, user_id: str, pinned: bool) -> dict:
    """Pins or unpins a user's conversation."""
    with get_db_conn() as conn:
        with conn.begin():
            # Check ownership
            conv = conn.execute(
                text("SELECT id FROM public.conversations WHERE id = :conv_id AND user_id = :user_id"),
                {"conv_id": conv_id, "user_id": user_id}
            ).fetchone()

            if not conv:
                raise KeyError(f"Conversation '{conv_id}' not found or access denied.")

            conn.execute(
                text("UPDATE public.conversations SET pinned = :pinned WHERE id = :conv_id"),
                {"pinned": pinned, "conv_id": conv_id}
            )
            
            # Fetch updated row
            updated = conn.execute(
                text("SELECT id, title, pinned, created_at, updated_at, title_source, category_name FROM public.conversations WHERE id = :conv_id"),
                {"conv_id": conv_id}
            ).fetchone()

    return {
        "id": str(updated[0]),
        "title": updated[1],
        "pinned": updated[2],
        "created_at": updated[3].isoformat(),
        "updated_at": updated[4].isoformat(),
        "title_source": updated[5],
        "category_name": updated[6]
    }

def delete_user_conversation(conv_id: str, user_id: str) -> None:
    """Deletes a conversation from the database, checking ownership."""
    with get_db_conn() as conn:
        with conn.begin():
            # Check ownership
            conv = conn.execute(
                text("SELECT id FROM public.conversations WHERE id = :conv_id AND user_id = :user_id"),
                {"conv_id": conv_id, "user_id": user_id}
            ).fetchone()

            if not conv:
                raise KeyError(f"Conversation '{conv_id}' not found or access denied.")

            conn.execute(
                text("DELETE FROM public.conversations WHERE id = :conv_id"),
                {"conv_id": conv_id}
            )

def find_conversation_by_category(user_id: str, category_name: str) -> Optional[dict]:
    """Finds the most recent conversation associated with a specific user and category."""
    with get_db_conn() as conn:
        row = conn.execute(
            text("""
                SELECT id, title, pinned, created_at, updated_at, title_source, category_name
                FROM public.conversations
                WHERE user_id = :user_id AND category_name = :category_name
                ORDER BY updated_at DESC
                LIMIT 1
            """),
            {"user_id": user_id, "category_name": category_name}
        ).fetchone()
        
    if not row:
        return None
    return {
        "id": str(row[0]),
        "title": row[1],
        "pinned": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
        "updated_at": row[4].isoformat() if row[4] else None,
        "title_source": row[5],
        "category_name": row[6]
    }

def create_user_conversation_with_category(user_id: str, category_name: str) -> dict:
    """Creates a new empty conversation for a user scoped to a category."""
    conv_id = str(uuid.uuid4())
    with get_db_conn() as conn:
        with conn.begin():
            conn.execute(
                text("""
                    INSERT INTO public.conversations (id, user_id, title, title_source, pinned, category_name)
                    VALUES (:id, :user_id, 'New conversation', 'auto', false, :category_name)
                """),
                {"id": conv_id, "user_id": user_id, "category_name": category_name}
            )
            
            conv = conn.execute(
                text("SELECT id, title, pinned, created_at, updated_at, title_source, category_name FROM public.conversations WHERE id = :id"),
                {"id": conv_id}
            ).fetchone()
            
    return {
        "id": str(conv[0]),
        "title": conv[1],
        "pinned": conv[2],
        "created_at": conv[3].isoformat(),
        "updated_at": conv[4].isoformat(),
        "title_source": conv[5],
        "category_name": conv[6],
        "messages": []
    }
