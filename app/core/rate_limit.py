"""Configuração de rate limiting para proteção contra abuso.

Implementa rate limiting usando SlowAPI com armazenamento em Redis.
Limita requisições por endereço IP real (via X-Forwarded-For quando
atrás de proxy reverso) para proteger endpoints da API contra ataques
de força bruta e DoS.
"""

import logging
import socket
import time

from slowapi import Limiter
from starlette.requests import Request

from app.config import settings
from app.core.auth_cookie import ACCESS_TOKEN_COOKIE
from app.core.security import decodificar_token

logger = logging.getLogger("argus")

# TTL do cache de _proxy_hostname_ips — slowapi chama key_func de forma
# síncrona (sem await possível), então socket.gethostbyname() sem cache
# bloqueava a thread do event loop asyncio em TODO request de rota
# rate-limited (dezenas de endpoints usam _get_real_client_ip como key_func
# padrão); um DNS lento/indisponível travava a API inteira (revisão pós-#14/
# 2026-07-13). 30s é curto o bastante pro cenário que a ausência de cache
# tentava proteger (container do proxy recriado com IP novo) resolver sozinho
# na próxima janela, sem pagar o custo do lookup em toda requisição.
_PROXY_HOSTNAME_TTL_SECONDS = 30
_proxy_hostname_ips_cache: set[str] = set()
_proxy_hostname_ips_cached_at: float = 0.0


def _proxy_hostname_ips() -> set[str]:
    """Resolve `settings.TRUSTED_PROXY_HOSTNAMES` (ex.: "caddy") para IPs.

    Cacheado por `_PROXY_HOSTNAME_TTL_SECONDS` — ver comentário do módulo.

    Returns:
        Conjunto de IPs atuais dos hostnames configurados (vazio se nenhum
        configurado, ou se a resolução falhar — fail-closed, não confia).
    """
    global _proxy_hostname_ips_cache, _proxy_hostname_ips_cached_at

    now = time.monotonic()
    if now - _proxy_hostname_ips_cached_at < _PROXY_HOSTNAME_TTL_SECONDS:
        return _proxy_hostname_ips_cache

    ips: set[str] = set()
    for hostname in settings.TRUSTED_PROXY_HOSTNAMES:
        try:
            ips.add(socket.gethostbyname(hostname))
        except OSError:
            logger.warning("rate_limit: falha ao resolver proxy confiado '%s'", hostname)
    _proxy_hostname_ips_cache = ips
    _proxy_hostname_ips_cached_at = now
    return ips


def _get_real_client_ip(request: Request) -> str:
    """Extrai IP real do cliente respeitando trust boundary do proxy reverso.

    So honra X-Forwarded-For quando o `request.client.host` esta em
    `settings.TRUSTED_PROXIES` (IPs exatos) ou resolve para um IP de
    `settings.TRUSTED_PROXY_HOSTNAMES` (hostnames Docker, ex.: "caddy").
    Caso contrario, retorna o `client.host` direto — atacante externo nao
    consegue inflar XFF para burlar rate limit em endpoints como
    `/auth/login` (10/min por IP).

    Usa o ÚLTIMO IP da lista, não o primeiro (achado de revisão pós-#14/
    2026-07-13): o Caddy deste deploy (docker/Caddyfile) não declara
    `trusted_proxies`, então ele *anexa* o IP real ao X-Forwarded-For que
    recebeu em vez de substituí-lo — um atacante que envie
    `X-Forwarded-For: 1.2.3.4` diretamente ao Caddy chega à API como
    `X-Forwarded-For: 1.2.3.4, <ip real>`. Tomar o primeiro IP (convenção
    para cadeias multi-proxy onde cada hop confiável anexa) permitia ao
    atacante forjar qualquer IP e burlar o rate limit só variando o header.
    Como este deploy só tem um proxy confiável entre o cliente e a API, o
    último IP é sempre o que o Caddy observou de fato — o único valor que o
    atacante não controla.

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
            return forwarded.split(",")[-1].strip()
    return client_host or "unknown"


def _get_user_rate_limit_key(request: Request) -> str:
    """Chave de rate limit pelo usuário autenticado (claim `sub` do JWT).

    Complementa o limite por IP (achado #07/2026-07-13 — controle
    compensatório da busca facial): o limite por IP sozinho não impede um
    usuário autenticado de rotacionar IP/rede para escalar scraping
    biométrico com a mesma credencial. Decodifica o token diretamente (sem
    tocar o banco) — o dependency `get_current_user` da rota já valida a
    sessão de verdade; aqui só precisamos de uma chave estável por usuário.

    Sem token válido, cai no IP (a rota exige autenticação de qualquer
    forma — `get_current_user` rejeita antes de a lógica do endpoint rodar).

    Args:
        request: Objeto Request do Starlette.

    Returns:
        "user:{id}" quando há um JWT válido, senão o IP real do cliente.
    """
    auth_header = request.headers.get("authorization", "")
    token = (
        auth_header.removeprefix("Bearer ").strip()
        if auth_header.lower().startswith("bearer ")
        else request.cookies.get(ACCESS_TOKEN_COOKIE)
    )
    if token:
        payload = decodificar_token(token)
        if payload and payload.get("sub"):
            return f"user:{payload['sub']}"
    return _get_real_client_ip(request)


#: Instância global de limiter usado em todos os endpoints.
#: Usa IP real do cliente como chave e Redis para armazenamento distribuído.
limiter = Limiter(
    key_func=_get_real_client_ip,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.REDIS_URL,
)
