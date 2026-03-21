"""Middlewares de logging, auditoria e segurança para requisições HTTP.

Intercepta todas as requisições HTTP para registrar logs de acesso,
adicionar headers de segurança (defense-in-depth) e preparar
infraestrutura para auditoria.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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
        response.headers["Permissions-Policy"] = "camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdn.tailwindcss.com "
            "https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org; "
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


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware para auditoria de requisições (placeholder para fase futura).

    Atualmente apenas passa requisição adiante. Será expandido para registrar
    detalhes de auditoria como usuário, endpoint, payload, timestamp, etc.
    """

    async def dispatch(self, request: Request, call_next):
        """Processa requisição e aguarda implementação de auditoria.

        Args:
            request: Objeto de requisição Starlette.
            call_next: Callable para passar requisição para próximo middleware.

        Returns:
            Resposta HTTP do endpoint.
        """

        response = await call_next(request)
        return response
