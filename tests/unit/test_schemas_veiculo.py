"""Testes dos schemas Pydantic de Veículo.

Valida a normalização para MAIÚSCULAS dos campos de texto livre (modelo,
cor, tipo, observações) e a normalização já existente da placa.
"""

from __future__ import annotations

from app.schemas.veiculo import VeiculoCreate, VeiculoUpdate


def test_veiculo_create_normaliza_modelo_cor_tipo_obs():
    """VeiculoCreate normaliza modelo, cor, tipo e observações."""
    v = VeiculoCreate(
        placa="abc1d23",
        modelo="gol",
        cor="prata",
        tipo="carro",
        observacoes="vidro traseiro quebrado",
    )
    assert v.placa == "ABC1D23"  # já era normalizada
    assert v.modelo == "GOL"
    assert v.cor == "PRATA"
    assert v.tipo == "CARRO"
    assert v.observacoes == "VIDRO TRASEIRO QUEBRADO"


def test_veiculo_update_normaliza():
    """VeiculoUpdate normaliza os campos de texto enviados."""
    u = VeiculoUpdate(modelo="onix", cor="preto", tipo="moto", observacoes="adesivado")
    assert u.modelo == "ONIX"
    assert u.cor == "PRETO"
    assert u.tipo == "MOTO"
    assert u.observacoes == "ADESIVADO"
