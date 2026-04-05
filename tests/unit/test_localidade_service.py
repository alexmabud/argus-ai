"""Testes unitários do LocalidadeService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ConflitoDadosError
from app.schemas.localidade import LocalidadeCreate
from app.services.localidade_service import LocalidadeService


@pytest.mark.asyncio
async def test_criar_cidade_nova():
    """Deve criar cidade quando não existe duplicata."""
    db = AsyncMock()
    db.add = MagicMock()
    service = LocalidadeService(db)
    service.repo = AsyncMock()
    service.repo.buscar_por_nome_e_parent = AsyncMock(return_value=None)
    service.repo.get = AsyncMock(return_value=MagicMock(tipo="estado"))

    data = LocalidadeCreate(nome="Campinas", tipo="cidade", parent_id=1)
    await service.criar(data)

    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_criar_cidade_duplicata_levanta_erro():
    """Deve levantar ConflitoDadosError quando cidade já existe."""
    db = AsyncMock()
    service = LocalidadeService(db)
    service.repo = AsyncMock()
    service.repo.buscar_por_nome_e_parent = AsyncMock(return_value=MagicMock())
    service.repo.get = AsyncMock(return_value=MagicMock(tipo="estado"))

    data = LocalidadeCreate(nome="Campinas", tipo="cidade", parent_id=1)
    with pytest.raises(ConflitoDadosError):
        await service.criar(data)


@pytest.mark.asyncio
async def test_criar_cidade_sem_pai_estado_levanta_erro():
    """Deve levantar erro quando pai de cidade não é um estado."""
    db = AsyncMock()
    service = LocalidadeService(db)
    service.repo = AsyncMock()
    service.repo.buscar_por_nome_e_parent = AsyncMock(return_value=None)
    service.repo.get = AsyncMock(return_value=MagicMock(tipo="bairro"))  # pai inválido

    data = LocalidadeCreate(nome="Campinas", tipo="cidade", parent_id=99)
    with pytest.raises(Exception):
        await service.criar(data)
