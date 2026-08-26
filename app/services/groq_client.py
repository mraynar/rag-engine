"""
Groq client factory for narrative generation.
Uses the official `groq` Python SDK (pip install groq).

Roles:
  - Manual document path (ChromaDB): full generation via Groq
  - Tabular cloud path: used for natural language narrative wrapping
    after deterministic query planning produces a raw answer.
"""
import threading

from groq import Groq

from app.services.config_store import get_active_value

_thread_local = threading.local()


def get_groq_api_key() -> str:
    """Return the currently active Groq API key from config_store."""
    return get_active_value("groq_api_key")


def get_groq_model() -> str:
    """Return the currently active Groq generation model name from config_store."""
    try:
        return get_active_value("groq_model")
    except RuntimeError:
        return "llama-3.3-70b-versatile"


def get_groq_client() -> Groq:
    """Return a thread-local Groq client, cached per API key."""
    api_key = get_groq_api_key()

    if not hasattr(_thread_local, "groq_cache"):
        _thread_local.groq_cache = {}

    cache = _thread_local.groq_cache
    if api_key not in cache:
        cache[api_key] = Groq(api_key=api_key)

    return cache[api_key]


def groq_generate(prompt: str, system: str = "") -> str:
    """
    Call Groq API with a prompt and return the generated text.

    Args:
        prompt: The user message / full prompt string.
        system: Optional system instruction.

    Returns:
        Generated text string from Groq.
    """
    client = get_groq_client()
    model = get_groq_model()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content
