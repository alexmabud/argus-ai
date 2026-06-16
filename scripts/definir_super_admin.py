"""Marca um usuário como super-admin (dono) pela matrícula.

Bootstrap idempotente e NÃO destrutivo, seguro para produção. Rode uma vez
no deploy, logo após `alembic upgrade head`.

Uso:
    python -m scripts.definir_super_admin --matricula admin001
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registra models no metadata
from app.config import settings
from app.services.usuario_admin_service import UsuarioAdminService


def _async_url() -> str:
    """Converte a DATABASE_URL para o driver asyncpg.

    Returns:
        URL de conexão assíncrona (postgresql+asyncpg://...).
    """
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


async def main(matricula: str) -> None:
    """Marca o usuário da matrícula informada como super-admin e commita.

    Args:
        matricula: Matrícula do dono a promover a super-admin.
    """
    engine = create_async_engine(_async_url(), echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        service = UsuarioAdminService(session)
        await service.definir_super_admin(matricula)
        await session.commit()
    await engine.dispose()
    print(f"OK: '{matricula}' agora é super-admin.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Define super-admin por matrícula.")
    parser.add_argument("--matricula", required=True, help="Matrícula do dono.")
    args = parser.parse_args()
    asyncio.run(main(args.matricula))
