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


async def _audit_background(
    usuario_id: int,
    acao: str,
    recurso_id: int | None,
    detalhes: dict,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    """Registra uma entrada de auditoria abrindo sessão própria.

    Não usa a sessão do request — ela pode já estar fechada quando
    a BackgroundTask executar.

    Args:
        usuario_id: ID do usuário autenticado.
        acao: Código da ação ("VIEW_MIDIA" ou "DOWNLOAD_MIDIA").
        recurso_id: ID da Foto no banco (pode ser None).
        detalhes: Dicionário com asset_key e matrícula.
        ip_address: IP do cliente.
        user_agent: User-Agent do cliente.
    """
    try:
        async with AsyncSessionLocal() as db:
            audit = AuditService(db)
            await audit.log(
                usuario_id=usuario_id,
                acao=acao,
                recurso="foto",
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
        redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        async with redis:
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
) -> None:
    """Agenda auditoria de VIEW em background, de-duplicada por 10 minutos.

    Deve ser chamada apenas para visualizações de imagem em tamanho cheio
    (não thumbnails) para evitar ruído no log de auditoria.

    Args:
        background_tasks: FastAPI BackgroundTasks do request atual.
        usuario_id: ID do usuário autenticado.
        matricula: Matrícula do usuário (usada na chave de de-dupe).
        asset_key: Key do asset no MinIO.
        foto_id: ID da Foto no banco (opcional).
        ip_address: IP do cliente.
        user_agent: User-Agent do cliente.
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
