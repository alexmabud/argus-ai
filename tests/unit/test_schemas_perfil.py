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
        guarnicao_id=1,
    )
    assert schema.tem_sessao is True


def test_senha_gerada_response():
    """Verifica campos de SenhaGeradaResponse."""
    schema = SenhaGeradaResponse(usuario_id=1, matricula="PM001", senha="abc12345")
    assert schema.senha == "abc12345"


def test_perfil_update_rejeita_foto_url_externa_http():
    """URL externa http:// nao deve ser aceita em foto_url.

    Caso contrario, atacante grava http://attacker/track.png?u=vitima e cada
    outro policial que abre o perfil exfiltra IP+referer.
    """
    with pytest.raises(ValidationError, match="foto_url"):
        PerfilUpdate(nome="Agente Teste", foto_url="http://attacker.com/x.png")


def test_perfil_update_rejeita_foto_url_externa_https():
    """URL externa https:// tambem nao deve ser aceita."""
    with pytest.raises(ValidationError, match="foto_url"):
        PerfilUpdate(nome="Agente Teste", foto_url="https://attacker.com/x.png")


def test_perfil_update_aceita_path_storage():
    """Path interno /storage/... deve ser aceito (formato retornado pelo S3 upload)."""
    schema = PerfilUpdate(
        nome="Agente Teste",
        foto_url="/storage/argus/avatares/uuid123_perfil.jpg",
    )
    assert schema.foto_url == "/storage/argus/avatares/uuid123_perfil.jpg"


def test_perfil_update_aceita_foto_url_none():
    """foto_url=None deve continuar valido (campo opcional)."""
    schema = PerfilUpdate(nome="Agente Teste", foto_url=None)
    assert schema.foto_url is None
