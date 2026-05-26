"""Middlewares de logging e segurança para requisições HTTP.

Intercepta todas as requisições HTTP para registrar logs de acesso e
adicionar headers de segurança (defense-in-depth). Auditoria é feita
explicitamente em cada endpoint via AuditService — não há middleware
genérico de auditoria para evitar logs ruidosos sem contexto de recurso.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger("argus")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que adiciona headers de segurança em todas as respostas.

    Defense-in-depth: mesmo com nginx configurado, garante headers de
    segurança em ambientes de desenvolvimento e caso proxy seja removido.
    """

    async def dispatch(self, request: Request, call_next):
        """Adiciona headers de segurança à resposta HTTP.

        Args:
            request: Objeto de requisição Starlette.
            call_next: Callable para passar requisição para próximo middleware.

        Returns:
            Resposta HTTP com headers de segurança adicionados.
        """
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self)"
        # Em dev liberamos http://localhost:9000 para servir fotos do MinIO
        # diretamente; em prod o storage passa pela API (mesmo origin).
        img_extra = " http://localhost:9000" if settings.DEBUG else ""
        # CSP sem 'unsafe-inline':
        # - script-src mantem 'unsafe-eval' (Alpine.js padrao usa new Function
        #   para interpretar x-data/x-show; remover quebraria o PWA).
        # - style-src precisa de 'unsafe-inline' enquanto tivermos style="..."
        #   embutido em templates (frontend/js/app.js gera HTML com style inline
        #   para animacoes). Migrar tudo pra classes CSS eh refactor maior.
        # - inline onclick foi removido em favor de data-navigate-to + delegated
        #   listener, permitindo retirar 'unsafe-inline' de script-src.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdn.tailwindcss.com "
            "https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob: "
            f"https://*.tile.openstreetmap.org https://unpkg.com{img_extra}; "
            "connect-src 'self' "
            "https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com "
            "https://nominatim.openstreetmap.org https://fonts.googleapis.com "
            "https://fonts.gstatic.com"
        )
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requisições HTTP.

    Registra informações de cada requisição: método, path, status code e
    tempo de processamento em segundos.
    """

    async def dispatch(self, request: Request, call_next):
        """Processa requisição e registra log.

        Args:
            request: Objeto de requisição Starlette.
            call_next: Callable para passar requisição para próximo middleware.

        Returns:
            Resposta HTTP do endpoint.
        """

        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        logger.info(
            "%s %s %s %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response
