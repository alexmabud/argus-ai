"""Testes do router /admin/equipes — listar, criar, toggle isolamento."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.usuario import Usuario


@pytest.fixture
async def admin_eq(db_session, guarnicao):
    """Admin com sessão ativa para testes de equipes.

    Args:
        db_session: Sessão do banco de dados para o teste.
        guarnicao: Guarnição de contexto para o admin.

    Returns:
        Usuario: Admin com sessão ativa.
    """
    u = Usuario(
        nome="Admin Equipes",
        matricula="ADMEQ001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        is_super_admin=True,
        session_id="admin-eq-session",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_eq_headers(admin_eq):
    """Headers de autenticação do admin de equipes.

    Args:
        admin_eq: Fixture de admin para equipes.

    Returns:
        dict: Headers com Authorization Bearer token.
    """
    token = criar_access_token(
        {
            "sub": str(admin_eq.id),
            "guarnicao_id": admin_eq.guarnicao_id,
            "sid": admin_eq.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_listar_equipes_retorna_lista(client: AsyncClient, admin_eq_headers, guarnicao):
    """GET /admin/equipes retorna todas as equipes ativas com bpm aninhado."""
    response = await client.get("/api/v1/admin/equipes", headers=admin_eq_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(e["id"] == guarnicao.id for e in data)
    assert "isolamento_abordagens" in data[0]
    assert "bpm" in data[0]
    assert "bpm_id" in data[0]


@pytest.mark.asyncio
async def test_criar_equipe_201(client: AsyncClient, admin_eq_headers, bpm):
    """POST /admin/equipes cria nova equipe e retorna 201."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": "GU 50", "bpm_id": bpm.id},
        headers=admin_eq_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "GU 50"
    assert data["bpm_id"] == bpm.id
    assert data["bpm"]["nome"] == bpm.nome
    assert data["codigo"]
    assert data["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_criar_equipe_nome_duplicado_409(client: AsyncClient, admin_eq_headers, guarnicao):
    """POST /admin/equipes rejeita nome duplicado com 409."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": guarnicao.nome, "bpm_id": guarnicao.bpm_id},
        headers=admin_eq_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_criar_equipe_sem_admin_403(client: AsyncClient, auth_headers, bpm):
    """Usuário comum recebe 403 ao tentar criar equipe."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": "X", "bpm_id": bpm.id},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_toggle_isolamento_alterna(client: AsyncClient, admin_eq_headers, guarnicao):
    """PATCH /admin/equipes/{id}/toggle-isolamento alterna o valor."""
    r1 = await client.patch(
        f"/api/v1/admin/equipes/{guarnicao.id}/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_eq_headers,
    )
    assert r1.status_code == 200
    assert r1.json()["isolamento_abordagens"] is True

    r2 = await client.patch(
        f"/api/v1/admin/equipes/{guarnicao.id}/toggle-isolamento",
        json={"isolamento_abordagens": False},
        headers=admin_eq_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_toggle_isolamento_inexistente_404(client: AsyncClient, admin_eq_headers):
    """PATCH em equipe inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/admin/equipes/999999/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_eq_headers,
    )
    assert response.status_code == 404
