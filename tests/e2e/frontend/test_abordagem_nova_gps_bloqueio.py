"""Teste e2e: bloqueio do submit de abordagem enquanto o GPS carrega.

Bug original (2026-07): o botão "Registrar Abordagem" só era bloqueado por
``submitting || pessoaIds.length === 0`` — nada impedia o agente de clicar
antes de ``captureGPS()`` (frontend/js/components/gps.js) terminar, salvando
a abordagem com ``latitude``/``longitude`` nulos.

Regra implementada em ``captureGPS()`` (frontend/js/pages/abordagem-nova.js):
- Enquanto ``gpsLoading`` é true, o submit fica bloqueado.
- Permissão negada (``GeolocationPositionError.code === 1``) mantém o submit
  bloqueado — é uma decisão reversível do usuário, não uma falha técnica.
- Qualquer outra falha definitiva (sinal indisponível, timeout mesmo após o
  fallback de baixa precisão, ou geolocalização não suportada) libera o
  submit mesmo sem coordenadas, para não travar o registro da abordagem por
  um problema fora do controle do agente.

O teste dirige os arquivos REAIS do frontend (copiados no momento do teste)
num harness HTML com a API e o GPS estubados, via Playwright/Chromium headless.

Opt-in: requer ``pip install playwright && playwright install chromium``.
Sem isso, o teste é pulado.
"""

import shutil
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api", reason="playwright não instalado")

from playwright.sync_api import Error as PlaywrightError  # noqa: E402
from playwright.sync_api import (
    Page,  # noqa: E402
    sync_playwright,  # noqa: E402
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_JS = REPO_ROOT / "frontend" / "js"
HARNESS_DIR = Path(__file__).parent / "harness"


@pytest.fixture
def harness(tmp_path: Path) -> Path:
    """Monta o harness em diretório temporário com os arquivos reais do frontend.

    Copia ``autocomplete.js`` e ``abordagem-nova.js`` do projeto (sempre a
    versão atual do código) junto com o HTML do harness e o Alpine vendorado.

    Returns:
        Caminho do HTML do harness pronto para abrir via file://.
    """
    shutil.copy(FRONTEND_JS / "components" / "autocomplete.js", tmp_path / "autocomplete.js")
    shutil.copy(FRONTEND_JS / "pages" / "abordagem-nova.js", tmp_path / "abordagem-nova.js")
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "abordagem_nova.html", tmp_path / "abordagem_nova.html")
    return tmp_path / "abordagem_nova.html"


def _selecionar_pessoa_existente(page: Page) -> None:
    """Seleciona a pessoa estubada 'FULANO EXISTENTE' pelo autocomplete.

    Usado para satisfazer a condição ``pessoaIds.length > 0`` do submit e
    isolar o efeito do bloqueio por GPS nos testes deste arquivo.

    Args:
        page: Página Playwright já aberta no harness.
    """
    busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
    busca.fill("FULANO")
    page.wait_for_timeout(500)
    page.get_by_text("FULANO EXISTENTE").first.click()
    page.wait_for_timeout(200)


def test_submit_desabilitado_enquanto_gps_carrega(harness: Path) -> None:
    """Botão de submit fica desabilitado enquanto o GPS ainda não resolveu.

    Estuba ``getGPSLocation`` com uma promise que só resolve quando o teste
    manda (via ``window.__gpsResolve``), simulando o intervalo real entre
    abrir a tela e a resposta do ``navigator.geolocation``. Depois de
    resolver com sucesso, o botão deve habilitar.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            "window.__gpsStub = () => new Promise((resolve) => { window.__gpsResolve = resolve; });"
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        _selecionar_pessoa_existente(page)

        botao = page.get_by_role("button", name="Registrar Abordagem")
        desabilitado_carregando = botao.is_disabled()

        assert page.evaluate("typeof window.__gpsResolve === 'function'"), (
            "captureGPS() não chamou getGPSLocation() — initForm() não disparou a captura de GPS"
        )
        page.evaluate(
            "window.__gpsResolve({ latitude: -15.6, longitude: -47.6, endereco_texto: 'X' })"
        )
        page.wait_for_timeout(200)
        habilitado_apos_sucesso = not botao.is_disabled()

        browser.close()

    assert desabilitado_carregando, "botão deveria estar desabilitado com GPS pendente"
    assert habilitado_apos_sucesso, "botão deveria habilitar após o GPS resolver com sucesso"


def test_submit_permanece_desabilitado_com_permissao_negada(harness: Path) -> None:
    """Permissão de localização negada mantém o submit bloqueado.

    ``code === 1`` (PERMISSION_DENIED) é a única falha de GPS que não libera
    o botão — é uma decisão reversível do usuário (pode conceder a permissão
    e tentar de novo), não uma falha técnica definitiva.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__gpsStub = () => Promise.reject({ code: 1 });")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(400)

        _selecionar_pessoa_existente(page)

        botao = page.get_by_role("button", name="Registrar Abordagem")
        desabilitado = botao.is_disabled()
        estado = page.evaluate("__state()")
        browser.close()

    assert desabilitado, "botão deveria continuar desabilitado com permissão negada"
    assert estado["gpsPermissionDenied"] is True


def test_submit_libera_com_sinal_indisponivel(harness: Path) -> None:
    """``code === 2`` (POSITION_UNAVAILABLE) é falha técnica definitiva: libera o submit.

    Bloquear o registro por indisponibilidade de sinal de GPS violaria a
    regra de negócio de cadastro de abordagem em menos de 40 segundos.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__gpsStub = () => Promise.reject({ code: 2 });")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(400)

        _selecionar_pessoa_existente(page)

        botao = page.get_by_role("button", name="Registrar Abordagem")
        habilitado = not botao.is_disabled()
        estado = page.evaluate("__state()")
        browser.close()

    assert habilitado, "botão deveria habilitar mesmo sem coordenadas (falha técnica)"
    assert estado["gpsPermissionDenied"] is False


def test_submit_libera_apos_timeout_em_ambas_tentativas(harness: Path) -> None:
    """``code === 3`` (TIMEOUT) mesmo após o fallback de baixa precisão libera o submit.

    ``captureGPS()`` tenta ``getGPSLocationLowAccuracy()`` quando a tentativa
    de alta precisão estoura o tempo; se as duas falharem, é falha técnica
    definitiva e o submit não deve ficar travado.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__gpsStub = () => Promise.reject({ code: 3 });
            window.__gpsStubLowAccuracy = () => Promise.reject({ code: 3 });
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(400)

        _selecionar_pessoa_existente(page)

        botao = page.get_by_role("button", name="Registrar Abordagem")
        habilitado = not botao.is_disabled()
        estado = page.evaluate("__state()")
        browser.close()

    assert habilitado, "botão deveria habilitar após timeout nas duas tentativas de GPS"
    assert estado["gpsPermissionDenied"] is False
