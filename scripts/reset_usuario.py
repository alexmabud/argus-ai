"""Reseta usuários do banco local e cria um novo admin.

Apaga todos os registros de usuarios (hard delete local),
garante uma guarnição padrão (necessária pelo schema do banco — NOT NULL)
e cria um novo admin. Use apenas em ambiente de desenvolvimento.
"""

from __future__ import annotations

import asyncio
import secrets
import string

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registra todos os models no metadata
from app.config import settings
from app.core.security import hash_senha
from app.models.audit_log import AuditLog
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


def _async_url() -> str:
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


def _gerar_senha(tamanho: int = 12) -> str:
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


async def main() -> None:
    engine = create_async_engine(_async_url(), echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Apagar audit_logs primeiro (FK -> usuarios.id)
        await session.execute(delete(AuditLog))
        await session.flush()

        # 2. Apagar todos os usuários (hard delete)
        await session.execute(delete(Usuario))
        await session.flush()

        # 2. Garantir guarnição padrão (exigida pelo schema — NOT NULL no banco)
        result = await session.execute(select(Guarnicao).limit(1))
        guarnicao = result.scalar_one_or_none()
        if not guarnicao:
            guarnicao = Guarnicao(nome="Padrão", unidade="DEV", codigo="DEV-001")
            session.add(guarnicao)
            await session.flush()

        # 3. Criar novo admin
        matricula = "admin001"
        senha = "admin123"

        session.add(
            Usuario(
                nome="Administrador Dev",
                matricula=matricula,
                senha_hash=hash_senha(senha),
                guarnicao_id=guarnicao.id,
                is_admin=True,
            )
        )
        await session.commit()

    await engine.dispose()

    print("\n" + "=" * 40)
    print("  NOVO USUARIO CRIADO")
    print("=" * 40)
    print(f"  Matrícula : {matricula}")
    print(f"  Senha     : {senha}")
    print("  Admin     : Sim")
    print("=" * 40)
    print("  Salve essas credenciais!")
    print("=" * 40 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
