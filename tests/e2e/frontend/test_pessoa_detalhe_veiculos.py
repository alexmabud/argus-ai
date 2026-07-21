"""Teste e2e: remoção de vínculo veículo-pessoa na ficha do abordado.

Cobre o slice "remover vínculo veículo-pessoa na ficha do abordado" da
feature de exclusão segura: o ícone de remoção direto no card de
"Veículos Vinculados ao Abordado" some — a remoção passa a exigir abrir
a foto ampliada do veículo (mesmo modal reutilizável `personPhotoModal`)
e confirmar via modal customizado (`confirmDialog`), restrito a quem
criou o vínculo (`criado_por_id`) ou admin/super-admin.

O teste dirige os arquivos REAIS do frontend (copiados no momento do
teste) num harness HTML com a API estubada, via Playwright/Chromium
headless.

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


def test_smoke_pagina_carrega_com_veiculo_vinculado(harness: Path) -> None:
    """A página carrega e mostra o veículo vinculado direto, sem erros de console."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        erros_console = []
        page.on("pageerror", lambda exc: erros_console.append(str(exc)))
        page.add_init_script(
            """
            window.__authUser = { id: 1 };
            window.__pessoa = {
              id: 1, nome: 'FULANO EXISTENTE', cpf_masked: '***.456.789-**',
              apelido: null, data_nascimento: null, nome_mae: null, enderecos: [],
              relacionamentos: [],
            };
            window.__veiculos = [
              { veiculo_id: 88, placa: 'XYZ9Z99', modelo: 'ONIX', cor: 'PRATA',
                origem: 'direto', criado_por_id: 1 },
            ];
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        estado = page.evaluate("__state()")
        browser.close()

    assert erros_console == []
    assert 88 in estado["veiculoIds"]


def test_dono_do_vinculo_remove_veiculo_via_foto_ampliada(harness: Path) -> None:
    """Dono do vínculo direto remove o veículo vinculado via lixeira na foto ampliada.

    Veículo sem foto cadastrada — exercita o fallback (card clicável mesmo
    sem miniatura de foto) e a lixeira condicionada a ser dono do vínculo.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__authUser = { id: 1 };
            window.__pessoa = {
              id: 1, nome: 'FULANO EXISTENTE', cpf_masked: '***.456.789-**',
              apelido: null, data_nascimento: null, nome_mae: null, enderecos: [],
              relacionamentos: [],
            };
            window.__veiculos = [
              { veiculo_id: 88, placa: 'XYZ9Z99', modelo: 'ONIX', cor: 'PRATA',
                origem: 'direto', criado_por_id: 1 },
            ];
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_text("XYZ-9Z99", exact=True).click()
        page.wait_for_timeout(200)
        page.locator('button[title="Remover veículo"]').click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Remover").click()
        page.wait_for_timeout(200)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 88 not in estado["veiculoIds"]
    deletes = [c for c in calls["deletes"] if c["url"] == "/pessoas/1/veiculos/88"]
    assert len(deletes) == 1


def test_cancelar_confirmacao_nao_remove_vinculo_veiculo(harness: Path) -> None:
    """Cancelar a confirmação mantém o vínculo veículo-pessoa."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__authUser = { id: 1 };
            window.__pessoa = {
              id: 1, nome: 'FULANO EXISTENTE', cpf_masked: '***.456.789-**',
              apelido: null, data_nascimento: null, nome_mae: null, enderecos: [],
              relacionamentos: [],
            };
            window.__veiculos = [
              { veiculo_id: 88, placa: 'XYZ9Z99', modelo: 'ONIX', cor: 'PRATA',
                origem: 'direto', criado_por_id: 1 },
            ];
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_text("XYZ-9Z99", exact=True).click()
        page.wait_for_timeout(200)
        page.locator('button[title="Remover veículo"]').click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Cancelar").click()
        page.wait_for_timeout(200)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 88 in estado["veiculoIds"]
    assert calls["deletes"] == []


def test_outro_usuario_nao_ve_lixeira_do_vinculo(harness: Path) -> None:
    """Usuário autenticado que não é dono do vínculo nem admin não vê a lixeira."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__authUser = { id: 2 };
            window.__pessoa = {
              id: 1, nome: 'FULANO EXISTENTE', cpf_masked: '***.456.789-**',
              apelido: null, data_nascimento: null, nome_mae: null, enderecos: [],
              relacionamentos: [],
            };
            window.__veiculos = [
              { veiculo_id: 88, placa: 'XYZ9Z99', modelo: 'ONIX', cor: 'PRATA',
                origem: 'direto', criado_por_id: 1 },
            ];
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_text("XYZ-9Z99", exact=True).click()
        page.wait_for_timeout(200)
        lixeira = page.locator('button[title="Remover veículo"]')
        visivel = lixeira.count() > 0 and lixeira.is_visible()
        browser.close()

    assert not visivel


def test_admin_ve_lixeira_de_vinculo_criado_por_outro(harness: Path) -> None:
    """Admin da guarnição vê a lixeira mesmo não sendo quem criou o vínculo."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__authUser = { id: 2, is_admin: true };
            window.__pessoa = {
              id: 1, nome: 'FULANO EXISTENTE', cpf_masked: '***.456.789-**',
              apelido: null, data_nascimento: null, nome_mae: null, enderecos: [],
              relacionamentos: [],
            };
            window.__veiculos = [
              { veiculo_id: 88, placa: 'XYZ9Z99', modelo: 'ONIX', cor: 'PRATA',
                origem: 'direto', criado_por_id: 1 },
            ];
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_text("XYZ-9Z99", exact=True).click()
        page.wait_for_timeout(200)
        visivel = page.locator('button[title="Remover veículo"]').is_visible()
        browser.close()

    assert visivel


def test_veiculo_origem_abordagem_nunca_mostra_lixeira(harness: Path) -> None:
    """Veículo derivado de abordagem (sem vínculo direto) nunca mostra a lixeira aqui."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__authUser = { id: 1, is_admin: true };
            window.__pessoa = {
              id: 1, nome: 'FULANO EXISTENTE', cpf_masked: '***.456.789-**',
              apelido: null, data_nascimento: null, nome_mae: null, enderecos: [],
              relacionamentos: [],
            };
            window.__veiculos = [
              { veiculo_id: 88, placa: 'XYZ9Z99', modelo: 'ONIX', cor: 'PRATA',
                origem: 'abordagem', criado_por_id: null },
            ];
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_text("XYZ-9Z99", exact=True).click()
        page.wait_for_timeout(200)
        lixeira = page.locator('button[title="Remover veículo"]')
        visivel = lixeira.count() > 0 and lixeira.is_visible()
        browser.close()

    assert not visivel
