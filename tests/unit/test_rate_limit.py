"""Testes do extrator de IP real e de chave por usuário para rate limiting.

Garante que X-Forwarded-For so eh honrado quando o request vem de um
proxy explicitamente confiavel. Atacante externo nao consegue inflar
o XFF para burlar rate limit.
"""

from unittest.mock import MagicMock

from app.core.rate_limit import _get_real_client_ip, _get_user_rate_limit_key
from app.core.security import criar_access_token


def _request(client_host: str | None, xff: str | None = None) -> MagicMock:
    req = MagicMock()
    if client_host is None:
        req.client = None
    else:
        req.client = MagicMock(host=client_host)
    req.headers = {"x-forwarded-for": xff} if xff else {}
    return req


def test_ignora_xff_de_cliente_nao_confiavel(monkeypatch):
    """XFF de cliente fora da lista TRUSTED_PROXIES deve ser ignorado."""
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    req = _request(client_host="8.8.8.8", xff="1.2.3.4")
    assert _get_real_client_ip(req) == "8.8.8.8"


def test_aceita_xff_de_proxy_confiavel(monkeypatch):
    """XFF de proxy listado em TRUSTED_PROXIES deve ser honrado (primeiro IP da cadeia)."""
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    req = _request(client_host="127.0.0.1", xff="1.2.3.4, 10.0.0.1")
    assert _get_real_client_ip(req) == "1.2.3.4"


def test_sem_xff_retorna_client_host(monkeypatch):
    """Sem XFF, sempre retorna o client.host (independente de ser proxy)."""
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    req = _request(client_host="127.0.0.1")
    assert _get_real_client_ip(req) == "127.0.0.1"


def test_request_sem_client_retorna_unknown(monkeypatch):
    """Fallback para 'unknown' quando request.client eh None."""
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    req = _request(client_host=None)
    assert _get_real_client_ip(req) == "unknown"


def test_aceita_xff_de_hostname_confiavel_resolvido(monkeypatch):
    """XFF é honrado quando client_host resolve para um TRUSTED_PROXY_HOSTNAMES.

    Achado #14/2026-07-13: em produção a API vê o container do Caddy (IP da
    rede Docker bridge), não loopback — TRUSTED_PROXIES sozinho nunca batia.
    """
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXY_HOSTNAMES", ["caddy"])
    def _resolve(host):
        return "172.20.0.5" if host == "caddy" else "0.0.0.0"

    monkeypatch.setattr("app.core.rate_limit.socket.gethostbyname", _resolve)
    req = _request(client_host="172.20.0.5", xff="1.2.3.4")
    assert _get_real_client_ip(req) == "1.2.3.4"


def test_ignora_xff_quando_hostname_nao_resolve_para_client_host(monkeypatch):
    """client_host que não bate com o IP resolvido do hostname confiável não é honrado."""
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXY_HOSTNAMES", ["caddy"])
    monkeypatch.setattr("app.core.rate_limit.socket.gethostbyname", lambda host: "172.20.0.5")
    req = _request(client_host="8.8.8.8", xff="1.2.3.4")
    assert _get_real_client_ip(req) == "8.8.8.8"


def test_falha_de_resolucao_dns_nao_confia_fail_closed(monkeypatch):
    """Falha ao resolver o hostname confiável não deve quebrar nem confiar por engano."""
    import socket as socket_module

    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", [])
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXY_HOSTNAMES", ["caddy"])

    def _raise(host):
        raise socket_module.gaierror("nome não resolvido")

    monkeypatch.setattr("app.core.rate_limit.socket.gethostbyname", _raise)
    req = _request(client_host="172.20.0.5", xff="1.2.3.4")
    assert _get_real_client_ip(req) == "172.20.0.5"


def _request_com_auth(
    client_host: str = "8.8.8.8",
    authorization: str | None = None,
    cookie_token: str | None = None,
) -> MagicMock:
    req = MagicMock()
    req.client = MagicMock(host=client_host)
    req.headers = {"authorization": authorization} if authorization else {}
    req.cookies = {"argus_access_token": cookie_token} if cookie_token else {}
    return req


def test_user_key_usa_sub_do_bearer_token():
    """Chave por usuário deriva do claim sub do Bearer token, não do IP."""
    token = criar_access_token({"sub": "42", "sid": "s1"})
    req = _request_com_auth(client_host="1.2.3.4", authorization=f"Bearer {token}")
    assert _get_user_rate_limit_key(req) == "user:42"


def test_user_key_usa_sub_do_cookie_quando_sem_header():
    """Sem header Authorization, cai para o cookie HttpOnly (mesma fonte do get_current_user)."""
    token = criar_access_token({"sub": "7", "sid": "s1"})
    req = _request_com_auth(client_host="1.2.3.4", cookie_token=token)
    assert _get_user_rate_limit_key(req) == "user:7"


def test_user_key_dois_usuarios_diferentes_geram_chaves_diferentes():
    """Dois usuários no mesmo IP não compartilham o mesmo budget de rate limit."""
    token_a = criar_access_token({"sub": "1", "sid": "s1"})
    token_b = criar_access_token({"sub": "2", "sid": "s2"})
    req_a = _request_com_auth(client_host="1.2.3.4", authorization=f"Bearer {token_a}")
    req_b = _request_com_auth(client_host="1.2.3.4", authorization=f"Bearer {token_b}")
    assert _get_user_rate_limit_key(req_a) != _get_user_rate_limit_key(req_b)


def test_user_key_sem_token_valido_cai_para_ip(monkeypatch):
    """Sem token válido, usa o IP real (a rota autenticada rejeitaria antes de chegar aqui)."""
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", [])
    req = _request_com_auth(client_host="9.9.9.9", authorization="Bearer token-invalido")
    assert _get_user_rate_limit_key(req) == "9.9.9.9"
