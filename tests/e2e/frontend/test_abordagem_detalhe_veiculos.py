"""Teste e2e: adicionar/remover veículo já cadastrado na tela de detalhe da abordagem.

Cobre o slice "adicionar/remover veículo" da feature de complementar
abordagem pós-registro: botão "+ Adicionar veículo" visível só para o
dono da abordagem ou admin da guarnição, busca por veículo já
cadastrado via autocomplete (ou cadastro inline de veículo novo),
vínculo via POST /abordagens/{id}/veiculos, e remoção via DELETE
/abordagens/{id}/veiculos/{veiculo_id}.

O teste dirige os arquivos REAIS do frontend (copiados no momento do
teste) num harness HTML com a API estubada, via Playwright/Chromium
headless. Reaproveita o mesmo harness de
test_abordagem_detalhe_pessoas.py (abordagem_detalhe.html).

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
    shutil.copy(FRONTEND_JS / "components" / "autocomplete.js", tmp_path / "autocomplete.js")
    shutil.copy(
        FRONTEND_JS / "components" / "person-photo-modal.js", tmp_path / "person-photo-modal.js"
    )
    shutil.copy(
        FRONTEND_JS / "components" / "cadastro-pessoa-modal.js",
        tmp_path / "cadastro-pessoa-modal.js",
    )
    shutil.copy(FRONTEND_JS / "pages" / "abordagem-detalhe.js", tmp_path / "abordagem-detalhe.js")
    shutil.copy(FRONTEND_CSS / "app.css", tmp_path / "app.css")
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "abordagem_detalhe.html", tmp_path / "abordagem_detalhe.html")
    return tmp_path / "abordagem_detalhe.html"


def test_dono_adiciona_veiculo_existente(harness: Path) -> None:
    """Dono da abordagem busca e adiciona veículo já cadastrado."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        botao_adicionar = page.get_by_role("button", name="+ Adicionar veículo")
        assert botao_adicionar.is_visible()
        botao_adicionar.click()

        busca = page.locator('input[placeholder="Buscar por placa..."]')
        busca.fill("XYZ9Z99")
        page.wait_for_timeout(500)
        page.get_by_text("XYZ9Z99", exact=False).first.click()
        page.wait_for_timeout(200)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 88 in estado["veiculoIds"]
    assert estado["adicionandoVeiculo"] is False
    posts = [c for c in calls["posts"] if c["url"] == "/abordagens/42/veiculos"]
    assert len(posts) == 1
    assert posts[0]["body"] == {"veiculo_id": 88}


def test_terceiro_nao_ve_botao_adicionar_veiculo(harness: Path) -> None:
    """Usuário que não é dono nem admin não vê o botão de adicionar veículo."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 2 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        botao_adicionar = page.get_by_role("button", name="+ Adicionar veículo")
        visivel = botao_adicionar.count() > 0 and botao_adicionar.is_visible()
        browser.close()

    assert not visivel


def test_dono_remove_veiculo_vinculado(harness: Path) -> None:
    """Dono da abordagem remove um veículo já vinculado via botão ×."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__authUser = { id: 1 };
            window.__abordagem = {
              id: 42,
              data_hora: new Date().toISOString(),
              endereco_texto: 'RUA TESTE, 100',
              observacao: null,
              usuario_id: 1,
              usuario: { id: 1, posto_graduacao: 'SD', nome_guerra: 'TESTE' },
              pessoas: [],
              veiculos: [{ id: 88, placa: 'XYZ9Z99', modelo: 'ONIX', cor: 'PRATA' }],
              fotos: [],
              ocorrencias: [],
            };
            """
        )
        page.on("dialog", lambda dialog: dialog.accept())
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        estado_antes = page.evaluate("__state()")
        assert 88 in estado_antes["veiculoIds"]

        page.locator('button[title="Remover veículo"]').click()
        page.wait_for_timeout(200)

        estado_depois = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 88 not in estado_depois["veiculoIds"]
    deletes = [c for c in calls["deletes"] if c["url"] == "/abordagens/42/veiculos/88"]
    assert len(deletes) == 1


def test_dono_cadastra_veiculo_novo_inline_e_vincula(harness: Path) -> None:
    """Dono busca placa sem resultado, cadastra veículo novo inline e ele é vinculado."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_role("button", name="+ Adicionar veículo").click()

        busca = page.locator('input[placeholder="Buscar por placa..."]')
        busca.fill("ABC1234")
        page.wait_for_timeout(500)

        page.get_by_text("+ Cadastrar novo veículo").click()
        page.wait_for_timeout(100)

        placa_input = page.locator('input[placeholder="ABC-1234"]')
        assert placa_input.input_value() == "ABC1234"

        page.get_by_role("button", name="Salvar e adicionar").click()
        page.wait_for_timeout(300)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert estado["adicionandoVeiculo"] is False
    assert 300 in estado["veiculoIds"]

    posts_veiculo = [c for c in calls["posts"] if c["url"] == "/veiculos/"]
    assert len(posts_veiculo) == 1
    assert posts_veiculo[0]["body"]["placa"] == "ABC1234"

    posts_vinculo = [c for c in calls["posts"] if c["url"] == "/abordagens/42/veiculos"]
    assert len(posts_vinculo) == 1
    assert posts_vinculo[0]["body"] == {"veiculo_id": 300}


def test_falha_ao_vincular_veiculo_novo_preserva_formulario(harness: Path) -> None:
    """Se o vínculo falhar após criar o veículo, o formulário não deve ser limpo.

    Regressão: criarEVincularVeiculo() limpava novoVeiculo incondicionalmente
    mesmo quando vincularVeiculo() falhava internamente (ela nunca relança
    erro), escondendo os dados digitados e deixando o veículo criado mas
    órfão no banco.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            "window.__authUser = { id: 1 }; window.__vincularVeiculoDeveFalhar = true;"
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_role("button", name="+ Adicionar veículo").click()
        busca = page.locator('input[placeholder="Buscar por placa..."]')
        busca.fill("ABC1234")
        page.wait_for_timeout(500)
        page.get_by_text("+ Cadastrar novo veículo").click()
        page.wait_for_timeout(100)

        page.get_by_role("button", name="Salvar e adicionar").click()
        page.wait_for_timeout(300)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert estado["novoVeiculoPlaca"] == "ABC1234", "formulário não deveria ter sido limpo"
    assert estado["erroVincularVeiculo"]
    assert 300 not in estado["veiculoIds"]
    posts_veiculo = [c for c in calls["posts"] if c["url"] == "/veiculos/"]
    assert len(posts_veiculo) == 1, "veículo deveria ter sido criado (órfão) mesmo com a falha"
