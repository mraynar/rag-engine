"""
Config & shared client.

API key & nama model sekarang dibaca dari config store via get_active_value(),
sesuai AGENTS.md poin 4. Setiap grup config boleh punya beberapa kandidat;
yang dipakai adalah yang is_active=True di masing-masing grup.

CATATAN: gemini_client dibuat SEKALI saat startup. Kalau gemini_api_key
diubah lewat UI, server perlu di-restart supaya client pakai key baru.
"""

from pathlib import Path

from google import genai

from app.services.config_store import get_active_value

# Path proyek (app/core/config.py → naik 2 level ke root rag-engine/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"

# Read the active candidate for each config group
GEMINI_API_KEY    = get_active_value("gemini_api_key")
EMBEDDING_MODEL   = get_active_value("embedding_model")
GENERATION_MODEL  = get_active_value("generation_model")

TOP_N = 3
DISTANCE_THRESHOLD = 0.65  # hasil kalibrasi manual, lihat catatan project

# 1 client dipakai bersama oleh semua service (retrieval & generation)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
