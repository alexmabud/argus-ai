"""Testes dos schemas Pydantic de PessoaObservacao.

Valida a normalização para MAIÚSCULAS do campo texto nas operações de
criação e atualização de observações de pessoa.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.pessoa_observacao import (
    PessoaObservacaoCreate,
    PessoaObservacaoUpdate,
)


def test_observacao_create_normaliza_para_maiuscula():
    """PessoaObservacaoCreate converte o texto para maiúsculas."""
    o = PessoaObservacaoCreate(texto="vista frequentemente na praça")
    assert o.texto == "VISTA FREQUENTEMENTE NA PRAÇA"


def test_observacao_update_normaliza_para_maiuscula():
    """PessoaObservacaoUpdate converte o texto para maiúsculas."""
    o = PessoaObservacaoUpdate(texto="novo texto")
    assert o.texto == "NOVO TEXTO"


def test_observacao_texto_vazio_rejeitado():
    """Texto vazio continua rejeitado (min_length=1)."""
    with pytest.raises(ValidationError):
        PessoaObservacaoCreate(texto="")
