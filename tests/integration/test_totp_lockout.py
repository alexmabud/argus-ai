"""Teste de lockout do TOTP (Grupo 10 — segurança).

Garante que um TOTP errado (com senha correta) CONTA para o contador de
tentativas e bloqueia a conta — senão um atacante que já tem a senha do admin
faria brute-force do código de 6 dígitos sem nunca disparar o lockout.
"""

import pyotp
import pytest

from app.core.crypto import encrypt
from app.core.exceptions import ContaBloqueadaError, CredenciaisInvalidasError
from app.core.security import hash_senha
from app.models.usuario import Usuario
from app.services.auth_service import LIMIAR_BLOQUEIO, AuthService


@pytest.mark.asyncio
async def test_totp_errado_conta_para_lockout(db_session, guarnicao):
    """Após LIMIAR_BLOQUEIO TOTPs errados, a conta admin é bloqueada.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição.
    """
    admin = Usuario(
        nome="Admin TOTP",
        matricula="ADMTOTP",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        session_id="sess-totp",
        is_admin=True,
        totp_secret=encrypt(pyotp.random_base32()),
    )
    db_session.add(admin)
    await db_session.flush()

    svc = AuthService(db_session)

    # Senha correta + TOTP errado, LIMIAR vezes → cada uma incrementa o contador.
    for _ in range(LIMIAR_BLOQUEIO):
        with pytest.raises(CredenciaisInvalidasError):
            await svc.login("ADMTOTP", "senha123", totp_code="000000")

    await db_session.refresh(admin)
    assert admin.bloqueado_ate is not None  # lockout disparou pelo TOTP errado

    # Já bloqueada: a próxima tentativa nem chega a verificar o TOTP.
    with pytest.raises(ContaBloqueadaError):
        await svc.login("ADMTOTP", "senha123", totp_code="000000")
