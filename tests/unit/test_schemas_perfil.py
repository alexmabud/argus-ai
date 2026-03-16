"""Testes dos schemas de perfil e admin."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    PerfilUpdate,
    SenhaGeradaResponse,
    UsuarioAdminCreate,
    UsuarioAdminRead,
    UsuarioRead,
)


def test_perfil_update_posto_valido():
    """Verifica que PerfilUpdate aceita posto da lista oficial."""
    schema = PerfilUpdate(nome="João Silva", posto_graduacao="Capitão")
    assert schema.posto_graduacao == "Capitão"


def test_perfil_update_posto_invalido_rejeita():
    """Verifica que PerfilUpdate rejeita posto fora da lista."""
    with pytest.raises(ValidationError):
        PerfilUpdate(nome="João", posto_graduacao="General")


def test_perfil_update_sem_posto_valido():
    """Verifica que PerfilUpdate aceita posto None."""
    schema = PerfilUpdate(nome="João Silva", posto_graduacao=None)
    assert schema.posto_graduacao is None


def test_perfil_update_nome_guerra():
    """Verifica que PerfilUpdate aceita nome_guerra."""
    schema = PerfilUpdate(nome="João Silva", nome_guerra="Silva")
    assert schema.nome_guerra == "Silva"


def test_admin_create_apenas_matricula():
    """Verifica que UsuarioAdminCreate aceita apenas matrícula."""
    schema = UsuarioAdminCreate(matricula="PM001")
    assert schema.matricula == "PM001"


def test_usuario_read_inclui_novos_campos():
    """Verifica que UsuarioRead inclui posto_graduacao, nome_guerra e foto_url."""
    schema = UsuarioRead(
        id=1,
        nome="Agente",
        matricula="T001",
        is_admin=False,
        guarnicao_id=1,
        criado_em=datetime.now(),
        posto_graduacao="Capitão",
        nome_guerra="Silva",
        foto_url="https://r2.example.com/foto.jpg",
    )
    assert schema.posto_graduacao == "Capitão"
    assert schema.nome_guerra == "Silva"
    assert schema.foto_url == "https://r2.example.com/foto.jpg"


def test_usuario_admin_read_tem_sessao():
    """Verifica que UsuarioAdminRead tem campo tem_sessao."""
    schema = UsuarioAdminRead(
        id=1,
        nome="Agente",
        matricula="PM001",
        is_admin=False,
        ativo=True,
        tem_sessao=True,
    )
    assert schema.tem_sessao is True


def test_senha_gerada_response():
    """Verifica campos de SenhaGeradaResponse."""
    schema = SenhaGeradaResponse(usuario_id=1, matricula="PM001", senha="abc12345")
    assert schema.senha == "abc12345"
