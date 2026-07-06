"""Reseta usuários do banco local e cria um novo admin.

Apaga todos os registros de usuarios (hard delete local),
garante uma guarnição padrão (necessária pelo schema do banco — NOT NULL)
e cria um novo admin. Use apenas em ambiente de desenvolvimento.
"""

from __future__ import annotations

import asyncio
import secrets
import string
import sys

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401 — registra todos os models no metadata
from app.config import settings
from app.core.security import hash_senha
from app.models.audit_log import AuditLog
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


def _async_url() -> str:
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


def _gerar_senha(tamanho: int = 16) -> str:
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


def _guard_producao() -> None:
    """Aborta se o ambiente parece producao.

    Defesas:
    - DEBUG=False (operacao destrutiva so em dev)
    - DATABASE_URL contendo 'prod' (heuristica simples mas eficaz)
    """
    if not settings.DEBUG:
        sys.exit(
            "ERRO: este script destroi todos os usuarios. "
            "Recusando em ambiente nao-DEBUG."
        )
    if "prod" in (settings.DATABASE_URL or "").lower():
        sys.exit("ERRO: DATABASE_URL contem 'prod'. Recusando.")


def _confirmar() -> None:
    """Exige confirmação interativa explícita antes do hard delete.

    Defesa em profundidade sobre `_guard_producao`: mostra o banco alvo (com a
    senha mascarada) e só prossegue se o operador digitar 'apagar'. Bypass
    não-interativo (automação) com a flag --yes.
    """
    url = settings.DATABASE_URL or ""
    alvo = url
    if "://" in url and "@" in url:
        prefixo, _, resto = url.partition("://")
        cred, _, host = resto.partition("@")
        user = cred.split(":", 1)[0]
        alvo = f"{prefixo}://{user}:***@{host}"
    print(f"Isto vai APAGAR TODOS os usuarios e audit_logs em: {alvo}")
    if "--yes" in sys.argv:
        return
    resp = input("Digite 'apagar' para confirmar: ")
    if resp.strip().lower() != "apagar":
        sys.exit("Cancelado.")


async def main() -> None:
    _guard_producao()
    _confirmar()
    engine = create_async_engine(_async_url(), echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # 1. Apagar audit_logs primeiro (FK -> usuarios.id)
        await session.execute(delete(AuditLog))
        await session.flush()

        # 2. Apagar todos os usuários (hard delete)
        await session.execute(delete(Usuario))
        await session.flush()

        # 2. Garantir BPM e guarnição padrão (exigidos pelo schema — NOT NULL no banco)
        result_bpm = await session.execute(select(Bpm).limit(1))
        bpm = result_bpm.scalar_one_or_none()
        if not bpm:
            bpm = Bpm(nome="BPM Dev")
            session.add(bpm)
            await session.flush()

        result = await session.execute(select(Guarnicao).limit(1))
        guarnicao = result.scalar_one_or_none()
        if not guarnicao:
            guarnicao = Guarnicao(nome="Guarnição Dev", codigo="DEV-001", bpm_id=bpm.id)
            session.add(guarnicao)
            await session.flush()

        # 3. Criar novo admin com senha aleatoria (nunca hardcoded)
        matricula = "admin001"
        senha = _gerar_senha(16)

        session.add(
            Usuario(
                nome="Administrador Dev",
                matricula=matricula,
                senha_hash=hash_senha(senha),
                guarnicao_id=guarnicao.id,
                is_admin=True,
                is_super_admin=True,
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
    print("  ANOTE A SENHA AGORA — nao sera exibida novamente.")
    print("=" * 40 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
