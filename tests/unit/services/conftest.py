"""Fixtures locais para testes unitários de services."""

import pytest

from app.services.storage_service import StorageService


@pytest.fixture(autouse=True)
def _reset_storage_service_singleton():
    """Limpa o singleton de StorageService entre testes do diretório.

    Evita contaminação cruzada quando um teste deixa instância pendurada
    com cliente fechado ou mock antigo.
    """
    StorageService._instance = None
    yield
    StorageService._instance = None
