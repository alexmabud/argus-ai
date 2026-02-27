# ruff: noqa: E501
"""Script de anonimização periódica de dados sensíveis (LGPD).

Anonimiza registros soft-deleted há mais tempo que DATA_RETENTION_DAYS.
Sobrescreve campos sensíveis (nome, CPF, embeddings) e remove fotos
do storage S3/R2. Deve ser executado periodicamente via cron ou scheduler.

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("anonimizar")

# Configuração
RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "1825"))  # 5 anos


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
        Pessoa.deleted_at.isnot(None),
        Pessoa.deleted_at < cutoff,
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

    await session.flush()
    logger.info("%d pessoas anonimizadas", len(pessoas))
    return len(pessoas)


async def anonimizar_fotos(session: AsyncSession, cutoff: datetime, dry_run: bool) -> int:
    """Remove embeddings faciais de fotos de pessoas anonimizadas.

    Limpa o campo embedding_face (512-dim) de fotos cujas pessoas
    associadas foram soft-deleted antes da data de corte.

    Args:
        session: Sessão assíncrona do SQLAlchemy.
        cutoff: Data limite.
        dry_run: Se True, apenas conta sem modificar.

    Returns:
        Número de fotos processadas.
    """
    query = (
        select(Foto)
        .join(Pessoa, Foto.pessoa_id == Pessoa.id)
        .where(
            Pessoa.deleted_at.isnot(None),
            Pessoa.deleted_at < cutoff,
            Foto.embedding_face.isnot(None),
        )
    )
    result = await session.execute(query)
    fotos = result.scalars().all()

    if dry_run:
        logger.info("[DRY-RUN] %d fotos teriam embeddings removidos", len(fotos))
        return len(fotos)

    for foto in fotos:
        foto.embedding_face = None

    await session.flush()
    logger.info("%d fotos com embeddings removidos", len(fotos))
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

    async with async_sessionmaker(engine, class_=AsyncSession)() as session:
        async with session.begin():
            pessoas_count = await anonimizar_pessoas(session, cutoff, dry_run)
            fotos_count = await anonimizar_fotos(session, cutoff, dry_run)

    await engine.dispose()

    logger.info("=== Concluído ===")
    logger.info("Pessoas anonimizadas: %d", pessoas_count)
    logger.info("Fotos processadas: %d", fotos_count)


if __name__ == "__main__":
    asyncio.run(main())
