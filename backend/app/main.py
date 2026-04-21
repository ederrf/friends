"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401
from app.config import settings
from app.database import engine
from app.errors import register_error_handlers
from app.routers import (
    dashboard_router,
    friends_router,
    groups_router,
    import_router,
    integrations_router,
    interactions_router,
    interests_router,
    tags_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown events.

    Schema lifecycle e responsabilidade do Alembic. Rode `make migrate`
    apos qualquer mudanca em `app.models`.
    """
    yield

    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Error handlers (PRD 9.7) ─────────────────────────────────────
register_error_handlers(app)

# ── Routers ──────────────────────────────────────────────────────
app.include_router(friends_router)
app.include_router(groups_router)
app.include_router(interactions_router)
app.include_router(dashboard_router)
app.include_router(interests_router)
app.include_router(tags_router)
app.include_router(import_router)
app.include_router(integrations_router)


# ── Health check ─────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "app": settings.app_name}
