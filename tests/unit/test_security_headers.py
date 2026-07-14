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


@pytest.mark.asyncio
async def test_csp_ainda_permite_unsafe_eval_ate_migracao_do_alpine():
    """'unsafe-eval' permanece — remover exige build do Alpine sem eval.

    Decisão HITL em aberto (achado #30/2026-07-13): migrar Alpine.js para
    build sem eval é refactor amplo com risco real de regressão de UI,
    fora do escopo de um fix mecânico. Este teste documenta o estado atual
    para que uma remoção futura seja deliberada (o teste passa a falhar,
    sinalizando que a migração aconteceu).
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    csp = resp.headers.get("content-security-policy", "")
    script_src = _extrair_diretiva(csp, "script-src")
    assert "'unsafe-eval'" in script_src


@pytest.mark.asyncio
async def test_csp_nao_lista_cdns_orfas():
    """CSP não deve permitir origens de CDN que o frontend não usa mais.

    Achado #30/2026-07-13: jsdelivr/tailwindcss.com/unpkg/fonts.google* e
    nominatim.openstreetmap.org ficaram na CSP muito depois do frontend
    migrar pra vendor self-hosted (frontend/vendor/) e geocodificação
    reversa server-side (app/services/geocoding_service.py) — grep em
    frontend/ confirma zero referência real a essas origens. Cada uma
    listada era superfície extra pra uma eventual XSS carregar script de
    origem externa, sem nenhum benefício funcional.
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    csp = resp.headers.get("content-security-policy", "")
    origens_orfas = [
        "cdn.jsdelivr.net",
        "cdn.tailwindcss.com",
        "unpkg.com",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "nominatim.openstreetmap.org",
    ]
    for origem in origens_orfas:
        assert origem not in csp, f"CSP não deveria mais listar {origem}"


@pytest.mark.asyncio
async def test_csp_img_src_mantem_tile_openstreetmap_em_uso_real():
    """img-src mantém *.tile.openstreetmap.org — Leaflet busca tiles direto do browser.

    Diferente das CDNs removidas em test_csp_nao_lista_cdns_orfas, esta
    origem tem uso real confirmado (frontend/js/pages/*.js chamam
    L.tileLayer com essa URL) — não deve ser removida junto.
    """
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    csp = resp.headers.get("content-security-policy", "")
    img_src = _extrair_diretiva(csp, "img-src")
    assert "https://*.tile.openstreetmap.org" in img_src
