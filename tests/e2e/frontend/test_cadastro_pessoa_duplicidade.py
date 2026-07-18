"""Teste e2e: detecção de duplicidade ao digitar o nome no cadastro de pessoa.

Slice 1 de .scratch/deteccao-duplicidade-pessoa/: o modal de cadastro de
pessoa (compartilhado entre o botão "Cadastrar Nova Pessoa" da home e a
Consulta IA) busca, com debounce, pessoas já cadastradas com nome parecido
enquanto o operador digita — evitando cadastro duplicado.

O teste dirige os arquivos REAIS do frontend (copiados no momento do teste)
num harness HTML com a API estubada, via Playwright/Chromium headless.

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
HARNESS_DIR = Path(__file__).parent / "harness"

_STUB_JOAO = """
(() => {
  window.__consultaStub = (url) => {
    const q = new URL(url, 'http://x').searchParams.get('q') || '';
    if (q.toUpperCase().includes('JOAO')) {
      return {
        pessoas: [{
          id: 55,
          nome: 'JOAO DA SILVA',
          cpf_masked: '***.123.456-**',
          apelido: 'JOAOZINHO',
          data_nascimento: '1990-01-01',
          foto_principal_url: null,
        }],
      };
    }
    return { pessoas: [] };
  };
})();
"""


@pytest.fixture
def harness(tmp_path: Path) -> Path:
    """Monta o harness em diretório temporário com os arquivos reais do frontend.

    Copia ``cadastro-pessoa-modal.js`` do projeto (sempre a versão atual do
    código) junto com o HTML do harness e o Alpine vendorado.

    Returns:
        Caminho do HTML do harness pronto para abrir via file://.
    """
    shutil.copy(
        FRONTEND_JS / "components" / "cadastro-pessoa-modal.js",
        tmp_path / "cadastro-pessoa-modal.js",
    )
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "cadastro_pessoa.html", tmp_path / "cadastro_pessoa.html")
    return tmp_path / "cadastro_pessoa.html"


def _open(harness: Path, browser_launcher):
    """Abre o harness num browser Chromium, aplicando o stub de /consultas/.

    Args:
        harness: Caminho do HTML do harness.
        browser_launcher: Callable que lança o browser (permite pular se
            Chromium estiver indisponível no ambiente).

    Returns:
        Tupla (browser, page) já com o harness carregado e o modal aberto.
    """
    browser = browser_launcher()
    page = browser.new_page()
    page.add_init_script(_STUB_JOAO)
    page.goto(f"file://{harness}")
    page.wait_for_timeout(300)
    return browser, page


def _launch_or_skip(p):
    try:
        return p.chromium.launch()
    except PlaywrightError:
        pytest.skip("Chromium indisponível — rode `playwright install chromium`")


def test_nome_com_correspondencia_exibe_painel_de_duplicata(harness: Path) -> None:
    """Digitar um nome com correspondência exibe o painel com o card certo."""
    with sync_playwright() as p:
        browser, page = _open(harness, lambda: _launch_or_skip(p))

        page.locator('input[placeholder="Nome completo"]').fill("JOAO DA SILVA")
        page.wait_for_timeout(600)  # debounce 400ms + folga

        estado = page.evaluate("__state()")
        painel_visivel = page.get_by_text("Possível pessoa já cadastrada").is_visible()
        card_nome_visivel = page.get_by_text("JOAO DA SILVA").last.is_visible()
        card_cpf_visivel = page.get_by_text("***.123.456-**").is_visible()
        browser.close()

    assert estado["cpDuplicatas"] == [
        {
            "id": 55,
            "nome": "JOAO DA SILVA",
            "cpf_masked": "***.123.456-**",
            "apelido": "JOAOZINHO",
            "data_nascimento": "1990-01-01",
            "foto_principal_url": None,
        }
    ]
    assert painel_visivel
    assert card_nome_visivel
    assert card_cpf_visivel


def test_nome_curto_nao_dispara_busca(harness: Path) -> None:
    """Nome com menos de 3 caracteres não deve nem chamar o endpoint de busca."""
    with sync_playwright() as p:
        browser, page = _open(harness, lambda: _launch_or_skip(p))

        page.locator('input[placeholder="Nome completo"]').fill("JO")
        page.wait_for_timeout(600)

        estado = page.evaluate("__state()")
        gets = page.evaluate("window.__calls.gets")
        browser.close()

    assert estado["cpDuplicatas"] == []
    assert not any(url.startswith("/consultas/") for url in gets), gets


def test_nome_sem_correspondencia_nao_exibe_painel(harness: Path) -> None:
    """Nome válido (≥3 chars) sem correspondência no backend não exibe o painel."""
    with sync_playwright() as p:
        browser, page = _open(harness, lambda: _launch_or_skip(p))

        page.locator('input[placeholder="Nome completo"]').fill("PESSOA INEXISTENTE")
        page.wait_for_timeout(600)

        estado = page.evaluate("__state()")
        painel_visivel = page.get_by_text("Possível pessoa já cadastrada").is_visible()
        browser.close()

    assert estado["cpDuplicatas"] == []
    assert not painel_visivel


def test_clicar_no_card_navega_para_ficha_e_fecha_modal(harness: Path) -> None:
    """Clicar no card de duplicata fecha o modal e navega para a ficha certa."""
    with sync_playwright() as p:
        browser, page = _open(harness, lambda: _launch_or_skip(p))

        page.locator('input[placeholder="Nome completo"]').fill("JOAO DA SILVA")
        page.wait_for_timeout(600)
        page.get_by_text("JOAO DA SILVA").last.click()
        page.wait_for_timeout(100)

        estado = page.evaluate("__state()")
        navegacoes = page.evaluate("window.__navigateCalls")
        browser.close()

    assert estado["showCadastroPessoa"] is False
    assert navegacoes == [{"page": "pessoa-detalhe", "pessoaId": 55}]
