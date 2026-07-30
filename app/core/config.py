"""
Config & shared client.

API key & nama model dibaca FRESH dari config store setiap kali dibutuhkan,
sehingga perubahan via Config UI langsung efektif di request berikutnya
tanpa restart container.

Hanya genai.Client yang di-cache (keyed by API key) karena itu yang mahal
dibuat ulang. Semua konstanta lain (TOP_N, DISTANCE_THRESHOLD, path)
tidak perlu hot-reload karena tidak berubah via UI.
"""

from pathlib import Path

from google import genai

from app.services.config_store import get_active_value

# Path proyek (app/core/config.py → naik 2 level ke root rag-engine/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"

TOP_N = 15            # dinaikan dari 3 → 15 agar query tabular/CSV bisa melihat cukup banyak baris
DISTANCE_THRESHOLD = 0.70  # dilonggarkan sedikit untuk menangkap chunk yang relevan tapi tidak identik


# ---------------------------------------------------------------------------
# Live readers — dibaca fresh dari config_store.json setiap panggilan
# ---------------------------------------------------------------------------

def get_gemini_api_key() -> str:
    """Baca API key aktif dari config store. Selalu fresh, tidak di-cache."""
    return get_active_value("gemini_api_key")


def get_embedding_model() -> str:
    """Baca nama embedding model aktif dari config store."""
    return get_active_value("embedding_model")


def get_generation_model() -> str:
    """Baca nama generation model aktif dari config store."""
    return get_active_value("generation_model")


# ---------------------------------------------------------------------------
# Client cache — genai.Client di-cache per thread (thread-local)
# ---------------------------------------------------------------------------

import threading

_thread_local = threading.local()


def get_gemini_client() -> genai.Client:
    """Return a genai.Client for the currently active API key, cached per thread."""
    api_key = get_gemini_api_key()
    
    if not hasattr(_thread_local, "client_cache"):
        _thread_local.client_cache = {}
        
    cache = _thread_local.client_cache
    if api_key not in cache:
        cache[api_key] = genai.Client(api_key=api_key)
        
    return cache[api_key]
