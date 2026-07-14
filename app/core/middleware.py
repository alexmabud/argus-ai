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
        # X-XSS-Protection é obsoleto: o auditor de XSS legado foi removido dos
        # browsers e "1; mode=block" chegou a introduzir vulnerabilidades. O valor
        # recomendado hoje é "0" (desliga o filtro); a proteção real vem do CSP.
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self)"
        # Defense-in-depth: HSTS no app-layer (Caddy já seta em prod).
        # Só tem efeito sob HTTPS; ignorado em http://.
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Em dev liberamos http://localhost:9000 para servir fotos do MinIO
        # diretamente; em prod o storage passa pela API (mesmo origin).
        img_extra = " http://localhost:9000" if settings.DEBUG else ""
        # CSP sem 'unsafe-inline':
        # - script-src mantem 'unsafe-eval' (Alpine.js padrao usa new Function
        #   para interpretar x-data/x-show; remover exige migrar pra build
        #   sem eval do Alpine — decisão HITL em aberto, achado #30/2026-07-13).
        # - style-src precisa de 'unsafe-inline' enquanto tivermos style="..."
        #   embutido em templates (frontend/js/app.js gera HTML com style inline
        #   para animacoes). Migrar tudo pra classes CSS eh refactor maior.
        # - inline onclick foi removido em favor de data-navigate-to + delegated
        #   listener, permitindo retirar 'unsafe-inline' de script-src.
        # - CDNs (jsdelivr/tailwindcss/unpkg) e nominatim.openstreetmap removidos
        #   do header (achado #30/2026-07-13): todo o vendor JS é self-hosted em
        #   frontend/vendor/ há tempo (grep confirma zero uso real dessas origens
        #   em frontend/), e a geocodificação reversa via Nominatim roda no
        #   backend (app/services/geocoding_service.py), nunca no browser — essas
        #   origens só ampliavam a superfície de uma eventual XSS sem nenhum
        #   benefício funcional. *.tile.openstreetmap.org fica: é o Leaflet
        #   buscando tiles de mapa direto do browser (uso real, confirmado).
        # - fonts.googleapis.com/fonts.gstatic.com foram removidos junto com os
        #   CDNs acima, mas frontend/css/app.css:6 ainda faz @import de lá — o
        #   grep original só cobriu JS/HTML, não CSS. Restaurados (revisão pós-
        #   #30/2026-07-13); self-hospedar as fontes é uma opção melhor a longo
        #   prazo, mas é uma mudança maior (assets binários) fora do escopo desta
        #   correção pontual.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            f"img-src 'self' data: blob: https://*.tile.openstreetmap.org{img_extra}; "
            "connect-src 'self'"
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
