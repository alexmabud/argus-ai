"""Testes do extrator de IP real e de chave por usuário para rate limiting.

Garante que X-Forwarded-For so eh honrado quando o request vem de um
proxy explicitamente confiavel. Atacante externo nao consegue inflar
o XFF para burlar rate limit.
"""

from unittest.mock import MagicMock

import pytest

from app.core.rate_limit import _get_real_client_ip, _get_user_rate_limit_key
from app.core.security import criar_access_token


@pytest.fixture(autouse=True)
def _cache_zerado_de_proxy_hostname(monkeypatch):
    """Zera o cache de _proxy_hostname_ips entre testes.

    _proxy_hostname_ips() cacheia a resolução DNS por 30s (revisão pós-#14/
    2026-07-13) — sem isto, o valor resolvido/mockado por um teste vazaria
    pro próximo dentro da mesma janela de 30s, quebrando isolamento entre
    testes que mockam socket.gethostbyname com resultados diferentes.
    """
    monkeypatch.setattr("app.core.rate_limit._proxy_hostname_ips_cached_at", 0.0)
    monkeypatch.setattr("app.core.rate_limit._proxy_hostname_ips_cache", set())


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
    """XFF de proxy listado em TRUSTED_PROXIES deve ser honrado (último IP da cadeia).

    Achado de revisão pós-#14/2026-07-13: o Caddy deste deploy anexa o IP que
    observou ao XFF recebido em vez de substituí-lo (sem `trusted_proxies`
    configurado) — o ÚLTIMO IP é o que o proxy confiável de fato viu; os
    anteriores podem ter sido forjados por quem originou a requisição.
    """
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    req = _request(client_host="127.0.0.1", xff="1.2.3.4, 10.0.0.1")
    assert _get_real_client_ip(req) == "10.0.0.1"


def test_xff_com_prefixo_forjado_pelo_atacante_eh_ignorado(monkeypatch):
    """Atacante que envia X-Forwarded-For direto não consegue forjar o IP usado no rate limit.

    Regressão do achado de revisão pós-#14: como o Caddy anexa (não
    substitui) o XFF recebido, um atacante que force
    `X-Forwarded-For: <ip-forjado>` chega à API como
    `X-Forwarded-For: <ip-forjado>, <ip-real-visto-pelo-caddy>`. Tomar o
    primeiro IP (comportamento antigo) deixava o atacante escolher a chave do
    rate limit livremente, bastando variar o header a cada requisição.
    """
    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXIES", ["127.0.0.1"])
    req = _request(client_host="127.0.0.1", xff="1.2.3.4, 5.5.5.5, 9.9.9.9")
    assert _get_real_client_ip(req) == "9.9.9.9"


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


def test_proxy_hostname_ips_cacheia_dentro_do_ttl(monkeypatch):
    """Dentro do TTL, _proxy_hostname_ips não chama socket.gethostbyname de novo.

    Revisão pós-#14/2026-07-13: socket.gethostbyname é uma chamada
    bloqueante de rede dentro do key_func síncrono do slowapi (sem await
    possível) — sem cache, rodava em TODO request de rota rate-limited,
    travando o event loop asyncio sob DNS lento. O cache de 30s elimina isso
    no caminho comum.
    """
    import app.core.rate_limit as rate_limit_module

    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXY_HOSTNAMES", ["caddy"])
    chamadas = []

    def _resolve(host):
        chamadas.append(host)
        return "172.20.0.5"

    monkeypatch.setattr("app.core.rate_limit.socket.gethostbyname", _resolve)

    primeira = rate_limit_module._proxy_hostname_ips()
    segunda = rate_limit_module._proxy_hostname_ips()

    assert primeira == segunda == {"172.20.0.5"}
    assert len(chamadas) == 1


def test_proxy_hostname_ips_reresolve_apos_expirar_ttl(monkeypatch):
    """Após o TTL expirar, _proxy_hostname_ips resolve de novo (não fica preso a IP obsoleto)."""
    import app.core.rate_limit as rate_limit_module

    monkeypatch.setattr("app.core.rate_limit.settings.TRUSTED_PROXY_HOSTNAMES", ["caddy"])
    monkeypatch.setattr("app.core.rate_limit.socket.gethostbyname", lambda host: "172.20.0.5")

    primeira = rate_limit_module._proxy_hostname_ips()
    # Simula o TTL expirado sem depender de sleep real no teste.
    monkeypatch.setattr("app.core.rate_limit._proxy_hostname_ips_cached_at", 0.0)
    monkeypatch.setattr("app.core.rate_limit.socket.gethostbyname", lambda host: "172.20.0.9")
    segunda = rate_limit_module._proxy_hostname_ips()

    assert primeira == {"172.20.0.5"}
    assert segunda == {"172.20.0.9"}


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
