"""Teste e2e: componente de modal de confirmação customizado (confirm-dialog.js).

Cobre o slice "componente de modal de confirmação" da feature de exclusão
segura de abordado/veículo/foto: modal reutilizável (estilo glass-card do
app) que substitui `window.confirm()` nos fluxos de remoção, com mensagem
parametrizável e callback de confirmação disparado só quando o usuário
confirma explicitamente.

O teste dirige os arquivos REAIS do frontend (copiados no momento do
teste) num harness HTML mínimo, via Playwright/Chromium headless.

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
    shutil.copy(FRONTEND_JS / "components" / "confirm-dialog.js", tmp_path / "confirm-dialog.js")
    shutil.copy(FRONTEND_CSS / "app.css", tmp_path / "app.css")
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "confirm_dialog.html", tmp_path / "confirm_dialog.html")
    return tmp_path / "confirm_dialog.html"


def test_abre_com_mensagem_customizada_e_dois_botoes(harness: Path) -> None:
    """Disparar abrirConfirmacao() mostra a mensagem e os botões confirmar/cancelar."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(200)

        page.get_by_role("button", name="Testar remoção").click()
        page.wait_for_timeout(100)

        estado = page.evaluate("__state()")
        confirmar_visivel = page.get_by_role("button", name="Remover").is_visible()
        cancelar_visivel = page.get_by_role("button", name="Cancelar").is_visible()
        browser.close()

    assert estado["visivel"] is True
    assert estado["mensagem"] == "Remover este item? Esta ação não pode ser desfeita."
    assert confirmar_visivel
    assert cancelar_visivel


def test_confirmar_dispara_callback_e_fecha(harness: Path) -> None:
    """Clicar em "Remover" chama o callback fornecido e fecha o modal."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(200)

        page.get_by_role("button", name="Testar remoção").click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Remover").click()
        page.wait_for_timeout(100)

        estado = page.evaluate("__state()")
        browser.close()

    assert estado["confirmado"] is True
    assert estado["visivel"] is False


def test_cancelar_fecha_sem_disparar_callback(harness: Path) -> None:
    """Clicar em "Cancelar" fecha o modal sem chamar o callback."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(200)

        page.get_by_role("button", name="Testar remoção").click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Cancelar").click()
        page.wait_for_timeout(100)

        estado = page.evaluate("__state()")
        browser.close()

    assert estado["confirmado"] is None
    assert estado["visivel"] is False


def test_clicar_fora_fecha_sem_disparar_callback(harness: Path) -> None:
    """Clicar no backdrop (fora do card) fecha o modal sem chamar o callback."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(200)

        page.get_by_role("button", name="Testar remoção").click()
        page.wait_for_timeout(100)
        # Clica dentro da faixa vertical do overlay (abaixo de --header-height,
        # 56px) mas fora do card centralizado (max-width 400px), garantindo
        # que o alvo do clique seja o backdrop e não o card de confirmação.
        page.mouse.click(10, 100)
        page.wait_for_timeout(100)

        estado = page.evaluate("__state()")
        browser.close()

    assert estado["confirmado"] is None
    assert estado["visivel"] is False
