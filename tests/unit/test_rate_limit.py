"""Testes do extrator de IP real para rate limiting.

Garante que X-Forwarded-For so eh honrado quando o request vem de um
proxy explicitamente confiavel. Atacante externo nao consegue inflar
o XFF para burlar rate limit.
"""

from unittest.mock import MagicMock

import pytest

from app.core.rate_limit import _get_real_client_ip


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
