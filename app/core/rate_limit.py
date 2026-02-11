"""Configuração de rate limiting para proteção contra abuso.

Implementa rate limiting usando SlowAPI com armazenamento em Redis.
Limita requisições por endereço IP para proteger endpoints da API contra
ataques de força bruta e DoS.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

#: Instância global de limiter usado em todos os endpoints.
#: Usa endereço IP remoto como chave e Redis para armazenamento distribuído.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.REDIS_URL,
)
