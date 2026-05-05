"""Testes de unidade do BpmService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError
from app.services.bpm_service import BpmService


@pytest.mark.asyncio
async def test_listar_bpms_retorna_todos_ativos(db_session: AsyncSession, bpm):
    """listar_bpms retorna todos os BPMs ativos."""
    service = BpmService(db_session)
    bpms = await service.listar_bpms()
    assert len(bpms) >= 1
    assert any(b.id == bpm.id for b in bpms)


@pytest.mark.asyncio
async def test_criar_bpm_sucesso(db_session: AsyncSession, usuario):
    """criar_bpm cria BPM com nome fornecido."""
    service = BpmService(db_session)
    b = await service.criar_bpm(nome="14º BPM", admin_id=usuario.id)
    assert b.id is not None
    assert b.nome == "14º BPM"
    assert b.ativo is True


@pytest.mark.asyncio
async def test_criar_bpm_nome_duplicado_falha(db_session: AsyncSession, bpm, usuario):
    """criar_bpm rejeita nome duplicado."""
    service = BpmService(db_session)
    with pytest.raises(ConflitoDadosError):
        await service.criar_bpm(nome=bpm.nome, admin_id=usuario.id)


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_ativa(db_session: AsyncSession, bpm, usuario):
    """toggle_isolamento(True) ativa isolamento_abordagens no BPM."""
    service = BpmService(db_session)
    result = await service.toggle_isolamento(bpm_id=bpm.id, valor=True, admin_id=usuario.id)
    assert result.isolamento_abordagens is True


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_desativa(db_session: AsyncSession, bpm, usuario):
    """toggle_isolamento(False) desativa isolamento_abordagens no BPM."""
    bpm.isolamento_abordagens = True
    await db_session.flush()
    service = BpmService(db_session)
    result = await service.toggle_isolamento(bpm_id=bpm.id, valor=False, admin_id=usuario.id)
    assert result.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_nao_encontrado(db_session: AsyncSession):
    """toggle_isolamento com ID inexistente lança NaoEncontradoError."""
    from app.core.exceptions import NaoEncontradoError

    service = BpmService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.toggle_isolamento(bpm_id=9999, valor=True, admin_id=1)
