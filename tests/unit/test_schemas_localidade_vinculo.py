"""Testes de normalização para MAIÚSCULAS em Localidade e VínculoManual.

Garante que cidade/bairro digitados no autocomplete e os campos de vínculo
manual digitados pelo operador são padronizados para MAIÚSCULAS.
"""

from __future__ import annotations

from app.schemas.localidade import LocalidadeCreate
from app.schemas.vinculo_manual import VinculoManualCreate


def test_localidade_create_normaliza_nome():
    """O nome digitado (vira nome_exibicao) é normalizado para maiúsculas."""
    loc = LocalidadeCreate(nome="rio de janeiro", tipo="cidade", parent_id=1)
    assert loc.nome == "RIO DE JANEIRO"


def test_vinculo_manual_normaliza_tipo_e_descricao():
    """tipo e descricao do vínculo manual são normalizados para maiúsculas."""
    v = VinculoManualCreate(
        pessoa_vinculada_id=2,
        tipo="irmão",
        descricao="mora junto",
    )
    assert v.tipo == "IRMÃO"
    assert v.descricao == "MORA JUNTO"


def test_vinculo_manual_descricao_opcional_none():
    """descricao ausente permanece None."""
    v = VinculoManualCreate(pessoa_vinculada_id=2, tipo="pai")
    assert v.tipo == "PAI"
    assert v.descricao is None
