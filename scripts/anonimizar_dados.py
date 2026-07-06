# ruff: noqa: E501
"""Script de anonimização periódica de dados sensíveis (LGPD).

Anonimiza registros soft-deleted há mais tempo que DATA_RETENTION_DAYS.
Sobrescreve campos sensíveis (nome, CPF, embeddings), apaga os arquivos de
foto do storage S3/R2 e limpa as URLs/embeddings no banco. Registra os IDs
afetados (pessoa/foto) para trilha de auditoria. Deve ser executado
periodicamente via cron ou scheduler.

Uso:
    python scripts/anonimizar_dados.py [--dry-run]
"""

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models.foto import Foto
from app.models.pessoa import Pessoa
from app.services.storage_service import StorageService, normalize_storage_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("anonimizar")

# Configuração
RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "1825"))  # 5 anos

# Marcador para arquivo_url (coluna NOT NULL) após apagar o arquivo do storage.
_URL_ANONIMIZADA = "ANONIMIZADO"


def _storage_key(url: str | None) -> str | None:
    """Extrai a chave do objeto no storage a partir da URL da foto.

    Converte a URL (absoluta legada ou relativa ``/storage/bucket/key``) para a
    chave relativa ao bucket, usada por ``StorageService.delete``.

    Args:
        url: URL armazenada em ``Foto.arquivo_url``/``thumbnail_url`` ou None.

    Returns:
        Chave do objeto (ex.: ``fotos/uuid.jpg``) ou None se não derivável.
    """
    norm = normalize_storage_url(url)
    if not norm or not norm.startswith("/storage/"):
        return None
    _bucket, _sep, key = norm[len("/storage/") :].partition("/")
    return key or None


async def anonimizar_pessoas(session: AsyncSession, cutoff: datetime, dry_run: bool) -> int:
    """Anonimiza pessoas soft-deleted antes da data de corte.

    Sobrescreve nome, apelido, CPF e observações com valores
    genéricos. Remove embeddings faciais das fotos associadas.

    Args:
        session: Sessão assíncrona do SQLAlchemy.
        cutoff: Data limite — registros deletados antes serão anonimizados.
        dry_run: Se True, apenas conta sem modificar.

    Returns:
        Número de registros anonimizados.
    """
    query = select(Pessoa).where(
        Pessoa.desativado_em.isnot(None),
        Pessoa.desativado_em < cutoff,
        Pessoa.nome != "ANONIMIZADO",
    )
    result = await session.execute(query)
    pessoas = result.scalars().all()

    if dry_run:
        logger.info("[DRY-RUN] %d pessoas seriam anonimizadas", len(pessoas))
        return len(pessoas)

    for pessoa in pessoas:
        pessoa.nome = "ANONIMIZADO"
        pessoa.apelido = None
        pessoa.cpf_criptografado = None
        pessoa.cpf_hash = None
        pessoa.observacoes = None
        pessoa.data_nascimento = None
        logger.info("Pessoa %d anonimizada", pessoa.id)

    await session.flush()
    logger.info("%d pessoas anonimizadas", len(pessoas))
    return len(pessoas)


async def anonimizar_fotos(
    session: AsyncSession, cutoff: datetime, dry_run: bool, storage: "StorageService | None"
) -> int:
    """Apaga as fotos de pessoas anonimizadas do storage e limpa o banco.

    Para cada foto de pessoa soft-deleted antes da data de corte: apaga os
    arquivos (original e thumbnail) do storage S3/R2, limpa o embedding facial
    (512-dim), a thumbnail_url e marca a arquivo_url como anonimizada. Registra
    o ID de cada foto/pessoa afetada.

    Args:
        session: Sessão assíncrona do SQLAlchemy.
        cutoff: Data limite.
        dry_run: Se True, apenas conta sem modificar (não toca no storage).
        storage: Serviço de storage já inicializado (None em dry-run).

    Returns:
        Número de fotos processadas.
    """
    query = (
        select(Foto)
        .join(Pessoa, Foto.pessoa_id == Pessoa.id)
        .where(
            Pessoa.desativado_em.isnot(None),
            Pessoa.desativado_em < cutoff,
            Foto.arquivo_url != _URL_ANONIMIZADA,
        )
    )
    result = await session.execute(query)
    fotos = result.scalars().all()

    if dry_run:
        logger.info("[DRY-RUN] %d fotos seriam apagadas do storage e limpas", len(fotos))
        return len(fotos)

    assert storage is not None  # garantido pelo caller fora do dry-run
    for foto in fotos:
        for url in (foto.arquivo_url, foto.thumbnail_url):
            key = _storage_key(url)
            if not key:
                continue
            try:
                await storage.delete(key)
            except Exception:
                logger.warning("Falha ao apagar foto %d do storage (key=%s)", foto.id, key)
        foto.embedding_face = None
        foto.thumbnail_url = None
        foto.arquivo_url = _URL_ANONIMIZADA
        logger.info("Foto %d (pessoa %s) apagada do storage e limpa", foto.id, foto.pessoa_id)

    await session.flush()
    logger.info("%d fotos apagadas do storage e limpas", len(fotos))
    return len(fotos)


async def main():
    """Executa anonimização de dados sensíveis."""
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        logger.info("=== MODO DRY-RUN (sem modificações) ===")

    cutoff = datetime.now(UTC) - timedelta(days=RETENTION_DAYS)
    logger.info(
        "Retenção: %d dias. Anonimizando registros deletados antes de %s",
        RETENTION_DAYS,
        cutoff.strftime("%Y-%m-%d"),
    )

    db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)

    # Storage só é necessário quando vamos efetivamente apagar arquivos.
    storage = None if dry_run else StorageService.get()
    if storage is not None:
        await storage.startup()

    try:
        async with async_sessionmaker(engine, class_=AsyncSession)() as session:
            async with session.begin():
                pessoas_count = await anonimizar_pessoas(session, cutoff, dry_run)
                fotos_count = await anonimizar_fotos(session, cutoff, dry_run, storage)
    finally:
        if storage is not None:
            await storage.shutdown()
        await engine.dispose()

    logger.info("=== Concluído ===")
    logger.info("Pessoas anonimizadas: %d", pessoas_count)
    logger.info("Fotos processadas: %d", fotos_count)


if __name__ == "__main__":
    asyncio.run(main())
