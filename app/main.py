"""FastAPI application factory and lifecycle management.

Creates the main FastAPI application instance with configured middleware,
routers, and lifecycle hooks. Also manages ML model initialization and
database connection lifecycle.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import AuditMiddleware, LoggingMiddleware
from app.core.rate_limit import limiter
from app.database.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Manages startup and shutdown events for the FastAPI application.
    On startup: initializes logging and ML models (future phases).
    On shutdown: disposes database engine and cleanup resources.

    Args:
        app: FastAPI application instance.

    Yields:
        None
    """
    setup_logging()
    # Startup: modelos de ML serão carregados aqui nas fases seguintes
    # from app.services.embedding_service import EmbeddingService
    # from app.services.face_service import FaceService
    # app.state.embedding_service = EmbeddingService()
    # app.state.face_service = FaceService()
    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Instantiates FastAPI with configured title, description, and version.
    Applies middleware stack (CORS, logging, audit, rate limiting) and
    includes all routers (health, API v1).

    Returns:
        Configured FastAPI application instance.
    """

    app = FastAPI(
        title="Argus AI",
        description="Sistema de apoio operacional com IA",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter

    # Middlewares (ordem importa — último adicionado executa primeiro)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    # Frontend PWA (será ativado quando o frontend existir)
    # app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    return app


app = create_app()
