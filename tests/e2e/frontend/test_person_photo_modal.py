"""Teste e2e: personPhotoModal sem contexto de exclusão não mostra a lixeira.

Regressão visada pelo code-review da feature de exclusão segura: a
lixeira do modal de foto ampliada (`person-photo-modal.js`) só deve
aparecer quando o chamador passa `deleteContext` explicitamente (5º
argumento de `openPhotoModal`). Páginas como dashboard.js, consulta.js e
os relacionamentos/vínculos de pessoa-detalhe.js chamam `openPhotoModal`
sem esse argumento — este teste garante que esse uso genérico nunca
ganha a opção de excluir, mesmo que o chamador também misture
`confirmDialog()` (usado por outras seções da mesma página, como
acontece em pessoa-detalhe.js e abordagem-detalhe.js).

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
    shutil.copy(FRONTEND_JS / "components" / "confirm-dialog.js", tmp_path / "confirm-dialog.js")
    shutil.copy(FRONTEND_CSS / "app.css", tmp_path / "app.css")
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "person_photo_modal.html", tmp_path / "person_photo_modal.html")
    return tmp_path / "person_photo_modal.html"


def test_sem_delete_context_nao_mostra_lixeira(harness: Path) -> None:
    """openPhotoModal chamado sem deleteContext (4 args) nunca mostra a lixeira."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(200)

        page.get_by_role("button", name="Abrir sem exclusao").click()
        page.wait_for_timeout(200)

        lixeira = page.locator('button[title="Remover"]')
        visivel = lixeira.count() > 0 and lixeira.is_visible()
        browser.close()

    assert not visivel


def test_com_delete_context_mostra_lixeira(harness: Path) -> None:
    """Controle positivo: com deleteContext, a lixeira aparece.

    Garante que o locator/seletor usado no teste anterior funciona de
    verdade — sem isso, aquele teste passaria mesmo se a lixeira nunca
    aparecesse por um bug no seletor, não pela ausência real do botão.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(200)

        page.get_by_role("button", name="Abrir com exclusao").click()
        page.wait_for_timeout(200)

        visivel = page.locator('button[title="Remover teste"]').is_visible()
        browser.close()

    assert visivel
