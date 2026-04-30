"""Testes de unidade do UsuarioAdminService — funcionalidades de equipe."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.core.security import hash_senha
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario
from app.services.usuario_admin_service import UsuarioAdminService


@pytest.fixture
async def outra_equipe(db_session: AsyncSession) -> Guarnicao:
    """Cria segunda equipe para testes de movimentação."""
    g = Guarnicao(nome="GU 99", unidade="9o BPM", codigo="9BPM-GU99")
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
async def test_mover_equipe_atualiza_guarnicao_id(db_session: AsyncSession, usuario, outra_equipe):
    """mover_equipe atualiza guarnicao_id do usuário."""
    service = UsuarioAdminService(db_session)
    u = await service.mover_equipe(
        usuario_id=usuario.id,
        guarnicao_id_destino=outra_equipe.id,
        admin_id=usuario.id,
    )
    assert u.guarnicao_id == outra_equipe.id


@pytest.mark.asyncio
async def test_mover_equipe_para_none_remove_equipe(db_session: AsyncSession, usuario):
    """mover_equipe com destino=None remove o usuário da equipe."""
    service = UsuarioAdminService(db_session)
    u = await service.mover_equipe(
        usuario_id=usuario.id,
        guarnicao_id_destino=None,
        admin_id=usuario.id,
    )
    assert u.guarnicao_id is None


@pytest.mark.asyncio
async def test_mover_equipe_usuario_inexistente_falha(db_session: AsyncSession, usuario):
    """mover_equipe em usuário inexistente lança NaoEncontradoError."""
    service = UsuarioAdminService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.mover_equipe(
            usuario_id=999_999,
            guarnicao_id_destino=None,
            admin_id=usuario.id,
        )


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_id_explicito(
    db_session: AsyncSession, outra_equipe, usuario
):
    """criar_usuario respeita guarnicao_id passado pelo caller."""
    service = UsuarioAdminService(db_session)
    novo, _ = await service.criar_usuario(
        matricula="PMNOVO", admin_id=usuario.id, guarnicao_id=outra_equipe.id
    )
    assert novo.guarnicao_id == outra_equipe.id


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_id_none_fica_sem_equipe(
    db_session: AsyncSession, usuario
):
    """criar_usuario com guarnicao_id=None cria usuário sem equipe."""
    service = UsuarioAdminService(db_session)
    novo, _ = await service.criar_usuario(
        matricula="PMSE01", admin_id=usuario.id, guarnicao_id=None
    )
    assert novo.guarnicao_id is None
