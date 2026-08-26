import secrets
from typing import Optional
from sqlalchemy import text
from app.services.db import get_db_conn

def create_token(category_name: str, label: Optional[str] = None) -> dict:
    """Validate that category_name exists in data_sources, generate a secure token, and store it."""
    with get_db_conn() as conn:
        with conn.begin():
            source = conn.execute(
                text("SELECT id FROM public.data_sources WHERE category_name = :category_name"),
                {"category_name": category_name}
            ).fetchone()
            
            if not source:
                raise ValueError("Kategori ini belum di-sync sebagai data tabular, token deep-link cuma bisa dibuat untuk kategori tabular")

            token_str = secrets.token_urlsafe(16)
            
            conn.execute(
                text("""
                    INSERT INTO public.access_tokens (token, category_name, label)
                    VALUES (:token, :category_name, :label)
                """),
                {"token": token_str, "category_name": category_name, "label": label}
            )
            
            row = conn.execute(
                text("SELECT id, token, category_name, label, created_at, revoked_at FROM public.access_tokens WHERE token = :token"),
                {"token": token_str}
            ).fetchone()
        
    return {
        "id": str(row[0]),
        "token": row[1],
        "category_name": row[2],
        "label": row[3],
        "created_at": row[4].isoformat() if row[4] else None,
        "revoked_at": row[5].isoformat() if row[5] else None
    }

def list_tokens() -> list[dict]:
    """Retrieve all deep-link tokens."""
    with get_db_conn() as conn:
        rows = conn.execute(
            text("""
                SELECT id, token, category_name, label, created_at, revoked_at 
                FROM public.access_tokens
                ORDER BY created_at DESC
            """)
        ).fetchall()
    
    return [
        {
            "id": str(r[0]),
            "token": r[1],
            "category_name": r[2],
            "label": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
            "revoked_at": r[5].isoformat() if r[5] else None
        }
        for r in rows
    ]

def revoke_token(token_id: str) -> None:
    """Mark an access token as revoked using soft-delete."""
    with get_db_conn() as conn:
        with conn.begin():
            exists = conn.execute(
                text("SELECT id FROM public.access_tokens WHERE id = :id"),
                {"id": token_id}
            ).fetchone()
            if not exists:
                raise KeyError(f"Token '{token_id}' not found.")
                
            conn.execute(
                text("UPDATE public.access_tokens SET revoked_at = now() WHERE id = :id"),
                {"id": token_id}
            )

def resolve_token(token: str) -> Optional[dict]:
    """Resolve an active, non-revoked token to its category details."""
    with get_db_conn() as conn:
        row = conn.execute(
            text("""
                SELECT category_name, label 
                FROM public.access_tokens 
                WHERE token = :token AND revoked_at IS NULL
            """),
            {"token": token}
        ).fetchone()
    
    if not row:
        return None
    return {
        "category_name": row[0],
        "label": row[1]
    }
