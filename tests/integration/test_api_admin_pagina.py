"""Testes da página de admins (gestão de admins pelo super-admin)."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.usuario import Usuario


@pytest.fixture
async def super_admin(db_session, guarnicao):
    """Fixture do super-admin (dono) com sessão ativa."""
    u = Usuario(
        nome="Dono",
        matricula="DONO001",
        senha_hash=hash_senha("x"),
        guarnicao_id=guarnicao.id,
        is_super_admin=True,
        session_id="dono-sid",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def super_headers(super_admin):
    """Headers Bearer do super-admin."""
    token = criar_access_token(
        {
            "sub": str(super_admin.id),
            "guarnicao_id": super_admin.guarnicao_id,
            "sid": super_admin.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def delegado(db_session, guarnicao):
    """Fixture de admin delegado (is_admin) sem toggles, com sessão ativa."""
    u = Usuario(
        nome="Delegado",
        matricula="DEL001",
        senha_hash=hash_senha("x"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        session_id="del-sid",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def delegado_headers(delegado):
    """Headers Bearer do admin delegado."""
    token = criar_access_token(
        {
            "sub": str(delegado.id),
            "guarnicao_id": delegado.guarnicao_id,
            "sid": delegado.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_promover_mantem_equipe(client: AsyncClient, super_headers, usuario):
    """Promover liga toggles e mantém o guarnicao_id do usuário."""
    equipe_antes = usuario.guarnicao_id
    resp = await client.put(
        f"/api/v1/admin/usuarios/{usuario.id}/admin",
        json={"is_admin": True, "pode_criar_usuario": True},
        headers=super_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_admin"] is True
    assert body["pode_criar_usuario"] is True
    assert body["guarnicao_id"] == equipe_antes


@pytest.mark.asyncio
async def test_listar_admins(client: AsyncClient, super_headers, usuario):
    """GET /admin/admins lista os admins (inclui recém-promovido)."""
    await client.put(
        f"/api/v1/admin/usuarios/{usuario.id}/admin",
        json={"is_admin": True},
        headers=super_headers,
    )
    resp = await client.get("/api/v1/admin/admins", headers=super_headers)
    assert resp.status_code == 200
    ids = {a["id"] for a in resp.json()}
    assert usuario.id in ids


@pytest.mark.asyncio
async def test_delegado_nao_promove(client: AsyncClient, delegado_headers, usuario):
    """Admin delegado recebe 403 ao tentar promover alguém."""
    resp = await client.put(
        f"/api/v1/admin/usuarios/{usuario.id}/admin",
        json={"is_admin": True},
        headers=delegado_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delegado_nao_lista_admins(client: AsyncClient, delegado_headers):
    """Admin delegado recebe 403 ao tentar listar admins."""
    resp = await client.get("/api/v1/admin/admins", headers=delegado_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_super_nao_se_rebaixa(client: AsyncClient, super_headers, super_admin):
    """Super-admin não pode rebaixar a si mesmo (anti-lockout)."""
    resp = await client.put(
        f"/api/v1/admin/usuarios/{super_admin.id}/admin",
        json={"is_admin": False},
        headers=super_headers,
    )
    assert resp.status_code == 403
