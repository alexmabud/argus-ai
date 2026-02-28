"""Inicializa banco de dados para ambiente de desenvolvimento.

Cria extensões PostgreSQL necessárias e todas as tabelas do metadata
SQLAlchemy. Também aplica retry de conexão para aguardar o Postgres
ficar pronto após `docker compose up`.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401
from app.config import settings
from app.models.base import Base

logger = logging.getLogger("argus.init_db")

REQUIRED_EXTENSIONS = ("pgcrypto", "postgis", "vector", "pg_trgm", "unaccent")
MAX_RETRIES = 30
RETRY_DELAY_SECONDS = 2


def _async_database_url() -> str:
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


async def _wait_for_database(engine) -> None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Banco disponível (tentativa %d/%d)", attempt, MAX_RETRIES)
            return
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise RuntimeError("Banco não ficou disponível a tempo") from exc
            logger.warning(
                "Banco indisponível (tentativa %d/%d): %s",
                attempt,
                MAX_RETRIES,
                exc,
            )
            await asyncio.sleep(RETRY_DELAY_SECONDS)


async def init_db() -> None:
    engine = create_async_engine(_async_database_url(), echo=False)
    try:
        await _wait_for_database(engine)

        async with engine.begin() as conn:
            for extension in REQUIRED_EXTENSIONS:
                await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Banco inicializado com sucesso")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    asyncio.run(init_db())
