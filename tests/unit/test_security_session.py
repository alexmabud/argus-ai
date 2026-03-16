"""Testes de segurança — session_id embutido nos tokens JWT.

Documenta o comportamento de propagação de claims customizados (como sid — session_id)
através dos tokens JWT. Verifica que qualquer claim no dicionário `data` é automaticamente
embutido no token, permitindo rastreamento de sessões e auditoria de autenticação.
"""

from app.core.security import criar_access_token, criar_refresh_token, decodificar_token


def test_access_token_inclui_session_id():
    """Verifica que session_id é embutido no access token.

    Valida que claims customizados (como 'sid') passados via dicionário `data`
    são inclusos no token JWT e podem ser recuperados após decodificação.
    """
    token = criar_access_token({"sub": "1", "sid": "meu-session-id"})
    payload = decodificar_token(token)
    assert payload["sid"] == "meu-session-id"


def test_refresh_token_inclui_session_id():
    """Verifica que session_id é embutido no refresh token.

    Valida que claims customizados (como 'sid') funcionam igualmente em tokens
    de refresh, permitindo rastreamento de sessão através de múltiplas renovações.
    """
    token = criar_refresh_token({"sub": "1", "sid": "meu-session-id"})
    payload = decodificar_token(token, expected_type="refresh")
    assert payload["sid"] == "meu-session-id"


def test_token_sem_session_id_decodifica_normalmente():
    """Verifica backward compatibility — tokens sem sid ainda decodificam.

    Garante que tokens criados antes da implementação de rastreamento de sessão
    (sem claim 'sid') continuam funcionando normalmente, sem erros na decodificação.
    """
    token = criar_access_token({"sub": "1"})
    payload = decodificar_token(token)
    assert payload["sub"] == "1"
    assert payload.get("sid") is None


def test_multiplos_claims_customizados():
    """Verifica propagação de múltiplos claims customizados.

    Valida que vários claims além de 'sub' e 'sid' são preservados corretamente,
    permitindo uso de dados adicionais em contextos de auditoria ou autorização.
    """
    data = {
        "sub": "user-123",
        "sid": "session-456",
        "guarnicao_id": 5,
        "role": "operador",
    }
    token = criar_access_token(data)
    payload = decodificar_token(token)
    assert payload["sub"] == "user-123"
    assert payload["sid"] == "session-456"
    assert payload["guarnicao_id"] == 5
    assert payload["role"] == "operador"


def test_access_token_tem_tipo_correto():
    """Verifica que access token possui tipo 'access'.

    Valida que o campo 'type' do token é corretamente setado, permitindo
    validação de tipo durante decodificação e prevenção de confusão entre
    tokens de acesso e refresh.
    """
    token = criar_access_token({"sub": "1"})
    payload = decodificar_token(token, expected_type="access")
    assert payload["type"] == "access"


def test_refresh_token_tem_tipo_correto():
    """Verifica que refresh token possui tipo 'refresh'.

    Valida que refresh tokens são corretamente marcados, impedindo seu uso
    em contextos que exigem access tokens.
    """
    token = criar_refresh_token({"sub": "1"})
    payload = decodificar_token(token, expected_type="refresh")
    assert payload["type"] == "refresh"


def test_refresh_token_rejeitado_como_access():
    """Verifica que refresh token não passa validação de access token.

    Garante separação funcional entre tipos de token, prevenindo reutilização
    de refresh tokens em contextos que exigem access tokens.
    """
    token = criar_refresh_token({"sub": "1", "sid": "session-id"})
    payload = decodificar_token(token, expected_type="access")
    assert payload is None


def test_access_token_rejeitado_como_refresh():
    """Verifica que access token não passa validação de refresh token.

    Complementa validação de tipo de token, garantindo que access tokens
    não podem ser reutilizados para operações que exigem refresh tokens.
    """
    token = criar_access_token({"sub": "1", "sid": "session-id"})
    payload = decodificar_token(token, expected_type="refresh")
    assert payload is None
