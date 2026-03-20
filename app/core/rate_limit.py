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
    """Extrai IP real do cliente, respeitando headers de proxy reverso.

    Lê X-Forwarded-For (primeiro IP da cadeia, que é o IP do cliente
    original) quando presente. Previne que todos os clientes atrás de
    nginx compartilhem o mesmo rate limit bucket.

    Args:
        request: Objeto Request do Starlette.

    Returns:
        Endereço IP do cliente real.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Primeiro IP é o cliente real; restante são proxies
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


#: Instância global de limiter usado em todos os endpoints.
#: Usa IP real do cliente como chave e Redis para armazenamento distribuído.
limiter = Limiter(
    key_func=_get_real_client_ip,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.REDIS_URL,
)
