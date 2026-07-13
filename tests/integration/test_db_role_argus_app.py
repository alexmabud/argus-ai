"""Testes do papel argus_app (DML-only).

Garantem que o usuário de runtime da aplicação NÃO pode executar DDL
(CREATE/DROP/ALTER) mas PODE executar DML (SELECT/INSERT/UPDATE/DELETE) —
exceto em ``audit_logs``, que é append-only mesmo para argus_app (achado
#05/2026-07-13). Defesa em profundidade: limita o blast radius de uma
eventual injeção.
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings

# URL do papel restrito. Em CI/local pode não existir → skip.
APP_DB_URL = os.getenv("APP_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not APP_DB_URL, reason="APP_DATABASE_URL não definida (papel argus_app ausente)"
)


@pytest.fixture
async def _revoke_audit_logs_reaplicado(setup_db):
    """Reaplica o REVOKE DELETE/UPDATE em audit_logs para argus_app.

    O fixture ``setup_db`` (conftest, autouse) faz DROP+CREATE de TODAS as
    tabelas antes de cada teste — inclusive ``audit_logs``. Quando a tabela
    renasce, ``ALTER DEFAULT PRIVILEGES FOR ROLE argus`` (create_app_role.sql,
    passo 7) concede SELECT/INSERT/UPDATE/DELETE de novo automaticamente
    (Postgres não tem "default privileges por tabela" — não sabe excluir
    audit_logs). Sem isso, os testes de append-only veriam o estado antes do
    REVOKE do script, não o estado real de produção (onde a tabela nunca é
    recriada). Depende explicitamente de ``setup_db`` para garantir a ordem.
    """
    owner_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(owner_url, poolclass=None)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("REVOKE DELETE, UPDATE ON audit_logs FROM argus_app"))
    finally:
        await engine.dispose()


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
    """argus_app PODE de fato fazer SELECT/INSERT/UPDATE/DELETE.

    Antes este teste só fazia SELECT count(*) — não provava que o DML real
    (INSERT/UPDATE/DELETE) é permitido. Agora exercita o ciclo completo em uma
    tabela existente (bpm), net-zero (insere e apaga a própria linha de teste).
    """
    engine = create_async_engine(
        APP_DB_URL.replace("postgresql://", "postgresql+asyncpg://"), poolclass=None
    )
    nome = "ARGUS_APP_DML_TEST"
    try:
        async with engine.begin() as conn:
            # SELECT
            res = await conn.execute(text("SELECT count(*) FROM bpm"))
            assert res.scalar() is not None

            # INSERT
            await conn.execute(
                text(
                    "INSERT INTO bpm (nome, ativo, criado_em, atualizado_em) "
                    "VALUES (:n, true, now(), now())"
                ),
                {"n": nome},
            )
            # UPDATE
            upd = await conn.execute(
                text("UPDATE bpm SET ativo = false WHERE nome = :n"), {"n": nome}
            )
            assert upd.rowcount == 1
            # DELETE (limpa a linha de teste — net-zero)
            dele = await conn.execute(text("DELETE FROM bpm WHERE nome = :n"), {"n": nome})
            assert dele.rowcount == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_argus_app_pode_inserir_audit_log() -> None:
    """argus_app PODE inserir em audit_logs — é assim que a API audita ações."""
    engine = create_async_engine(
        APP_DB_URL.replace("postgresql://", "postgresql+asyncpg://"), poolclass=None
    )
    try:
        async with engine.begin() as conn:
            res = await conn.execute(
                text(
                    "INSERT INTO audit_logs (acao, recurso, timestamp) "
                    "VALUES ('LOGIN', 'auth', now()) RETURNING id"
                )
            )
            assert res.scalar() is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_argus_app_nao_pode_apagar_audit_log(_revoke_audit_logs_reaplicado) -> None:
    """argus_app NÃO pode DELETE em audit_logs — trilha é append-only mesmo p/ runtime."""
    engine = create_async_engine(
        APP_DB_URL.replace("postgresql://", "postgresql+asyncpg://"), poolclass=None
    )
    try:
        async with engine.begin() as conn:
            with pytest.raises(Exception) as exc:
                await conn.execute(text("DELETE FROM audit_logs"))
            assert "permission denied" in str(exc.value).lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_argus_app_nao_pode_alterar_audit_log(_revoke_audit_logs_reaplicado) -> None:
    """argus_app NÃO pode UPDATE em audit_logs — trilha é append-only mesmo p/ runtime."""
    engine = create_async_engine(
        APP_DB_URL.replace("postgresql://", "postgresql+asyncpg://"), poolclass=None
    )
    try:
        async with engine.begin() as conn:
            with pytest.raises(Exception) as exc:
                await conn.execute(text("UPDATE audit_logs SET acao = 'FORJADO'"))
            assert "permission denied" in str(exc.value).lower()
    finally:
        await engine.dispose()
