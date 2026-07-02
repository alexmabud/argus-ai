"""Testes unitários dos helpers de cookie de autenticação (app.core.auth_cookie).

Garante que os cookies de access/refresh são HttpOnly, SameSite=strict e com o
path correto, e que o clear os remove — antes sem cobertura (achado #5 do G9).
"""

from starlette.responses import Response

from app.core.auth_cookie import (
    ACCESS_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    clear_access_cookie,
    clear_refresh_cookie,
    set_access_cookie,
    set_refresh_cookie,
)


def _set_cookie_headers(response: Response) -> list[str]:
    """Retorna todos os headers Set-Cookie da resposta."""
    return [v.decode() for k, v in response.raw_headers if k == b"set-cookie"]


def test_set_access_cookie_httponly_samesite_strict():
    """O cookie de access é HttpOnly, SameSite=strict, path=/ e carrega o token."""
    resp = Response()
    set_access_cookie(resp, "jwt-access-123")
    cookies = _set_cookie_headers(resp)
    alvo = next(c for c in cookies if c.startswith(f"{ACCESS_TOKEN_COOKIE}="))
    assert "jwt-access-123" in alvo
    assert "HttpOnly" in alvo
    assert "samesite=strict" in alvo.lower()
    assert "Path=/" in alvo


def test_set_refresh_cookie_path_restrito_ao_refresh():
    """O cookie de refresh é HttpOnly e tem path restrito ao endpoint de refresh."""
    resp = Response()
    set_refresh_cookie(resp, "jwt-refresh-456")
    alvo = next(c for c in _set_cookie_headers(resp) if c.startswith(f"{REFRESH_TOKEN_COOKIE}="))
    assert "jwt-refresh-456" in alvo
    assert "HttpOnly" in alvo
    assert "samesite=strict" in alvo.lower()
    # Path mais restrito que "/" — não vaza o refresh token em toda requisição.
    assert "Path=/" in alvo and "refresh" in alvo.lower()


def test_clear_access_cookie_expira():
    """clear_access_cookie emite um Set-Cookie de expiração para o cookie de access."""
    resp = Response()
    clear_access_cookie(resp)
    cookies = _set_cookie_headers(resp)
    assert any(c.startswith(f"{ACCESS_TOKEN_COOKIE}=") for c in cookies)
    alvo = next(c for c in cookies if c.startswith(f"{ACCESS_TOKEN_COOKIE}="))
    assert "Max-Age=0" in alvo or "expires=Thu, 01 Jan 1970" in alvo.lower()


def test_clear_refresh_cookie_expira():
    """clear_refresh_cookie emite um Set-Cookie de expiração para o refresh."""
    resp = Response()
    clear_refresh_cookie(resp)
    assert any(c.startswith(f"{REFRESH_TOKEN_COOKIE}=") for c in _set_cookie_headers(resp))
