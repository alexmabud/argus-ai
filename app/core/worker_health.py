"""Métrica de liveness por instância do worker arq.

O arq só grava uma "health-check key" no Redis, compartilhada por padrão
entre todas as instâncias do worker (mesmo ``queue_name``). Com múltiplos
workers (``worker`` + ``worker-2`` em produção), isso mascara a morte de um
deles: enquanto o outro seguir vivo, a chave continua fresca. Este módulo
expõe ``argus_worker_alive{worker_id=...}`` (1 = health-check recente no
Redis, 0 = ausente/expirada) para permitir alertar por instância — cada
worker grava sua própria chave (``WORKER_ID`` em ``app/worker.py``), e este
gauge é atualizado periodicamente lendo o Redis a partir da API.
"""

import asyncio
import logging

import redis.asyncio as aioredis
from prometheus_client import Gauge

from app.config import settings

logger = logging.getLogger("argus")

#: 1 = health-check do worker está fresca no Redis; 0 = ausente/expirada.
#: multiprocess_mode="mostrecent": a api roda com PROMETHEUS_MULTIPROC_DIR
#: (múltiplos processos Gunicorn) — sem isso, o modo default ("all") somaria/
#: duplicaria a leitura por processo em vez de refletir o valor mais recente.
WORKER_ALIVE_GAUGE = Gauge(
    "argus_worker_alive",
    "1 se a health-check key do worker arq está fresca no Redis, 0 caso contrário",
    ["worker_id"],
    multiprocess_mode="mostrecent",
)


def _worker_ids() -> list[str]:
    """Lê a lista de worker_id esperados a partir de ``settings.WORKER_IDS``.

    Returns:
        Lista de IDs (ex.: ["worker-1", "worker-2"]), vazia se não configurado.
    """
    return [w.strip() for w in settings.WORKER_IDS.split(",") if w.strip()]


async def atualizar_worker_health_gauge() -> None:
    """Verifica a health-check key de cada worker esperado e atualiza o gauge.

    Falha de conexão ao Redis marca todos os workers monitorados como 0
    (não assume "vivo" na dúvida) e loga o erro — a checagem seguinte tenta
    de novo.
    """
    worker_ids = _worker_ids()
    if not worker_ids:
        return
    try:
        client: aioredis.Redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            for worker_id in worker_ids:
                existe = await client.exists(f"arq:health-check:{worker_id}")
                WORKER_ALIVE_GAUGE.labels(worker_id=worker_id).set(1 if existe else 0)
        finally:
            await client.aclose()
    except Exception:
        logger.warning("worker_health: falha ao consultar Redis, marcando workers indisponíveis")
        for worker_id in worker_ids:
            WORKER_ALIVE_GAUGE.labels(worker_id=worker_id).set(0)


async def loop_worker_health(intervalo_segundos: int = 30) -> None:
    """Loop em background que atualiza o gauge periodicamente.

    Roda até ser cancelado (via ``asyncio.CancelledError`` no shutdown do
    lifespan da aplicação).

    Args:
        intervalo_segundos: Intervalo entre checagens (padrão 30s).
    """
    while True:
        await atualizar_worker_health_gauge()
        await asyncio.sleep(intervalo_segundos)
