"""Configuração de rate limiting para proteção contra abuso.

Implementa rate limiting usando SlowAPI com armazenamento em Redis.
Limita requisições por endereço IP real (via X-Forwarded-For quando
atrás de proxy reverso) para proteger endpoints da API contra ataques
de força bruta e DoS.
"""

import logging
import socket

from slowapi import Limiter
from starlette.requests import Request

from app.config import settings
from app.core.auth_cookie import ACCESS_TOKEN_COOKIE
from app.core.security import decodificar_token

logger = logging.getLogger("argus")


def _proxy_hostname_ips() -> set[str]:
    """Resolve `settings.TRUSTED_PROXY_HOSTNAMES` (ex.: "caddy") para IPs.

    Resolvido a cada chamada (sem cache) — DNS do Docker já resolve local e
    rápido, e cachear arriscaria confiar num IP obsoleto se o container do
    proxy for recriado com IP diferente na rede bridge.

    Returns:
        Conjunto de IPs atuais dos hostnames configurados (vazio se nenhum
        configurado, ou se a resolução falhar — fail-closed, não confia).
    """
    ips: set[str] = set()
    for hostname in settings.TRUSTED_PROXY_HOSTNAMES:
        try:
            ips.add(socket.gethostbyname(hostname))
        except OSError:
            logger.warning("rate_limit: falha ao resolver proxy confiado '%s'", hostname)
    return ips


def _get_real_client_ip(request: Request) -> str:
    """Extrai IP real do cliente respeitando trust boundary do proxy reverso.

    So honra X-Forwarded-For quando o `request.client.host` esta em
    `settings.TRUSTED_PROXIES` (IPs exatos) ou resolve para um IP de
    `settings.TRUSTED_PROXY_HOSTNAMES` (hostnames Docker, ex.: "caddy").
    Caso contrario, retorna o `client.host` direto — atacante externo nao
    consegue inflar XFF para burlar rate limit em endpoints como
    `/auth/login` (10/min por IP).

    Args:
        request: Objeto Request do Starlette.

    Returns:
        Endereço IP do cliente real ou "unknown" se nao for possivel determinar.
    """
    client_host = request.client.host if request.client else None
    if client_host and (
        client_host in settings.TRUSTED_PROXIES or client_host in _proxy_hostname_ips()
    ):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Primeiro IP é o cliente original; demais sao proxies da cadeia.
            return forwarded.split(",")[0].strip()
    return client_host or "unknown"


#: Instância global de limiter usado em todos os endpoints.
#: Usa IP real do cliente como chave e Redis para armazenamento distribuído.
limiter = Limiter(
    key_func=_get_real_client_ip,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.REDIS_URL,
)
