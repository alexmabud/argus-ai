"""Configuração de rate limiting para proteção contra abuso.

Implementa rate limiting usando SlowAPI com armazenamento em Redis.
Limita requisições por endereço IP real (via X-Forwarded-For quando
atrás de proxy reverso) para proteger endpoints da API contra ataques
de força bruta e DoS.
"""

from slowapi import Limiter
from starlette.requests import Request

from app.config import settings


def _get_real_client_ip(request: Request) -> str:
    """Extrai IP real do cliente respeitando trust boundary do proxy reverso.

    So honra X-Forwarded-For quando o `request.client.host` esta em
    `settings.TRUSTED_PROXIES`. Caso contrario, retorna o `client.host`
    direto — atacante externo nao consegue inflar XFF para burlar rate
    limit em endpoints como `/auth/login` (10/min por IP).

    Args:
        request: Objeto Request do Starlette.

    Returns:
        Endereço IP do cliente real ou "unknown" se nao for possivel determinar.
    """
    client_host = request.client.host if request.client else None
    if client_host and client_host in settings.TRUSTED_PROXIES:
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
