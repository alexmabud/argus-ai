"""Testes de autenticação — senha única e session_id exclusivo."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import CredenciaisInvalidasError
from app.services.auth_service import AuthService


@pytest.fixture
def mock_db():
    """Fixture de mock para sessão do banco."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_login_gera_session_id(mock_db):
    """Verifica que login bem-sucedido gera e salva session_id no usuário."""
    usuario = MagicMock()
    usuario.id = 1
    usuario.guarnicao_id = 1
    usuario.session_id = None

    service = AuthService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = usuario
    service.audit = AsyncMock()

    with patch("app.services.auth_service.verificar_senha", return_value=True), patch(
        "app.services.auth_service.hash_senha", return_value="hash_aleatorio"
    ):
        result = await service.login("TEST001", "senha123")

    # session_id deve ter sido atribuído
    assert usuario.session_id is not None
    assert len(usuario.session_id) == 36  # UUID4 format

    # Token deve conter sid
    from app.core.security import decodificar_token

    payload = decodificar_token(result.access_token)
    assert payload["sid"] == usuario.session_id


@pytest.mark.asyncio
async def test_login_invalida_senha_apos_uso(mock_db):
    """Verifica que senha é substituída por hash inutilizável após login."""
    usuario = MagicMock()
    usuario.id = 1
    usuario.guarnicao_id = None
    usuario.session_id = None

    service = AuthService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = usuario
    service.audit = AsyncMock()

    novo_hash = "hash_novo_inutilizavel"
    with patch("app.services.auth_service.verificar_senha", return_value=True), patch(
        "app.services.auth_service.hash_senha", return_value=novo_hash
    ):
        await service.login("TEST001", "senha_unica")

    # senha_hash substituída
    assert usuario.senha_hash == novo_hash


@pytest.mark.asyncio
async def test_login_invalido_nao_altera_usuario(mock_db):
    """Verifica que login com senha errada não altera o usuário."""
    usuario = MagicMock()
    usuario.id = 1
    usuario.session_id = "sessao-anterior"

    service = AuthService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = usuario
    service.audit = AsyncMock()

    with patch("app.services.auth_service.verificar_senha", return_value=False):
        with pytest.raises(CredenciaisInvalidasError):
            await service.login("TEST001", "senhaerrada")

    # session_id NÃO deve ter mudado
    assert usuario.session_id == "sessao-anterior"
