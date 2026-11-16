"""
UniNova Backend Application Entry Point
Initializes FastAPI, middleware, CORS allowlist, routers, and lifecycle events.
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_v1_router
from app.api.v1.endpoints.health import router as health_router
from app.common.errors import register_error_handlers
from app.core.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
logger = setup_logging(app_env=settings.APP_ENV, debug=settings.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle events (startup & shutdown)."""
    logger.info(
        "Starting %s v%s (environment: %s, debug: %s)",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
        settings.DEBUG,
    )
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


def create_application() -> FastAPI:
    """Application factory for FastAPI."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="UniNova Fashion E-Commerce Backend REST API",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    # Configure CORS allowlist
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$"
        if settings.APP_ENV != "production"
        else None,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Register standard exception handlers
    register_error_handlers(application)

    # Static uploads directory
    uploads_dir = Path("/app/uploads") if os.path.exists("/app") else Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    application.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

    # Root health endpoints (for AWS ALB / Docker container health checks)
    application.include_router(health_router)

    # Versioned API routes (/api/v1)
    application.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_application()
