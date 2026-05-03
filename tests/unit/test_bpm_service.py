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
