"""Testes dos schemas de Equipe (Guarnicao)."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    EquipeCreate,
    EquipeRead,
    UsuarioAdminCreate,
    UsuarioAdminRead,
)


def test_equipe_create_valida_campos():
    """EquipeCreate exige nome e unidade."""
    e = EquipeCreate(nome="3a Cia - GU 01", unidade="3o BPM")
    assert e.nome == "3a Cia - GU 01"
    assert e.unidade == "3o BPM"


def test_equipe_create_rejeita_nome_vazio():
    """EquipeCreate rejeita nome vazio."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="", unidade="3o BPM")


def test_equipe_create_rejeita_unidade_vazia():
    """EquipeCreate rejeita unidade vazia."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="GU 01", unidade="")


def test_equipe_read_inclui_isolamento():
    """EquipeRead expõe campo isolamento_abordagens."""
    e = EquipeRead(
        id=1,
        nome="GU 01",
        unidade="3o BPM",
        codigo="3BPM-GU01",
        isolamento_abordagens=True,
    )
    assert e.isolamento_abordagens is True


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
