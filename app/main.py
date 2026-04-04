"""Factory e gerenciamento do ciclo de vida da aplicação FastAPI.

Cria a instância principal da aplicação FastAPI com middlewares, routers
e hooks de ciclo de vida configurados. Também gerencia inicialização de
modelos de ML e ciclo de vida de conexões com banco de dados. Inclui
proxy reverso para storage S3/MinIO para evitar mixed-content em HTTPS.
"""

import logging
import traceback
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import AuditMiddleware, LoggingMiddleware, SecurityHeadersMiddleware
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
    # Startup rápido: serviços de IA são carregados sob demanda (lazy loading).
    app.state.embedding_service = None
    app.state.face_service = None
    # Cliente HTTP para proxy de storage (MinIO/R2).
    app.state.storage_http = httpx.AsyncClient(timeout=30.0)

    yield
    # Shutdown
    await app.state.storage_http.aclose()
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
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
    )

    # Rate limiting
    app.state.limiter = limiter

    # Handler obrigatório do SlowAPI para retornar 429 em vez de 500
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        """Retorna 429 quando rate limit é excedido."""
        return JSONResponse(
            status_code=429,
            content={"detail": "Muitas requisições. Tente novamente em alguns segundos."},
        )

    # Middlewares (ordem importa — último adicionado executa primeiro)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # Handler global para exceções não-tratadas — garante resposta JSON em vez de plain text
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Retorna JSON para qualquer exceção não-tratada, evitando plain text 500."""
        logger.error(
            "Erro interno não tratado em %s %s: %s: %s\n%s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Erro interno do servidor. Tente novamente."},
        )

    # Routers
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    # Proxy reverso para storage S3/MinIO — evita mixed-content em HTTPS.
    # Em produção o Caddy intercepta /storage/* antes de chegar aqui,
    # mas em dev (sem Caddy) o FastAPI faz o proxy.
    @app.get("/storage/{path:path}")
    async def storage_proxy(path: str, request: Request) -> Response:
        """Proxy reverso para arquivos no storage S3/MinIO.

        Repassa a requisição para o endpoint S3 configurado, permitindo
        que URLs relativas (/storage/bucket/key) funcionem em qualquer
        ambiente sem mixed-content.

        Args:
            path: Caminho do arquivo no storage (bucket/key).
            request: Request HTTP original.

        Returns:
            Response com o conteúdo do arquivo e headers preservados.
        """
        upstream_url = f"{settings.S3_ENDPOINT}/{path}"
        client: httpx.AsyncClient = request.app.state.storage_http
        upstream = await client.get(upstream_url)
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers={
                "Content-Type": upstream.headers.get("Content-Type", "application/octet-stream"),
                "Cache-Control": "public, max-age=86400",
            },
        )

    # Service Worker — nunca pode ser cacheado pelo browser HTTP.
    # O browser precisa sempre buscar a versão mais recente para detectar atualizações da PWA.
    @app.get("/sw.js")
    async def service_worker() -> Response:
        """Serve o Service Worker com headers que impedem cache HTTP.

        O SW deve ser sempre buscado do servidor para que o browser detecte
        atualizações da PWA. Cache HTTP do sw.js impede o ciclo de update.

        Returns:
            Response com o conteúdo do sw.js e Cache-Control: no-cache.
        """
        import os

        sw_path = os.path.join("frontend", "sw.js")
        with open(sw_path, encoding="utf-8") as f:
            content = f.read()
        return Response(
            content=content,
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    # Frontend PWA — deve ser o último mount (catch-all)
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    return app


app = create_app()
