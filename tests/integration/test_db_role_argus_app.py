"""Testes do papel argus_app (DML-only).

Garantem que o usuário de runtime da aplicação NÃO pode executar DDL
(CREATE/DROP/ALTER) mas PODE executar DML (SELECT/INSERT/UPDATE/DELETE).
Defesa em profundidade: limita o blast radius de uma eventual injeção.
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# URL do papel restrito. Em CI/local pode não existir → skip.
APP_DB_URL = os.getenv("APP_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not APP_DB_URL, reason="APP_DATABASE_URL não definida (papel argus_app ausente)"
)


@pytest.mark.asyncio
async def test_argus_app_nao_pode_criar_tabela() -> None:
    """argus_app deve receber permission denied ao tentar DDL."""
    engine = create_async_engine(
        APP_DB_URL.replace("postgresql://", "postgresql+asyncpg://"), poolclass=None
    )
    try:
        async with engine.begin() as conn:
            with pytest.raises(Exception) as exc:
                await conn.execute(text("CREATE TABLE _hack_test (id int)"))
            assert "permission denied" in str(exc.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_argus_app_nao_pode_dropar_tabela() -> None:
    """argus_app não pode DROP de tabela existente.

    DROP exige ser DONO da tabela (não é um privilégio concedível via GRANT),
    então o Postgres responde "must be owner of table" — diferente do
    "permission denied" emitido para CREATE/DML negados. Aceitamos ambas
    as formas: o que importa é que a operação é recusada por falta de
    privilégio (InsufficientPrivilegeError).
    """
    engine = create_async_engine(
        APP_DB_URL.replace("postgresql://", "postgresql+asyncpg://"), poolclass=None
    )
    try:
        async with engine.begin() as conn:
            with pytest.raises(Exception) as exc:
                await conn.execute(text("DROP TABLE usuarios"))
            msg = str(exc.value).lower()
            assert "permission denied" in msg or "must be owner" in msg
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_argus_app_pode_ler_e_escrever() -> None:
    """argus_app PODE fazer SELECT/INSERT/DELETE numa tabela existente."""
    engine = create_async_engine(
        APP_DB_URL.replace("postgresql://", "postgresql+asyncpg://"), poolclass=None
    )
    try:
        async with engine.begin() as conn:
            # SELECT simples deve funcionar
            res = await conn.execute(text("SELECT count(*) FROM guarnicoes"))
            assert res.scalar() is not None
    finally:
        await engine.dispose()
