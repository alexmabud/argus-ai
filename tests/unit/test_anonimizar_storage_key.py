"""Teste da extração de chave de storage do script de anonimização (LGPD).

Valida ``_storage_key`` — a conversão URL→chave usada para apagar os arquivos
de foto do storage no script ``scripts/anonimizar_dados.py`` (achado #14/2C).
"""

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "anonimizar_dados.py"
_spec = importlib.util.spec_from_file_location("anonimizar_dados", _SCRIPT)
anon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(anon)


def test_storage_key_relativo():
    """URL relativa /storage/bucket/key resolve para a chave relativa ao bucket."""
    assert anon._storage_key("/storage/argus-fotos/fotos/uuid.jpg") == "fotos/uuid.jpg"


def test_storage_key_none():
    """URL None não gera chave."""
    assert anon._storage_key(None) is None


def test_storage_key_sentinela():
    """Marcador de URL anonimizada não é uma chave de storage."""
    assert anon._storage_key(anon._URL_ANONIMIZADA) is None
