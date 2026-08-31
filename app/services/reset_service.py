import shutil
from pathlib import Path

import chromadb
from sqlalchemy import text

from app.core.config import VECTOR_STORE_DIR
from app.services.db import get_db_conn
from app.services.sources_store import SOURCES_STORE_PATH, _save_store as save_sources
from app.services.document_store import DOCUMENTS_STORE_PATH, _save_store as save_docs
from app.services.chat_store import CONVERSATIONS_PATH, _save as save_chats


def reset_all_data() -> None:
    save_sources([])
    save_docs([])
    save_chats([])

    documents_dir = SOURCES_STORE_PATH.parent / "documents"
    if documents_dir.exists():
        for item in documents_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    try:
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        try:
            chroma_client.delete_collection("tps_docs")
        except Exception:
            pass
        chroma_client.get_or_create_collection("tps_docs")
    except Exception as e:
        print(f"[reset_service] Warning: failed to reset ChromaDB collection: {e}")

    print("[reset_service] Truncating database tables: access_tokens, data_rows, data_sources, messages, conversations")
    with get_db_conn() as conn:
        with conn.begin():
            conn.execute(
                text("""
                    TRUNCATE TABLE access_tokens, data_rows, data_sources, messages, conversations
                    RESTART IDENTITY CASCADE
                """)
            )
    print("[reset_service] Database tables truncated successfully.")
