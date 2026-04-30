"""Testes do model Guarnicao — campo isolamento_abordagens."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guarnicao import Guarnicao


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_default_false(db_session: AsyncSession):
    """Nova guarnição tem isolamento_abordagens=False por padrão."""
    g = Guarnicao(nome="GU 02", unidade="3o BPM", codigo="3BPM-3CIA-GU02")
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_persiste_true(db_session: AsyncSession):
    """isolamento_abordagens=True persiste corretamente."""
    g = Guarnicao(
        nome="GU 03",
        unidade="3o BPM",
        codigo="3BPM-3CIA-GU03",
        isolamento_abordagens=True,
    )
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is True
