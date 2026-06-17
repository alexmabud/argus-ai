"""Testes de permissão granular e scope nos endpoints de gestão do admin."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


def _headers(u: Usuario) -> dict:
    """Monta headers Bearer para um usuário com sessão ativa."""
    token = criar_access_token(
        {"sub": str(u.id), "guarnicao_id": u.guarnicao_id, "sid": u.session_id}
    )
    return {"Authorization": f"Bearer {token}"}


async def _delegado(db_session, guarnicao_id, **flags) -> Usuario:
    """Cria um admin delegado com flags específicas e sessão ativa.

    Args:
        db_session: Sessão de teste.
        guarnicao_id: Guarnição do delegado.
        **flags: Toggles pode_* / admin_global a ligar.

    Returns:
        Usuario delegado persistido.
    """
    u = Usuario(
        nome="Delegado",
        matricula=f"DEL{id(flags) % 100000}",
        senha_hash=hash_senha("x"),
        guarnicao_id=guarnicao_id,
        is_admin=True,
        session_id="del-sid",
        **flags,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def outra_guarnicao(db_session, bpm) -> Guarnicao:
    """Segunda guarnição para testes de scope cross-equipe."""
    g = Guarnicao(nome="GU OUTRA", bpm_id=bpm.id, codigo="OUT-001")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def super_admin(db_session, guarnicao) -> Usuario:
    """Super-admin com sessão ativa."""
    u = Usuario(
        nome="Dono",
        matricula="DONO_SC",
        senha_hash=hash_senha("x"),
        guarnicao_id=guarnicao.id,
        is_super_admin=True,
        session_id="dono-sid",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.mark.asyncio
async def test_criar_na_propria_equipe_ok(client: AsyncClient, db_session, guarnicao):
    """Delegado local (admin_global=False) cria usuário na própria guarnição → 201."""
    delegado = await _delegado(db_session, guarnicao.id, pode_criar_usuario=True)
    resp = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "NA_MINHA", "guarnicao_id": guarnicao.id},
        headers=_headers(delegado),
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_criar_em_outra_equipe_bloqueado(
    client: AsyncClient, db_session, guarnicao, outra_guarnicao
):
    """Delegado local não cria usuário em outra guarnição → 403."""
    delegado = await _delegado(db_session, guarnicao.id, pode_criar_usuario=True)
    resp = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "NA_OUTRA", "guarnicao_id": outra_guarnicao.id},
        headers=_headers(delegado),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sem_pode_gerar_senha_bloqueado(client: AsyncClient, db_session, guarnicao, usuario):
    """Delegado sem pode_gerar_senha → 403 ao gerar senha."""
    delegado = await _delegado(db_session, guarnicao.id, pode_criar_usuario=True)
    resp = await client.post(
        f"/api/v1/admin/usuarios/{usuario.id}/gerar-senha",
        headers=_headers(delegado),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sem_pode_pausar_bloqueado(client: AsyncClient, db_session, guarnicao, usuario):
    """Delegado sem pode_pausar → 403 ao pausar."""
    delegado = await _delegado(db_session, guarnicao.id, pode_gerar_senha=True)
    resp = await client.patch(
        f"/api/v1/admin/usuarios/{usuario.id}/pausar",
        headers=_headers(delegado),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_excluir_apenas_super_admin(client: AsyncClient, db_session, guarnicao, usuario):
    """Delegado com TODOS os toggles ainda recebe 403 ao excluir."""
    delegado = await _delegado(
        db_session,
        guarnicao.id,
        pode_criar_usuario=True,
        pode_gerar_senha=True,
        pode_pausar=True,
        pode_mover_equipe=True,
        pode_gerir_equipes=True,
        admin_global=True,
    )
    resp = await client.delete(f"/api/v1/admin/usuarios/{usuario.id}", headers=_headers(delegado))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_excluir_super_admin_ok(client: AsyncClient, super_admin, usuario):
    """Super-admin exclui usuário → 204."""
    resp = await client.delete(
        f"/api/v1/admin/usuarios/{usuario.id}", headers=_headers(super_admin)
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_gerir_equipes_exige_global(client: AsyncClient, db_session, guarnicao, bpm):
    """Delegado com pode_gerir_equipes mas admin_global=False → 403 ao criar equipe."""
    delegado = await _delegado(db_session, guarnicao.id, pode_gerir_equipes=True)
    resp = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": "Nova GU", "bpm_id": bpm.id},
        headers=_headers(delegado),
    )
    assert resp.status_code == 403
