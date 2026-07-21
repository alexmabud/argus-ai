"""Teste e2e: remoção de foto na ficha do abordado (admin-only).

Cobre o slice "remover foto na ficha do abordado" da feature de exclusão
segura: o "✕" admin-only que ficava direto na miniatura (rosto ou
evidência) some — a remoção passa a exigir abrir a foto ampliada e usar
a lixeira lá dentro (visível só para admin), com confirmação customizada
(`confirmDialog`), em vez do `confirm()` nativo que existia antes.

O teste dirige os arquivos REAIS do frontend (copiados no momento do
teste) num harness HTML com a API estubada, via Playwright/Chromium
headless. Reaproveita o harness de test_pessoa_detalhe_veiculos.py
(pessoa_detalhe.html).

Opt-in: requer ``pip install playwright && playwright install chromium``.
Sem isso, o teste é pulado.
"""

import shutil
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="playwright não instalado")

from playwright.sync_api import Error as PlaywrightError  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_JS = REPO_ROOT / "frontend" / "js"
FRONTEND_CSS = REPO_ROOT / "frontend" / "css"
HARNESS_DIR = Path(__file__).parent / "harness"


@pytest.fixture
def harness(tmp_path: Path) -> Path:
    """Monta o harness em diretório temporário com os arquivos reais do frontend.

    Returns:
        Caminho do HTML do harness pronto para abrir via file://.
    """
    shutil.copy(
        FRONTEND_JS / "components" / "person-photo-modal.js", tmp_path / "person-photo-modal.js"
    )
    shutil.copy(
        FRONTEND_JS / "components" / "veiculo-ficha-form.js", tmp_path / "veiculo-ficha-form.js"
    )
    shutil.copy(FRONTEND_JS / "components" / "confirm-dialog.js", tmp_path / "confirm-dialog.js")
    shutil.copy(FRONTEND_JS / "pages" / "pessoa-detalhe.js", tmp_path / "pessoa-detalhe.js")
    shutil.copy(FRONTEND_CSS / "app.css", tmp_path / "app.css")
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "pessoa_detalhe.html", tmp_path / "pessoa_detalhe.html")
    return tmp_path / "pessoa_detalhe.html"


def _pessoa_com_fotos() -> str:
    return """
        window.__pessoa = {
          id: 1, nome: 'FULANO EXISTENTE', cpf_masked: '***.456.789-**',
          apelido: null, data_nascimento: null, nome_mae: null, enderecos: [],
          relacionamentos: [],
        };
        window.__fotos = [
          { id: 501, tipo: 'rosto', arquivo_url: 'https://example.test/rosto.jpg' },
          { id: 502, tipo: 'tatuagem', arquivo_url: 'https://example.test/evidencia.jpg' },
        ];
    """


def test_admin_apaga_foto_de_rosto_via_foto_ampliada(harness: Path) -> None:
    """Admin remove uma foto de rosto via lixeira na foto ampliada."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1, is_admin: true };" + _pessoa_com_fotos())
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        estado_antes = page.evaluate("__state()")
        assert 501 in estado_antes["fotoIds"]

        page.locator('img[src="https://example.test/rosto.jpg"]').click()
        page.wait_for_timeout(100)
        page.locator('button[title="Apagar foto"]').click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Remover").click()
        page.wait_for_timeout(200)

        estado_depois = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 501 not in estado_depois["fotoIds"]
    deletes = [c for c in calls["deletes"] if c["url"] == "/fotos/501"]
    assert len(deletes) == 1


def test_admin_apaga_foto_de_evidencia_via_foto_ampliada(harness: Path) -> None:
    """Admin remove uma foto de evidência via lixeira na foto ampliada."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1, is_admin: true };" + _pessoa_com_fotos())
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.locator('img[src="https://example.test/evidencia.jpg"]').click()
        page.wait_for_timeout(100)
        page.locator('button[title="Apagar foto"]').click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Remover").click()
        page.wait_for_timeout(200)

        estado_depois = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 502 not in estado_depois["fotoIds"]
    deletes = [c for c in calls["deletes"] if c["url"] == "/fotos/502"]
    assert len(deletes) == 1


def test_cancelar_confirmacao_nao_apaga_foto(harness: Path) -> None:
    """Cancelar a confirmação mantém a foto."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1, is_admin: true };" + _pessoa_com_fotos())
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.locator('img[src="https://example.test/rosto.jpg"]').click()
        page.wait_for_timeout(100)
        page.locator('button[title="Apagar foto"]').click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Cancelar").click()
        page.wait_for_timeout(200)

        estado_depois = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 501 in estado_depois["fotoIds"]
    assert calls["deletes"] == []


def test_nao_admin_nao_ve_lixeira_na_foto_ampliada(harness: Path) -> None:
    """Usuário não-admin não vê a lixeira em nenhuma foto ampliada."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };" + _pessoa_com_fotos())
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.locator('img[src="https://example.test/rosto.jpg"]').click()
        page.wait_for_timeout(100)
        lixeira = page.locator('button[title="Apagar foto"]')
        visivel = lixeira.count() > 0 and lixeira.is_visible()
        browser.close()

    assert not visivel


def test_miniaturas_nao_tem_mais_botao_apagar_direto(harness: Path) -> None:
    """As miniaturas de foto não têm mais o "✕" direto, nem para admin."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1, is_admin: true };" + _pessoa_com_fotos())
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        lixeira_direta = page.locator('button[title="Apagar foto"]')
        visivel_antes_de_ampliar = lixeira_direta.count() > 0 and lixeira_direta.is_visible()
        browser.close()

    assert not visivel_antes_de_ampliar
