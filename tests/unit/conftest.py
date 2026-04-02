"""Configuração pytest para testes unitários.

Sobrepõe fixtures de banco de dados do conftest raiz para que testes
puramente unitários possam rodar sem conexão com PostgreSQL.
"""

import pytest


@pytest.fixture(autouse=True)
async def setup_db():
    """Fixture no-op que sobrepõe o setup_db do conftest raiz.

    Testes unitários não necessitam de banco de dados.
    """
    yield
