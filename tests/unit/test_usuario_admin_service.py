"""Testes do serviço de gestão de usuários pelo admin."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_db():
    """Mock da sessão do banco."""
    return AsyncMock()


def test_gerar_senha_tem_entropia_minima():
    """Verifica que a senha gerada tem pelo menos 12 caracteres (token_urlsafe 12)."""
    from app.services.usuario_admin_service import _gerar_senha

    for _ in range(20):  # múltiplas chamadas para cobrir variabilidade
        s = _gerar_senha()
        assert len(s) >= 12, f"Senha gerada tem apenas {len(s)} chars: {s!r}"


@pytest.mark.asyncio
async def test_criar_usuario_retorna_senha_gerada(mock_db):
    """Verifica que criação gera senha aleatória e retorna em plain text."""
    from app.services.usuario_admin_service import UsuarioAdminService

    # nenhum usuário com essa matrícula (ativo ou inativo)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()

    service = UsuarioAdminService(mock_db)
    service.audit = AsyncMock()

    with patch("app.services.usuario_admin_service.hash_senha", return_value="hash"):
        usuario, senha = await service.criar_usuario("PM001", admin_id=1)

    assert len(senha) >= 8
    assert usuario.matricula == "PM001"
    assert usuario.session_id is None  # sem sessão até o primeiro login


@pytest.mark.asyncio
async def test_criar_usuario_matricula_duplicada_levanta_erro(mock_db):
    """Verifica que matrícula duplicada (usuário ativo) levanta ConflitoDadosError."""
    from app.core.exceptions import ConflitoDadosError
    from app.services.usuario_admin_service import UsuarioAdminService

    usuario_ativo = MagicMock()
    usuario_ativo.ativo = True
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = usuario_ativo
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = UsuarioAdminService(mock_db)

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


@pytest.mark.asyncio
async def test_definir_super_admin_marca_por_matricula(db_session, usuario):
    """definir_super_admin marca is_super_admin=True pela matrícula (idempotente)."""
    from app.services.usuario_admin_service import UsuarioAdminService

    service = UsuarioAdminService(db_session)

    alterado = await service.definir_super_admin(usuario.matricula)
    await db_session.refresh(usuario)
    assert alterado is True
    assert usuario.is_super_admin is True

    # idempotente: segunda chamada não quebra e mantém True
    de_novo = await service.definir_super_admin(usuario.matricula)
    assert de_novo is True
    await db_session.refresh(usuario)
    assert usuario.is_super_admin is True


@pytest.mark.asyncio
async def test_definir_super_admin_matricula_inexistente(db_session):
    """Matrícula inexistente lança NaoEncontradoError."""
    from app.core.exceptions import NaoEncontradoError
    from app.services.usuario_admin_service import UsuarioAdminService

    service = UsuarioAdminService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.definir_super_admin("NAOEXISTE")
