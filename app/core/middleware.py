"""Middlewares de logging e auditoria para requisições HTTP.

Intercepta todas as requisições HTTP para registrar logs de acesso
e preparar infraestrutura para auditoria (será implementada nas fases futuras).
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("argus")


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
