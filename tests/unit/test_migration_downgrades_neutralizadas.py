"""Testes das migrations com downgrade neutralizado (achado #27/2026-07-13).

Garante que os downgrades perigosos (recriação manual de tabelas internas
do Tiger Geocoder do PostGIS + DROP de todas as tabelas da aplicação;
DROP EXTENSION unaccent, usada por toda busca fuzzy de nome) levantam
NotImplementedError em vez de executar DDL destrutivo — sem depender de um
banco real, já que a exceção é levantada antes de qualquer op.execute().
"""

import importlib.util
from pathlib import Path

import pytest

_VERSIONS_DIR = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def _carregar_migration(filename: str):
    """Carrega um módulo de migration do Alembic diretamente do arquivo."""
    path = _VERSIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestDowngradeSchemaInicialNeutralizado:
    """Testes de 08ef2221d8ba_schema_inicial.py (migration raiz, down_revision=None)."""

    def test_downgrade_levanta_not_implemented_error(self):
        """downgrade() não deve executar DDL — só levantar NotImplementedError."""
        mod = _carregar_migration("08ef2221d8ba_schema_inicial.py")
        with pytest.raises(NotImplementedError, match="Tiger Geocoder"):
            mod.downgrade()


class TestDowngradeUnaccentNeutralizado:
    """Testes de f5a6b7c8d9e0_add_unaccent_extension.py."""

    def test_downgrade_levanta_not_implemented_error(self):
        """downgrade() não deve executar DROP EXTENSION — só levantar NotImplementedError."""
        mod = _carregar_migration("f5a6b7c8d9e0_add_unaccent_extension.py")
        with pytest.raises(NotImplementedError, match="unaccent"):
            mod.downgrade()
