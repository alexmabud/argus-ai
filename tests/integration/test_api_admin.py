"""Testes do painel admin — gestão de usuários."""

import pyotp
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


@pytest.mark.asyncio
async def test_listar_usuarios_inclui_sem_equipe(client: AsyncClient, admin_headers, db_session):
    """GET /admin/usuarios inclui usuários sem equipe (guarnicao_id=None)."""
    from app.core.security import hash_senha
    from app.models.usuario import Usuario

    sem_equipe = Usuario(
        nome="Sem Equipe",
        matricula="ZZ001",
        senha_hash=hash_senha("xxxx"),
        guarnicao_id=None,
    )
    db_session.add(sem_equipe)
    await db_session.flush()

    response = await client.get("/api/v1/admin/usuarios", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(u["id"] == sem_equipe.id and u["guarnicao_id"] is None for u in data)


@pytest.mark.asyncio
async def test_mover_usuario_equipe_atualiza(
    client: AsyncClient, admin_headers, usuario, db_session, bpm
):
    """PATCH /admin/usuarios/{id}/equipe move o usuário para outra equipe."""
    from app.models.guarnicao import Guarnicao

    nova = Guarnicao(nome="GU 77", bpm_id=bpm.id, codigo="7BPM-GU77")
    db_session.add(nova)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/admin/usuarios/{usuario.id}/equipe",
        json={"guarnicao_id": nova.id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guarnicao_id"] == nova.id


@pytest.mark.asyncio
async def test_mover_usuario_para_none(client: AsyncClient, admin_headers, usuario):
    """PATCH /admin/usuarios/{id}/equipe com guarnicao_id=None remove de equipe."""
    response = await client.patch(
        f"/api/v1/admin/usuarios/{usuario.id}/equipe",
        json={"guarnicao_id": None},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guarnicao_id"] is None


@pytest.mark.asyncio
async def test_mover_usuario_inexistente_404(client: AsyncClient, admin_headers):
    """PATCH em usuário inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/admin/usuarios/999999/equipe",
        json={"guarnicao_id": None},
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_explicita(
    client: AsyncClient, admin_headers, db_session, bpm
):
    """POST /admin/usuarios respeita guarnicao_id no payload."""
    from sqlalchemy import select

    from app.models.guarnicao import Guarnicao
    from app.models.usuario import Usuario

    nova = Guarnicao(nome="GU 88", bpm_id=bpm.id, codigo="8BPM-GU88")
    db_session.add(nova)
    await db_session.flush()

    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "PMNEW01", "guarnicao_id": nova.id},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["matricula"] == "PMNEW01"
    res = await db_session.execute(select(Usuario).where(Usuario.id == body["usuario_id"]))
    u = res.scalar_one()
    assert u.guarnicao_id == nova.id


@pytest.mark.asyncio
async def test_criar_usuario_sem_equipe(client: AsyncClient, admin_headers, db_session):
    """POST /admin/usuarios com guarnicao_id=None cria usuário sem equipe."""
    from sqlalchemy import select

    from app.models.usuario import Usuario

    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "PMSEM01", "guarnicao_id": None},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    res = await db_session.execute(select(Usuario).where(Usuario.id == body["usuario_id"]))
    u = res.scalar_one()
    assert u.guarnicao_id is None


@pytest.mark.asyncio
async def test_totp_setup_retorna_uri(client: AsyncClient, admin_headers, admin_usuario):
    """POST /admin/2fa/setup gera secret TOTP e retorna URI otpauth://.

    O secret é salvo cifrado no banco. A URI é compatível com Google Authenticator.
    """

    response = await client.post("/api/v1/admin/2fa/setup", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert "uri" in body
    assert body["uri"].startswith("otpauth://totp/")
    assert "Argus" in body["uri"]


@pytest.mark.asyncio
async def test_totp_setup_sem_admin_retorna_403(client: AsyncClient, auth_headers):
    """POST /admin/2fa/setup requer admin — usuário comum retorna 403."""
    response = await client.post("/api/v1/admin/2fa/setup", headers=auth_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_admin_com_totp_correto(client, db_session, guarnicao, admin_usuario):
    """Login do admin com TOTP configurado e código correto deve autenticar."""
    import pyotp

    from app.core.crypto import encrypt

    # Configurar secret TOTP para o admin
    secret = pyotp.random_base32()
    admin_usuario.totp_secret = encrypt(secret)
    admin_usuario.senha_hash = hash_senha("senha123")
    await db_session.flush()

    totp = pyotp.TOTP(secret)
    code = totp.now()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"matricula": "ADMIN001", "senha": "senha123", "totp_code": code},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_admin_com_totp_errado_retorna_401(
    client, db_session, guarnicao, admin_usuario
):
    """Login do admin com TOTP configurado e código errado retorna 401."""
    import pyotp

    from app.core.crypto import encrypt

    secret = pyotp.random_base32()
    admin_usuario.totp_secret = encrypt(secret)
    admin_usuario.senha_hash = hash_senha("senha123")
    await db_session.flush()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"matricula": "ADMIN001", "senha": "senha123", "totp_code": "000000"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_admin_sem_totp_configurado_funciona(
    client, db_session, guarnicao, admin_usuario
):
    """Login do admin sem totp_secret configurado deve funcionar (bootstrap)."""
    admin_usuario.senha_hash = hash_senha("senha123")
    admin_usuario.totp_secret = None
    await db_session.flush()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"matricula": "ADMIN001", "senha": "senha123"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_totp_errado_nao_reseta_fail_counter(client, db_session, guarnicao, admin_usuario):
    """Falha de TOTP com senha correta não deve zerar tentativas_falhas.

    Garante que um atacante com a senha não consiga fazer brute-force de
    TOTP sem acionar o bloqueio por conta (tentativas_falhas não é zerado
    quando o TOTP falha — apenas quando ambos passam).
    """

    from app.core.crypto import encrypt

    secret = pyotp.random_base32()
    admin_usuario.totp_secret = encrypt(secret)
    admin_usuario.senha_hash = hash_senha("senha123")
    admin_usuario.tentativas_falhas = 3
    await db_session.flush()

    # Senha correta + TOTP errado
    resp = await client.post(
        "/api/v1/auth/login",
        json={"matricula": "ADMIN001", "senha": "senha123", "totp_code": "000000"},
    )
    assert resp.status_code == 401

    await db_session.refresh(admin_usuario)
    # tentativas_falhas não deve ter sido zerada (era 3, deve continuar >= 3)
    assert admin_usuario.tentativas_falhas >= 3


@pytest.mark.asyncio
async def test_totp_setup_gera_audit_log(client, db_session, admin_headers, admin_usuario):
    """POST /admin/2fa/setup deve registrar evento 2FA_SETUP no audit log.

    Args:
        client: Cliente HTTP assincrónico.
        db_session: Sessão do banco de testes.
        admin_headers: Headers de autenticação do admin.
        admin_usuario: Fixture de usuário admin.
    """
    from sqlalchemy import select

    from app.models.audit_log import AuditLog

    await client.post("/api/v1/admin/2fa/setup", headers=admin_headers)

    result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.acao == "2FA_SETUP",
            AuditLog.usuario_id == admin_usuario.id,
        )
    )
    assert result.scalars().first() is not None


@pytest.mark.asyncio
async def test_totp_code_invalido_rejeita_nao_digito(client, usuario):
    """LoginRequest.totp_code deve rejeitar valor não-numérico.

    Args:
        client: Cliente HTTP assincrónico.
        usuario: Fixture de usuário.
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"matricula": "TEST001", "senha": "senha123", "totp_code": "abc123"},
    )
    assert resp.status_code == 422
