"""Testes do helper de normalização de texto para MAIÚSCULAS.

Cobre a função `to_upper` e os tipos anotados `UpperStr`/`UpperStrReq`
usados nos schemas Pydantic para padronizar texto digitado pelo usuário.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.validators import UpperStr, UpperStrReq, to_upper


def test_to_upper_converte_minusculo():
    """Texto minúsculo deve virar maiúsculo."""
    assert to_upper("joão da silva") == "JOÃO DA SILVA"


def test_to_upper_respeita_acentos():
    """Acentos devem ser preservados na conversão."""
    assert to_upper("são joão") == "SÃO JOÃO"


def test_to_upper_remove_espacos_nas_pontas():
    """Espaços nas pontas devem ser removidos."""
    assert to_upper("  rua das flores  ") == "RUA DAS FLORES"


def test_to_upper_preserva_none():
    """None deve permanecer None (campos opcionais)."""
    assert to_upper(None) is None


class _ModeloOpcional(BaseModel):
    campo: UpperStr = None


class _ModeloObrigatorio(BaseModel):
    campo: UpperStrReq


def test_upperstr_opcional_normaliza():
    """UpperStr converte valor opcional para maiúsculo."""
    assert _ModeloOpcional(campo="abc").campo == "ABC"


def test_upperstr_opcional_aceita_none():
    """UpperStr aceita None sem erro."""
    assert _ModeloOpcional().campo is None


def test_upperstrreq_normaliza():
    """UpperStrReq converte valor obrigatório para maiúsculo."""
    assert _ModeloObrigatorio(campo="abc").campo == "ABC"


def test_upperstrreq_rejeita_none():
    """UpperStrReq não aceita None (campo obrigatório)."""
    with pytest.raises(ValidationError):
        _ModeloObrigatorio(campo=None)
