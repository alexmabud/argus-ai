"""Factory e gerenciamento do ciclo de vida da aplicação FastAPI.

Cria a instância principal da aplicação FastAPI com middlewares, routers
e hooks de ciclo de vida configurados. Também gerencia inicialização de
modelos de ML e ciclo de vida de conexões com banco de dados. Inclui
proxy reverso para storage S3/MinIO para evitar mixed-content em HTTPS.
"""

import logging
import traceback
from contextlib import asynccontextmanager

from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.config import settings
from app.core.logging_config import setup_logging
from app.core.middleware import LoggingMiddleware, SecurityHeadersMiddleware
from app.core.permissions import TenantFilter
from app.core.rate_limit import limiter
from app.database.session import engine, get_db
from app.dependencies import get_current_user
from app.models.foto import Foto
from app.models.ocorrencia import Ocorrencia
from app.models.usuario import Usuario
from app.services.storage_service import StorageService

logger = logging.getLogger("argus")

#: Tamanho de chunk usado pelo proxy ``/storage`` ao streamar do S3 para o
#: browser. 64 KB equilibra throughput (poucas iterações por foto típica
#: de 1-3 MB) e memória de pico por stream concorrente.
STORAGE_PROXY_CHUNK_SIZE = 64 * 1024


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

    # Cliente S3 singleton — reutiliza TCP/TLS entre requests.
    await StorageService.get().startup()

    yield
    # Shutdown
    await StorageService.get().shutdown()
    await engine.dispose()


def create_app() -> FastAPI:
    """Cria e configura a instância da aplicação FastAPI.

    Instancia FastAPI com título, descrição e versão configurados.
    Aplica stack de middlewares (CORS, logging, security headers, rate limiting)
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
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
    )

    # Handler 404 JSON customizado (default do FastAPI já é JSON, mas este é mais limpo)
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Retorna 404 JSON sem expor tecnologia ou path interno."""
        return JSONResponse(
            status_code=404,
            content={"detail": "Recurso não encontrado."},
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

    # Proxy autenticado para storage S3/MinIO. O bucket é privado
    # (mc anonymous set none), então o backend baixa via S3 SDK com
    # credenciais e devolve ao browser. Requer JWT (header ou cookie
    # HTTPOnly) para impedir acesso público a fotos e documentos.
    @app.get("/storage/{path:path}")
    async def storage_proxy(
        path: str,
        request: Request,
        user: Usuario = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> Response:
        """Proxy autenticado para arquivos no storage S3/MinIO.

        Streama os bytes diretamente do S3 para o cliente, sem buffer
        intermediário — workers async não ficam presos esperando o
        download inteiro do backend terminar antes de devolver a resposta.

        Suporta cache via ``ETag``/``If-None-Match``: o ETag do objeto
        é repassado ao browser, e quando o cliente envia o mesmo valor
        em ``If-None-Match``, propagamos para o S3 como ``IfNoneMatch``.
        Se bater, o S3 responde 304 nativamente e poupamos a
        transferência completa.

        O ``path`` recebido tem o formato ``{bucket}/{key}`` para manter
        compatibilidade com URLs relativas já gravadas em banco
        (``/storage/argus/fotos/foo.jpg``). Apenas o bucket configurado
        em ``S3_BUCKET`` é aceito — qualquer outro bucket retorna 404
        para impedir uso do proxy como SSRF para outros buckets.

        Args:
            path: Caminho ``{bucket}/{key}`` recebido na URL.
            request: Request HTTP — usado para ler ``If-None-Match``.
            _: Usuário autenticado (JWT via header ou cookie).

        Returns:
            ``StreamingResponse`` com o conteúdo do arquivo e headers de
            cache, ou ``Response(304)`` quando o ETag do cliente bate.

        Raises:
            HTTPException: 404 se a chave não existe ou aponta para
                outro bucket; 502 em outros erros de S3.
        """
        bucket, _sep, key = path.partition("/")
        if not key or bucket != settings.S3_BUCKET:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo não encontrado",
            )

        # Tenant check seletivo: fotos vinculadas a pessoa permanecem globais
        # (BNMP, modelo de produto); midias de abordagem e PDFs de ocorrencia
        # respeitam o isolamento BPM/equipe. Assets nao registrados em banco
        # passam sem checagem (uploads legitimos ainda nao indexados).
        url_publica = f"/storage/{path}"
        foto = (
            await db.execute(
                select(Foto).where(
                    or_(Foto.arquivo_url == url_publica, Foto.thumbnail_url == url_publica)
                )
            )
        ).scalar_one_or_none()
        if foto is not None:
            if foto.pessoa_id is None:
                # Midia de abordagem: respeita tenant.
                TenantFilter.check_ownership(foto, user)
        else:
            ocorrencia = (
                await db.execute(
                    select(Ocorrencia).where(Ocorrencia.arquivo_pdf_url == url_publica)
                )
            ).scalar_one_or_none()
            if ocorrencia is not None:
                TenantFilter.check_ownership(ocorrencia, user)

        if_none_match = request.headers.get("if-none-match")

        try:
            body, content_type, etag, length = await StorageService.get().stream_with_meta(
                key, if_none_match=if_none_match
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"304", "NotModified"} or status_code == 304:
                # S3 confirmou que o ETag do cliente ainda é válido — poupa transferência.
                headers_304 = {"Cache-Control": "private, max-age=3600"}
                if if_none_match:
                    headers_304["ETag"] = if_none_match
                return Response(status_code=304, headers=headers_304)
            if code in {"NoSuchKey", "404"} or status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo não encontrado"
                ) from exc
            logger.exception("Falha ao baixar %s do storage: %s", key, code)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, detail="Erro ao acessar storage"
            ) from exc

        headers = {"Cache-Control": "private, max-age=3600"}
        if etag:
            headers["ETag"] = etag
        if length is not None:
            headers["Content-Length"] = str(length)

        async def chunks():
            """Stream do S3 com cleanup garantido em caso de desconexão."""
            try:
                async for chunk in body.iter_chunks(STORAGE_PROXY_CHUNK_SIZE):
                    yield chunk
            finally:
                close = getattr(body, "close", None)
                if close is not None:
                    result = close()
                    if hasattr(result, "__await__"):
                        await result

        return StreamingResponse(chunks(), headers=headers, media_type=content_type)

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

    # Prometheus metrics deve ser exposto ANTES do mount "/" (catch-all StaticFiles).
    # Routes registradas após mount("/") nunca são alcançadas — o StaticFiles captura tudo.
    Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        excluded_handlers=["/health", "/metrics", "/sw.js", "/storage/.*"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    # Frontend PWA — deve ser o último mount (catch-all)
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    return app


app = create_app()
