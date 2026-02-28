"""Factory e gerenciamento do ciclo de vida da aplicação FastAPI.

Cria a instância principal da aplicação FastAPI com middlewares, routers
e hooks de ciclo de vida configurados. Também gerencia inicialização de
modelos de ML e ciclo de vida de conexões com banco de dados.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import AuditMiddleware, LoggingMiddleware
from app.core.rate_limit import limiter
from app.database.session import engine

logger = logging.getLogger("argus")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciador de contexto do ciclo de vida da aplicação.

    Gerencia eventos de inicialização e encerramento da aplicação FastAPI.
    Na inicialização: configura logging e carrega modelos de ML.
    No encerramento: libera engine do banco de dados e recursos.

    Args:
        app: Instância da aplicação FastAPI.

    Yields:
        None
    """

    setup_logging()
    # Startup: carregar modelos de ML
    try:
        from app.services.embedding_service import EmbeddingService

        app.state.embedding_service = EmbeddingService()
    except Exception as exc:
        logger.warning("Embedding service indisponível no startup: %s", exc)
        app.state.embedding_service = None

    # Face service é opcional — requer insightface
    try:
        from app.services.face_service import FaceService

        app.state.face_service = FaceService()
    except ImportError:
        app.state.face_service = None

    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    """Cria e configura a instância da aplicação FastAPI.

    Instancia FastAPI com título, descrição e versão configurados.
    Aplica stack de middlewares (CORS, logging, audit, rate limiting)
    e inclui todos os routers (health, API v1).

    Returns:
        Instância da aplicação FastAPI configurada.
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

    # Frontend PWA — deve ser o último mount (catch-all)
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    return app


app = create_app()
