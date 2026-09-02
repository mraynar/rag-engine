import time
from datetime import datetime, timezone
from fastapi import APIRouter
import chromadb

from backend.core.config import VECTOR_STORE_DIR, get_embedding_model, get_generation_model
from backend.services.stores import list_config

router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/health")
def get_health_status() -> dict:
    """Check the health status of the API, vector store, and active configuration."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    uptime_seconds = int(time.time() - _START_TIME)

    # 1. Check ChromaDB collection status
    chroma_status = "unavailable"
    doc_count = 0
    try:
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = chroma_client.get_or_create_collection(name="tps_docs")
        doc_count = collection.count()
        chroma_status = "connected"
    except Exception as e:
        chroma_status = f"error: {str(e)}"

    # 2. Check active AI models and Gemini API key configuration
    configs = list_config()
    active_gemini_key = any(
        c.get("group") == "gemini_api_key" and c.get("is_active") for c in configs
    )

    try:
        emb_model = get_embedding_model()
    except Exception:
        emb_model = "not_configured"

    try:
        gen_model = get_generation_model()
    except Exception:
        gen_model = "not_configured"

    is_healthy = chroma_status == "connected" and active_gemini_key

    return {
        "status": "healthy" if is_healthy else "degraded",
        "timestamp": now_iso,
        "uptime_seconds": uptime_seconds,
        "vector_store": {
            "status": chroma_status,
            "total_chunks": doc_count,
        },
        "ai_configuration": {
            "gemini_api_key_configured": active_gemini_key,
            "embedding_model": emb_model,
            "generation_model": gen_model,
        },
    }
