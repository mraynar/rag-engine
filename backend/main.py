import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.chat import router as chat_router
from backend.api.routes.config import router as config_router
from backend.api.routes.conversations import router as conversations_router
from backend.api.routes.health import router as health_router
from backend.api.routes.sources import router as sources_router
from backend.api.routes.access_tokens import router as access_tokens_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="RAG Engine", lifespan=lifespan)

# Read allowed origins dynamically from CORS_ORIGINS env var (comma-separated).
# Default: localhost:3000 only. Supported for local network and external domain access.
_raw_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _raw_cors.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(config_router)
app.include_router(conversations_router)
app.include_router(sources_router)
app.include_router(health_router)
app.include_router(access_tokens_router)