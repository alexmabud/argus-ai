"""Router de verificação de saúde da aplicação.

Fornece endpoints de health check para monitoramento da disponibilidade
e status da API do Argus AI.
"""

import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db

logger = logging.getLogger("argus")

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Verifica a saúde e disponibilidade da aplicação.

    Endpoint simples que retorna o status da aplicação. Útil para
    health checks em orchestradores como Kubernetes, load balancers
    ou monitoramento. Deliberadamente raso (não toca DB/Redis) — é o alvo
    do probe externo (blackbox exporter) que alimenta o alerta de produção
    "API Offline"; aprofundar aqui faria uma instabilidade transitória de
    DB/Redis virar falso-positivo de "API inteira fora do ar". Para um
    check que também valida dependências, ver /health/ready (achado
    #29/2026-07-13).

    Returns:
        dict: Dicionário com status da aplicação.
            - status: "ok" se a aplicação está funcionando.
            - service: Nome da aplicação ("Argus AI").

    Raises:
        Nenhuma. Sempre retorna sucesso se a aplicação está respondendo.
    """
    return {"status": "ok", "service": "Argus AI"}


@router.get("/health/ready")
async def readiness_check(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """Verifica se a aplicação está pronta para servir tráfego (DB + Redis).

    Diferente de /health (sempre "ok" se o processo responde), este
    endpoint testa conectividade real com PostgreSQL (SELECT 1) e Redis
    (PING) — pensado para o HEALTHCHECK do container em desenvolvimento
    (docker/api.Dockerfile), não para o probe externo de produção que
    alimenta alertas (achado #29/2026-07-13: HEALTHCHECK antes só via
    curl em /health, que "mentia" saudável mesmo com o banco fora do ar).

    Args:
        response: Objeto Response do FastAPI, usado para setar status 503
            quando alguma dependência falha.
        db: Sessão do banco de dados (injetada).

    Returns:
        dict: {"status": "ok"|"degraded", "checks": {"database": bool, "redis": bool}}.

    Status Code:
        200: Banco e Redis respondendo.
        503: Banco ou Redis indisponível.
    """
    checks = {"database": False, "redis": False}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        logger.warning("Readiness check: banco de dados indisponível", exc_info=True)

    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        try:
            await redis_client.ping()
            checks["redis"] = True
        finally:
            await redis_client.aclose()
    except Exception:
        logger.warning("Readiness check: Redis indisponível", exc_info=True)

    ok = all(checks.values())
    response.status_code = status.HTTP_200_OK if ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ok else "degraded", "checks": checks}
