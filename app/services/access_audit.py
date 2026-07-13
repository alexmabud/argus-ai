"""Camada 3 do watermark rastreável: auditoria de acesso e exfiltração.

Registra em background duas categorias de eventos:

- **VIEW_MIDIA**: visualização inline (proxy /storage). De-duplicado por
  ``(matrícula, asset_key)`` via Redis com TTL de 10 minutos — evita ruído
  de log para o mesmo arquivo aberto repetidamente na mesma sessão.
- **DOWNLOAD_MIDIA**: download forçado (/fotos/{id}/download). Sempre
  registrado, sem de-dupe, pois representa exfiltração intencional.

As tasks rodam em background (FastAPI ``BackgroundTasks``) e abrem sua
própria ``AsyncSessionLocal`` — a sessão do request pode já estar fechada
quando a task executar.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from app.config import settings
from app.database.session import AsyncSessionLocal
from app.services.audit_service import AuditService

if TYPE_CHECKING:
    from fastapi import BackgroundTasks

logger = logging.getLogger("argus")

#: TTL da chave de de-dupe do VIEW no Redis (10 minutos).
VIEW_DEDUP_TTL = 600

#: Pool Redis compartilhado — criado na primeira chamada (lazy).
_redis_client: aioredis.Redis | None = None


def _get_redis_client() -> aioredis.Redis:
    """Retorna o cliente Redis compartilhado, criando-o na primeira chamada.

    Usa o pool de conexões do aioredis (lazy connection). Não fecha o pool
    após cada uso — reutiliza conexões TCP entre chamadas. Thread-safe no
    contexto asyncio (event loop único).

    Returns:
        Cliente Redis configurado com ``REDIS_URL``.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def _audit_background(
    usuario_id: int,
    acao: str,
    recurso_id: int | None,
    detalhes: dict,
    ip_address: str | None,
    user_agent: str | None,
    recurso: str = "foto",
) -> None:
    """Registra uma entrada de auditoria abrindo sessão própria.

    Não usa a sessão do request — ela pode já estar fechada quando
    a BackgroundTask executar.

    Política fail-open explícita (achado #25/2026-07-13): esta função roda
    como BackgroundTask, ou seja, sempre DEPOIS da resposta HTTP já ter sido
    enviada ao cliente — uma falha aqui (DB fora do ar, etc.) não pode e não
    deve impedir o streaming do arquivo, que já aconteceu. O único efeito
    de uma falha é a ausência da linha de auditoria; ela nunca é silenciosa
    de verdade, pois cai em logger.exception (visível em log/alerta), mas
    não há retry nem bloqueio do request original.

    Args:
        usuario_id: ID do usuário autenticado.
        acao: Código da ação ("VIEW_MIDIA" ou "DOWNLOAD_MIDIA").
        recurso_id: ID do recurso no banco (pode ser None).
        detalhes: Dicionário com asset_key e matrícula.
        ip_address: IP do cliente.
        user_agent: User-Agent do cliente.
        recurso: Tipo do recurso acessado ("foto", "ocorrencia" ou "usuario"
            para avatar) — antes sempre fixo em "foto", mesmo para PDF de
            ocorrência (achado #25/2026-07-13).
    """
    try:
        async with AsyncSessionLocal() as db:
            audit = AuditService(db)
            await audit.log(
                usuario_id=usuario_id,
                acao=acao,
                recurso=recurso,
                recurso_id=recurso_id,
                detalhes=detalhes,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await db.commit()
    except Exception:
        logger.exception("Falha ao registrar audit %s para usuario %d", acao, usuario_id)


async def _dedup_view(matricula: str, asset_key: str) -> bool:
    """Verifica e registra a chave de de-dupe de VIEW no Redis.

    Usa SET NX EX para garantir atomicidade. Se Redis estiver
    indisponível, retorna True (fail-open) para não suprimir o log.

    Args:
        matricula: Matrícula do usuário.
        asset_key: Key do asset no MinIO.

    Returns:
        True se deve emitir o log (chave nova); False se já foi logado
        recentemente (dentro do TTL).
    """
    dedup_key = f"wm:view:{matricula}:{asset_key}"
    try:
        redis = _get_redis_client()
        was_set = await redis.set(dedup_key, "1", nx=True, ex=VIEW_DEDUP_TTL)
        return bool(was_set)
    except Exception:
        logger.warning("Redis indisponível para de-dupe de VIEW; emitindo log de %s", asset_key)
        return True


def log_view(
    background_tasks: BackgroundTasks,
    usuario_id: int,
    matricula: str,
    asset_key: str,
    foto_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    recurso: str = "foto",
) -> None:
    """Agenda auditoria de VIEW em background, de-duplicada por 10 minutos.

    Cobre tanto imagem com watermark quanto PDF/vídeo servidos in-line pelo
    proxy /storage (achado #25/2026-07-13 — antes só a variante com
    watermark, sempre imagem, deixava trilha).

    Args:
        background_tasks: FastAPI BackgroundTasks do request atual.
        usuario_id: ID do usuário autenticado.
        matricula: Matrícula do usuário (usada na chave de de-dupe).
        asset_key: Key do asset no MinIO.
        foto_id: ID do recurso no banco (Foto, Ocorrencia ou Usuario/avatar
            conforme `recurso`; opcional).
        ip_address: IP do cliente.
        user_agent: User-Agent do cliente.
        recurso: Tipo do recurso acessado ("foto", "ocorrencia" ou "usuario").
    """

    async def _run() -> None:
        """Executa de-dupe + audit em background."""
        should_log = await _dedup_view(matricula, asset_key)
        if not should_log:
            return
        await _audit_background(
            usuario_id=usuario_id,
            acao="VIEW_MIDIA",
            recurso_id=foto_id,
            detalhes={"asset_key": asset_key, "matricula": matricula},
            ip_address=ip_address,
            user_agent=user_agent,
            recurso=recurso,
        )

    background_tasks.add_task(_run)


def log_download(
    background_tasks: BackgroundTasks,
    usuario_id: int,
    matricula: str,
    asset_key: str,
    foto_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Agenda auditoria de DOWNLOAD em background, sempre registrada.

    Diferente do VIEW, o download é considerado exfiltração intencional
    e nunca é de-duplicado.

    Args:
        background_tasks: FastAPI BackgroundTasks do request atual.
        usuario_id: ID do usuário autenticado.
        matricula: Matrícula do usuário.
        asset_key: Key do asset no MinIO.
        foto_id: ID da Foto no banco (opcional).
        ip_address: IP do cliente.
        user_agent: User-Agent do cliente.
    """
    background_tasks.add_task(
        _audit_background,
        usuario_id=usuario_id,
        acao="DOWNLOAD_MIDIA",
        recurso_id=foto_id,
        detalhes={"asset_key": asset_key, "matricula": matricula},
        ip_address=ip_address,
        user_agent=user_agent,
    )
