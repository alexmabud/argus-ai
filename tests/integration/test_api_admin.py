"""Testes do painel admin — gestão de usuários."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.usuario import Usuario


@pytest.fixture
async def admin_usuario(db_session, guarnicao):
    """Fixture de usuário admin com sessão ativa.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição.

    Returns:
        Usuario admin com session_id ativo.
    """
    u = Usuario(
        nome="Admin Teste",
        matricula="ADMIN001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        session_id="admin-session-id",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_headers(admin_usuario):
    """Headers de autenticação para o admin.

    Args:
        admin_usuario: Fixture de usuário admin.

    Returns:
        dict: Headers com Authorization Bearer token do admin.
    """
    token = criar_access_token(
        {
            "sub": str(admin_usuario.id),
            "guarnicao_id": admin_usuario.guarnicao_id,
            "sid": admin_usuario.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_listar_usuarios_admin(client: AsyncClient, admin_headers, usuario):
    """Admin consegue listar usuários da guarnição."""
    response = await client.get("/api/v1/admin/usuarios", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_criar_usuario_retorna_senha(client: AsyncClient, admin_headers):
    """Admin cria usuário e recebe senha gerada."""
    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "NOVO001"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "senha" in data
    assert len(data["senha"]) >= 8
    assert data["matricula"] == "NOVO001"


@pytest.mark.asyncio
async def test_criar_usuario_sem_admin_retorna_403(client: AsyncClient, auth_headers):
    """Usuário comum não pode criar usuários."""
    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "NOVO002"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pausar_usuario(client: AsyncClient, admin_headers, usuario, db_session):
    """Admin pausa usuário e session_id é limpo."""
    response = await client.patch(
        f"/api/v1/admin/usuarios/{usuario.id}/pausar",
        headers=admin_headers,
    )
    assert response.status_code == 200
    await db_session.refresh(usuario)
    assert usuario.session_id is None


@pytest.mark.asyncio
async def test_gerar_nova_senha(client: AsyncClient, admin_headers, usuario):
    """Admin gera nova senha e recebe plain text."""
    response = await client.post(
        f"/api/v1/admin/usuarios/{usuario.id}/gerar-senha",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "senha" in data
    assert len(data["senha"]) >= 8
