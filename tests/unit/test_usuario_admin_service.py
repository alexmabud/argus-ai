"""Testes do serviço de gestão de usuários pelo admin."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_db():
    """Mock da sessão do banco."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_criar_usuario_retorna_senha_gerada(mock_db):
    """Verifica que criação gera senha aleatória e retorna em plain text."""
    from app.services.usuario_admin_service import UsuarioAdminService

    # Configurar mock para query de guarnição padrão (guarnicao_id não informado)
    mock_guarnicao = MagicMock()
    mock_guarnicao.id = 1
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_guarnicao
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()

    service = UsuarioAdminService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = None
    service.audit = AsyncMock()

    with patch("app.services.usuario_admin_service.hash_senha", return_value="hash"):
        usuario, senha = await service.criar_usuario("PM001", admin_id=1)

    assert len(senha) >= 8
    assert usuario.matricula == "PM001"
    assert usuario.session_id is None  # sem sessão até o primeiro login


@pytest.mark.asyncio
async def test_criar_usuario_matricula_duplicada_levanta_erro(mock_db):
    """Verifica que matrícula duplicada levanta ConflitoDadosError."""
    from app.core.exceptions import ConflitoDadosError
    from app.services.usuario_admin_service import UsuarioAdminService

    service = UsuarioAdminService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = MagicMock()  # já existe

    with pytest.raises(ConflitoDadosError):
        await service.criar_usuario("PM001", admin_id=1)


@pytest.mark.asyncio
async def test_pausar_usuario_limpa_session_id(mock_db):
    """Verifica que pausar apaga session_id (desconexão imediata)."""
    from app.services.usuario_admin_service import UsuarioAdminService

    usuario = MagicMock()
    usuario.session_id = "sessao-ativa"
    usuario.ativo = True

    service = UsuarioAdminService(mock_db)
    service.repo = AsyncMock()
    service.repo.get.return_value = usuario
    service.audit = AsyncMock()

    await service.pausar_usuario(usuario_id=1, admin_id=2)

    assert usuario.session_id is None


@pytest.mark.asyncio
async def test_gerar_nova_senha_invalida_sessao(mock_db):
    """Verifica que gerar nova senha limpa session_id e retorna nova senha."""
    from app.services.usuario_admin_service import UsuarioAdminService

    usuario = MagicMock()
    usuario.session_id = "sessao-velha"
    usuario.ativo = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = usuario
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = UsuarioAdminService(mock_db)
    service.audit = AsyncMock()

    with patch("app.services.usuario_admin_service.hash_senha", return_value="novo_hash"):
        senha, matricula = await service.gerar_nova_senha(usuario_id=1, admin_id=2)

    assert len(senha) >= 8
    assert usuario.session_id is None
    assert usuario.senha_hash == "novo_hash"
    assert usuario.ativo is True
