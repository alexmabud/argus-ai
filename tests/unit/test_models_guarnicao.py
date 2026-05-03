"""Testes do model Guarnicao — campo isolamento_abordagens e FK bpm_id."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guarnicao import Guarnicao


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_default_false(db_session: AsyncSession, bpm):
    """Nova guarnição tem isolamento_abordagens=False por padrão."""
    g = Guarnicao(nome="GU 02", bpm_id=bpm.id, codigo="3BPM-3CIA-GU02")
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_persiste_true(db_session: AsyncSession, bpm):
    """isolamento_abordagens=True persiste corretamente."""
    g = Guarnicao(
        nome="GU 03",
        bpm_id=bpm.id,
        codigo="3BPM-3CIA-GU03",
        isolamento_abordagens=True,
    )
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is True


@pytest.mark.asyncio
async def test_guarnicao_carrega_bpm(db_session: AsyncSession, bpm):
    """Guarnicao carrega o relacionamento bpm automaticamente."""
    g = Guarnicao(nome="GU 04", bpm_id=bpm.id, codigo="3BPM-3CIA-GU04")
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.bpm_id == bpm.id
