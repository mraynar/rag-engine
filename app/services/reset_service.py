import shutil
from pathlib import Path
import chromadb

from app.core.config import VECTOR_STORE_DIR
from app.services.sources_store import SOURCES_STORE_PATH, _save_store as save_sources
from app.services.document_store import DOCUMENTS_STORE_PATH, _save_store as save_docs
from app.services.chat_store import CONVERSATIONS_PATH, _save as save_chats

def reset_all_data() -> None:
    # 1. Reset JSON databases to empty lists
    save_sources([])
    save_docs([])
    save_chats([])

    # 2. Delete all manually uploaded documents from data/documents/
    documents_dir = SOURCES_STORE_PATH.parent / "documents"
    if documents_dir.exists():
        for item in documents_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    # 3. Wipe ChromaDB index collection
    try:
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        try:
            chroma_client.delete_collection("tps_docs")
        except Exception:
            pass
        # Recreate a fresh empty collection
        chroma_client.get_or_create_collection("tps_docs")
    except Exception as e:
        print(f"[reset_service] Warning: failed to reset ChromaDB collection: {e}")
