"""Teste e2e: fluxo de login (frontend/js/pages/login.js + frontend/js/auth.js).

Cobre o contrato real do formulário de login: sucesso, primeira falha (que
sempre revela o campo de 2FA, independente do motivo — é assim que o código
atual decide, não uma sinalização explícita do backend) e segunda falha (que
aí sim mostra a mensagem de erro real vinda do backend).

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

    Copia ``auth.js`` e ``login.js`` do projeto (sempre a versão atual do
    código) junto com o HTML do harness e o Alpine vendorado.

    Returns:
        Caminho do HTML do harness pronto para abrir via file://.
    """
    shutil.copy(FRONTEND_JS / "auth.js", tmp_path / "auth.js")
    shutil.copy(FRONTEND_JS / "pages" / "login.js", tmp_path / "login.js")
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "login.html", tmp_path / "login.html")
    return tmp_path / "login.html"


def _submeter(page: Page, matricula: str = "12345", senha: str = "segredo", totp: str = "") -> None:
    """Preenche e submete o formulário de login.

    Args:
        page: Página Playwright já aberta no harness.
        matricula: Valor do campo matrícula.
        senha: Valor do campo senha.
        totp: Valor do campo TOTP, se visível (vazio = não preenche).
    """
    page.locator('input[placeholder="Matrícula"]').fill(matricula)
    page.locator('input[placeholder="••••••••"]').fill(senha)
    if totp:
        page.locator('input[placeholder="000000"]').fill(totp)
    page.get_by_role("button", name="ACESSAR SISTEMA").click()
    page.wait_for_timeout(300)


def test_login_com_sucesso_chama_onlogin(harness: Path) -> None:
    """Login bem-sucedido na primeira tentativa chama onLogin com o usuário retornado."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            "window.__meStub = () => ({ id: 7, nome: 'AGENTE TESTE', matricula: '12345' });"
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        _submeter(page)

        calls = page.evaluate("window.__calls")
        browser.close()

    assert calls["onLogin"] == [{"id": 7, "nome": "AGENTE TESTE", "matricula": "12345"}]
    assert {
        "url": "/auth/login",
        "body": {"matricula": "12345", "senha": "segredo"},
    } in calls["posts"]


def test_primeira_falha_revela_campo_totp_sem_chamar_onlogin(harness: Path) -> None:
    """Primeira tentativa que falha mostra o campo de 2FA e a mensagem genérica.

    ``login.js`` trata QUALQUER falha na primeira tentativa (``mostrarTotp``
    ainda ``false``) como possível pedido de 2FA — não distingue senha errada
    de "precisa de TOTP" nesse ponto. Só a segunda falha revela o erro real
    (ver ``test_segunda_falha_mostra_erro_real_do_backend``).
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            "window.__loginStub = () => { throw new Error('Credenciais inválidas'); };"
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        _submeter(page)

        erro = page.locator("[x-text='erro']").text_content()
        totp_visivel = page.locator('input[placeholder="000000"]').is_visible()
        calls = page.evaluate("window.__calls")
        browser.close()

    assert totp_visivel, "campo TOTP deveria aparecer após a primeira falha"
    assert erro == "Informe o código 2FA se você é administrador."
    assert calls["onLogin"] == []


def test_segunda_falha_mostra_erro_real_do_backend(harness: Path) -> None:
    """Segunda tentativa (já com campo TOTP visível) que falha mostra o erro real."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            "window.__loginStub = () => { throw new Error('Credenciais inválidas'); };"
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        _submeter(page)  # primeira falha: revela o campo TOTP
        _submeter(page, totp="000000")  # segunda falha: mostra o erro real

        erro = page.locator("[x-text='erro']").text_content()
        calls = page.evaluate("window.__calls")
        browser.close()

    assert erro == "Credenciais inválidas"
    assert calls["onLogin"] == []


def test_segunda_tentativa_com_sucesso_apos_totp_completa_login(harness: Path) -> None:
    """Após a primeira falha revelar o campo TOTP, reenviar com sucesso completa o login."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            let tentativa = 0;
            window.__loginStub = () => {
              tentativa += 1;
              if (tentativa === 1) throw new Error('Credenciais inválidas');
              return {};
            };
            window.__meStub = () => ({ id: 7, nome: 'AGENTE TESTE' });
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        _submeter(page)  # primeira falha: revela o campo TOTP
        _submeter(page, totp="123456")  # segunda tentativa: sucesso

        calls = page.evaluate("window.__calls")
        browser.close()

    assert calls["onLogin"] == [{"id": 7, "nome": "AGENTE TESTE"}]
