"""Testes de unidade do EquipeService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.services.equipe_service import EquipeService


@pytest.mark.asyncio
async def test_listar_equipes_retorna_todas_ativas(db_session: AsyncSession, guarnicao):
    """listar_equipes retorna todas as equipes ativas."""
    service = EquipeService(db_session)
    equipes = await service.listar_equipes()
    assert len(equipes) >= 1
    assert any(e.id == guarnicao.id for e in equipes)


@pytest.mark.asyncio
async def test_criar_equipe_gera_codigo(db_session: AsyncSession, usuario):
    """criar_equipe gera código único automaticamente."""
    service = EquipeService(db_session)
    e = await service.criar_equipe(nome="3a Cia - GU 02", unidade="3o BPM", admin_id=usuario.id)
    assert e.id is not None
    assert e.codigo
    assert e.nome == "3a Cia - GU 02"
    assert e.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_criar_equipe_nome_duplicado_falha(db_session: AsyncSession, guarnicao, usuario):
    """criar_equipe rejeita nome duplicado entre ativas."""
    service = EquipeService(db_session)
    with pytest.raises(ConflitoDadosError):
        await service.criar_equipe(
            nome=guarnicao.nome, unidade=guarnicao.unidade, admin_id=usuario.id
        )


@pytest.mark.asyncio
async def test_toggle_isolamento_alterna_valor(db_session: AsyncSession, guarnicao, usuario):
    """toggle_isolamento alterna o valor."""
    service = EquipeService(db_session)
    assert guarnicao.isolamento_abordagens is False
    e1 = await service.toggle_isolamento(guarnicao.id, valor=True, admin_id=usuario.id)
    assert e1.isolamento_abordagens is True
    e2 = await service.toggle_isolamento(guarnicao.id, valor=False, admin_id=usuario.id)
    assert e2.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_toggle_isolamento_inexistente_falha(db_session: AsyncSession, usuario):
    """toggle_isolamento em equipe inexistente lança NaoEncontradoError."""
    service = EquipeService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.toggle_isolamento(999_999, valor=True, admin_id=usuario.id)
