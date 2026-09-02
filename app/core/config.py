from pathlib import Path

from google import genai

from app.services.stores import get_active_value

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"

TOP_N = 15            # raised from 3; tabular docs need more candidates
DISTANCE_THRESHOLD = 0.70  # relaxed to catch near-duplicate chunks


def get_gemini_api_key() -> str:
    return get_active_value("gemini_api_key")


def get_embedding_model() -> str:
    return get_active_value("embedding_model")


def get_generation_model() -> str:
    return get_active_value("generation_model")


import threading

_thread_local = threading.local()


def get_gemini_client() -> genai.Client:
    """Return a thread-local genai.Client, cached per API key."""
    api_key = get_gemini_api_key()

    if not hasattr(_thread_local, "client_cache"):
        _thread_local.client_cache = {}

    cache = _thread_local.client_cache
    if api_key not in cache:
        cache[api_key] = genai.Client(api_key=api_key)

    return cache[api_key]
