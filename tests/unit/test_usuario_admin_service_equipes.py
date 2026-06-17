"""Testes de unidade do UsuarioAdminService — funcionalidades de equipe."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.core.security import hash_senha
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario
from app.services.usuario_admin_service import UsuarioAdminService


@pytest.fixture
async def super_admin(db_session: AsyncSession) -> Usuario:
    """Cria um super-admin (alcance global) para executar as ações nos testes.

    Args:
        db_session: Sessão assíncrona do banco de dados.

    Returns:
        Usuario com is_super_admin=True (passa em qualquer scope).
    """
    a = Usuario(
        nome="Dono",
        matricula="DONO_EQ",
        senha_hash=hash_senha("x"),
        is_super_admin=True,
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.fixture
async def outra_equipe(db_session: AsyncSession, bpm) -> Guarnicao:
    """Cria segunda equipe para testes de movimentação.

    Args:
        db_session: Sessão assíncrona do banco de dados.
        bpm: Fixture com o BPM pai para associar a equipe.

    Returns:
        Guarnicao persistida no banco com flush (sem commit).
    """
    g = Guarnicao(nome="GU 99", bpm_id=bpm.id, codigo="9BPM-GU99")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.mark.asyncio
async def test_listar_todos_retorna_todos_usuarios_ativos(db_session: AsyncSession, usuario):
    """listar_todos retorna todos os usuários ativos do sistema."""
    service = UsuarioAdminService(db_session)
    todos = await service.listar_todos()
    assert any(u.id == usuario.id for u in todos)


@pytest.mark.asyncio
async def test_listar_todos_inclui_sem_equipe(db_session: AsyncSession):
    """listar_todos inclui usuários com guarnicao_id=None."""
    sem_equipe = Usuario(
        nome="Sem Equipe",
        matricula="ZZ001",
        senha_hash=hash_senha("xxxx"),
        guarnicao_id=None,
    )
    db_session.add(sem_equipe)
    await db_session.flush()

    service = UsuarioAdminService(db_session)
    todos = await service.listar_todos()
    assert any(u.id == sem_equipe.id and u.guarnicao_id is None for u in todos)


@pytest.mark.asyncio
async def test_mover_equipe_atualiza_guarnicao_id(
    db_session: AsyncSession, usuario, outra_equipe, super_admin
):
    """mover_equipe atualiza guarnicao_id do usuário."""
    service = UsuarioAdminService(db_session)
    u = await service.mover_equipe(
        usuario_id=usuario.id,
        guarnicao_id_destino=outra_equipe.id,
        admin=super_admin,
    )
    assert u.guarnicao_id == outra_equipe.id


@pytest.mark.asyncio
async def test_mover_equipe_para_none_remove_equipe(db_session: AsyncSession, usuario, super_admin):
    """mover_equipe com destino=None remove o usuário da equipe."""
    service = UsuarioAdminService(db_session)
    u = await service.mover_equipe(
        usuario_id=usuario.id,
        guarnicao_id_destino=None,
        admin=super_admin,
    )
    assert u.guarnicao_id is None


@pytest.mark.asyncio
async def test_mover_equipe_usuario_inexistente_falha(
    db_session: AsyncSession, usuario, super_admin
):
    """mover_equipe em usuário inexistente lança NaoEncontradoError."""
    service = UsuarioAdminService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.mover_equipe(
            usuario_id=999_999,
            guarnicao_id_destino=None,
            admin=super_admin,
        )


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_id_explicito(
    db_session: AsyncSession, outra_equipe, usuario, super_admin
):
    """criar_usuario respeita guarnicao_id passado pelo caller."""
    service = UsuarioAdminService(db_session)
    novo, _ = await service.criar_usuario(
        matricula="PMNOVO", admin=super_admin, guarnicao_id=outra_equipe.id
    )
    assert novo.guarnicao_id == outra_equipe.id


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_id_none_fica_sem_equipe(
    db_session: AsyncSession, usuario, super_admin
):
    """criar_usuario com guarnicao_id=None cria usuário sem equipe."""
    service = UsuarioAdminService(db_session)
    novo, _ = await service.criar_usuario(matricula="PMSE01", admin=super_admin, guarnicao_id=None)
    assert novo.guarnicao_id is None
