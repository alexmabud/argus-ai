"""Testes dos schemas de Equipe (Guarnicao) e BPM."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    EquipeCreate,
    EquipeRead,
    UsuarioAdminCreate,
    UsuarioAdminRead,
)
from app.schemas.bpm import BpmCreate, BpmRead


def test_bpm_create_valida_nome():
    """BpmCreate exige nome."""
    b = BpmCreate(nome="14º BPM")
    assert b.nome == "14º BPM"


def test_bpm_create_rejeita_nome_vazio():
    """BpmCreate rejeita nome vazio."""
    with pytest.raises(ValidationError):
        BpmCreate(nome="")


def test_bpm_read_campos():
    """BpmRead expõe id e nome."""
    b = BpmRead(id=1, nome="14º BPM")
    assert b.id == 1
    assert b.nome == "14º BPM"


def test_equipe_create_valida_campos():
    """EquipeCreate exige nome e bpm_id."""
    e = EquipeCreate(nome="3a Cia - GU 01", bpm_id=1)
    assert e.nome == "3a Cia - GU 01"
    assert e.bpm_id == 1


def test_equipe_create_rejeita_nome_vazio():
    """EquipeCreate rejeita nome vazio."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="", bpm_id=1)


def test_equipe_create_rejeita_bpm_id_ausente():
    """EquipeCreate rejeita bpm_id ausente."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="GU 01")


def test_equipe_read_inclui_bpm_e_isolamento():
    """EquipeRead expõe bpm (objeto aninhado) e isolamento_abordagens."""
    bpm_obj = BpmRead(id=1, nome="14º BPM")
    e = EquipeRead(
        id=1,
        nome="GU 01",
        bpm_id=1,
        bpm=bpm_obj,
        codigo="14BPM-GU01",
        isolamento_abordagens=True,
    )
    assert e.isolamento_abordagens is True
    assert e.bpm.nome == "14º BPM"


def test_usuario_admin_create_aceita_guarnicao_id_opcional():
    """UsuarioAdminCreate aceita guarnicao_id opcional (None = sem equipe)."""
    u1 = UsuarioAdminCreate(matricula="PM001")
    assert u1.guarnicao_id is None
    u2 = UsuarioAdminCreate(matricula="PM002", guarnicao_id=5)
    assert u2.guarnicao_id == 5


def test_usuario_admin_read_aceita_guarnicao_id_none():
    """UsuarioAdminRead permite guarnicao_id None (usuário sem equipe)."""
    u = UsuarioAdminRead(
        id=1,
        nome="Soldado",
        matricula="PM001",
        is_admin=False,
        ativo=True,
        tem_sessao=False,
        guarnicao_id=None,
    )
    assert u.guarnicao_id is None
