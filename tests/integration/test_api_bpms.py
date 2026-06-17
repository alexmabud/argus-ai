"""Testes do router /admin/bpms — listar e criar BPMs."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.usuario import Usuario


@pytest.fixture
async def admin_bpm(db_session, guarnicao):
    """Admin para testes de BPM.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Guarnição de contexto para o admin.

    Returns:
        Usuario: Admin com sessão ativa.
    """
    u = Usuario(
        nome="Admin BPM",
        matricula="ADMBPM001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        is_super_admin=True,
        session_id="admin-bpm-session",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_bpm_headers(admin_bpm):
    """Headers de autenticação do admin de BPMs.

    Args:
        admin_bpm: Fixture de admin para BPMs.

    Returns:
        dict: Headers com Authorization Bearer token.
    """
    token = criar_access_token(
        {
            "sub": str(admin_bpm.id),
            "guarnicao_id": admin_bpm.guarnicao_id,
            "sid": admin_bpm.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_listar_bpms_retorna_lista(client: AsyncClient, admin_bpm_headers, bpm):
    """GET /admin/bpms retorna lista com BPMs ativos."""
    response = await client.get("/api/v1/admin/bpms", headers=admin_bpm_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(b["id"] == bpm.id for b in data)


@pytest.mark.asyncio
async def test_criar_bpm_201(client: AsyncClient, admin_bpm_headers):
    """POST /admin/bpms cria novo BPM e retorna 201."""
    response = await client.post(
        "/api/v1/admin/bpms",
        json={"nome": "14º BPM"},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "14º BPM"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_criar_bpm_sem_admin_403(client: AsyncClient, auth_headers):
    """Usuário comum recebe 403 ao tentar criar BPM."""
    response = await client.post(
        "/api/v1/admin/bpms",
        json={"nome": "Novo BPM"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_criar_bpm_nome_duplicado_409(client: AsyncClient, admin_bpm_headers, bpm):
    """POST /admin/bpms rejeita nome duplicado com 409."""
    response = await client.post(
        "/api/v1/admin/bpms",
        json={"nome": bpm.nome},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_ativa_200(client: AsyncClient, admin_bpm_headers, bpm):
    """PATCH /admin/bpms/{id}/toggle-isolamento com True retorna 200 e campo atualizado."""
    response = await client.patch(
        f"/api/v1/admin/bpms/{bpm.id}/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 200
    assert response.json()["isolamento_abordagens"] is True


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_desativa_200(
    client: AsyncClient, admin_bpm_headers, bpm, db_session
):
    """PATCH /admin/bpms/{id}/toggle-isolamento com False retorna 200 e desativa."""
    bpm.isolamento_abordagens = True
    await db_session.flush()
    response = await client.patch(
        f"/api/v1/admin/bpms/{bpm.id}/toggle-isolamento",
        json={"isolamento_abordagens": False},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 200
    assert response.json()["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_sem_admin_403(client: AsyncClient, auth_headers, bpm):
    """Usuário comum recebe 403 ao tentar alterar isolamento de BPM."""
    response = await client.patch(
        f"/api/v1/admin/bpms/{bpm.id}/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_nao_encontrado_404(client: AsyncClient, admin_bpm_headers):
    """PATCH com BPM inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/admin/bpms/9999/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 404
