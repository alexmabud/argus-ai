"""Testes dos headers de seguranca emitidos pelo SecurityHeadersMiddleware.

Garante que a CSP nao volte a permitir 'unsafe-inline' por engano —
remocao do unico onclick inline (app.js:555 -> data-navigate-to) abriu
espaco para apertar a politica.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


def _extrair_diretiva(csp: str, nome: str) -> str:
    """Retorna o valor (tokens) de uma diretiva CSP especifica."""
    for parte in csp.split(";"):
        parte = parte.strip()
        if parte.startswith(nome + " "):
            return parte
    return ""


@pytest.mark.asyncio
async def test_csp_script_src_nao_permite_unsafe_inline():
    """script-src nao deve mais ter 'unsafe-inline' (vetor principal de XSS).

    'unsafe-eval' continua presente — exigido pelo Alpine.js padrao para
    interpretar expressoes x-data/x-show. Migrar pro build alpinejs/csp
    seria refactor amplo, fora do escopo de Task 15.

    style-src 'unsafe-inline' permanece: muitos templates de app.js usam
    style="..." inline para animacoes — remover exigiria refactor amplo
    do frontend, fora do escopo.
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    csp = resp.headers.get("content-security-policy", "")
    script_src = _extrair_diretiva(csp, "script-src")
    assert script_src, "CSP deve declarar script-src"
    assert "'unsafe-inline'" not in script_src
