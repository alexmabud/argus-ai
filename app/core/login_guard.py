"""Proteção contra brute-force de login por IP usando Redis.

Complementa o bloqueio por conta (tentativas_falhas/bloqueado_ate do Usuario)
com um bloqueio por IP no Redis, configurável via MAX_LOGIN_ATTEMPTS e
LOGIN_BLOCK_DURATION_SECONDS. Opera de forma independente: um IP pode
ser bloqueado mesmo que as tentativas sejam contra contas diferentes.
"""

import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger("argus")

_CHAVE_PREFIXO = "login_fail"


def _chave_ip(ip: str) -> str:
    """Retorna a chave Redis para o contador de falhas do IP.

    Args:
        ip: Endereço IP do cliente.

    Returns:
        Chave no formato 'login_fail:{ip}'.
    """
    return f"{_CHAVE_PREFIXO}:{ip}"


async def _get_redis() -> aioredis.Redis | None:
    """Retorna cliente Redis ou None se indisponível.

    Returns:
        Cliente Redis assíncrono ou None em caso de erro de conexão.
    """
    try:
        client: aioredis.Redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        return client
    except Exception:
        logger.warning("login_guard: Redis indisponível, bloqueio por IP desabilitado")
        return None


async def ip_bloqueado(ip: str) -> bool:
    """Verifica se o IP está bloqueado por excesso de falhas de login.

    Args:
        ip: Endereço IP do cliente.

    Returns:
        True se o IP está bloqueado, False caso contrário ou se Redis indisponível.
    """
    redis = await _get_redis()
    if redis is None:
        # Fail-open (D-G2-1): sem Redis o bloqueio por IP some; o lockout por
        # conta no DB segue como defesa primária. Registramos em ERROR para que
        # a operação enxergue que a proteção contra brute-force por IP está
        # desativada enquanto o Redis estiver fora.
        logger.error(
            "login_guard: Redis indisponível — bloqueio por IP DESATIVADO, "
            "login permitido sem checagem de IP (%s)",
            ip,
        )
        return False
    try:
        val = await redis.get(_chave_ip(ip))
        if val is None:
            return False
        return int(val) >= settings.MAX_LOGIN_ATTEMPTS
    except Exception:
        logger.warning("login_guard: erro ao verificar bloqueio de IP %s", ip)
        return False
    finally:
        await redis.aclose()


async def registrar_falha_ip(ip: str) -> int:
    """Incrementa o contador de falhas do IP e define TTL de bloqueio.

    O TTL é reiniciado a cada falha (janela deslizante simples).
    Se Redis estiver indisponível, falha silenciosamente.

    Args:
        ip: Endereço IP do cliente.

    Returns:
        Novo valor do contador, ou 0 se Redis indisponível.
    """
    redis = await _get_redis()
    if redis is None:
        return 0
    try:
        chave = _chave_ip(ip)
        contagem = await redis.incr(chave)
        await redis.expire(chave, settings.LOGIN_BLOCK_DURATION_SECONDS)
        return int(contagem)
    except Exception:
        logger.warning("login_guard: erro ao registrar falha de IP %s", ip)
        return 0
    finally:
        await redis.aclose()


async def resetar_ip(ip: str) -> None:
    """Remove o contador de falhas do IP após login bem-sucedido.

    Args:
        ip: Endereço IP do cliente.
    """
    redis = await _get_redis()
    if redis is None:
        return
    try:
        await redis.delete(_chave_ip(ip))
    except Exception:
        logger.warning("login_guard: erro ao resetar contador de IP %s", ip)
    finally:
        await redis.aclose()
