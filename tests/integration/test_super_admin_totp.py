"""TOTP obrigatório para super-admin (achado #03/2026-07-13).

``definir_super_admin.py`` só liga ``is_super_admin`` (nunca ``is_admin``), e
o login antigo checava só ``is_admin`` para exigir TOTP — a conta mais
privilegiada do sistema logava só com senha mesmo com 2FA configurado. Cobre
a exigência de TOTP para super-admin e a paridade de semântica de sessão
(senha permanente, session_id estável) com o admin comum.
"""

import pyotp
import pytest

from app.core.crypto import encrypt
from app.core.exceptions import CredenciaisInvalidasError
from app.core.security import hash_senha, verificar_senha
from app.models.usuario import Usuario
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_super_admin_com_totp_configurado_exige_codigo(db_session, guarnicao):
    """Super-admin com totp_secret não pode logar só com senha."""
    dono = Usuario(
        nome="Dono do Sistema",
        matricula="DONO001",
        senha_hash=hash_senha("senha-forte"),
        guarnicao_id=guarnicao.id,
        is_admin=False,
        is_super_admin=True,
        totp_secret=encrypt(pyotp.random_base32()),
    )
    db_session.add(dono)
    await db_session.flush()

    svc = AuthService(db_session)
    with pytest.raises(CredenciaisInvalidasError):
        await svc.login("DONO001", "senha-forte")


@pytest.mark.asyncio
async def test_super_admin_com_totp_configurado_loga_com_codigo_correto(db_session, guarnicao):
    """Super-admin com TOTP correto completa o login normalmente."""
    secret = pyotp.random_base32()
    dono = Usuario(
        nome="Dono do Sistema",
        matricula="DONO002",
        senha_hash=hash_senha("senha-forte"),
        guarnicao_id=guarnicao.id,
        is_admin=False,
        is_super_admin=True,
        totp_secret=encrypt(secret),
    )
    db_session.add(dono)
    await db_session.flush()

    svc = AuthService(db_session)
    codigo = pyotp.TOTP(secret).now()
    resposta = await svc.login("DONO002", "senha-forte", totp_code=codigo)

    assert resposta.access_token


@pytest.mark.asyncio
async def test_super_admin_sem_totp_secret_loga_sem_codigo_fase_bootstrap(db_session, guarnicao):
    """Sem totp_secret ainda (pré-enrollment), login segue sem exigir TOTP."""
    dono = Usuario(
        nome="Dono do Sistema",
        matricula="DONO003",
        senha_hash=hash_senha("senha-forte"),
        guarnicao_id=guarnicao.id,
        is_admin=False,
        is_super_admin=True,
        totp_secret=None,
    )
    db_session.add(dono)
    await db_session.flush()

    svc = AuthService(db_session)
    resposta = await svc.login("DONO003", "senha-forte")

    assert resposta.access_token


@pytest.mark.asyncio
async def test_super_admin_sem_is_admin_tem_senha_permanente_e_sessao_estavel(
    db_session, guarnicao
):
    """Super-admin (is_admin=False) não deve cair na semântica de usuário comum.

    Sem essa paridade, ao exigir TOTP o super-admin ficaria com a senha
    invalidada (uso único) a cada login — quebrando o próprio acesso da
    conta que o fix de TOTP deveria proteger.
    """
    dono = Usuario(
        nome="Dono do Sistema",
        matricula="DONO004",
        senha_hash=hash_senha("senha-forte"),
        guarnicao_id=guarnicao.id,
        is_admin=False,
        is_super_admin=True,
    )
    db_session.add(dono)
    await db_session.flush()

    svc = AuthService(db_session)
    await svc.login("DONO004", "senha-forte")
    await db_session.refresh(dono)

    assert verificar_senha("senha-forte", dono.senha_hash), "senha não deveria virar uso único"
    assert dono.session_id is not None
