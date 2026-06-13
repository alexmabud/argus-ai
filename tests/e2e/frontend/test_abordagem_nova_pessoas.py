"""Teste de regressão e2e: pessoas novas + pessoa existente na nova abordagem.

Bug original (2026-06): pessoas cadastradas inline recebiam ID temporário
negativo mas nunca eram registradas no ``selected`` do autocomplete, porque
``criarPessoa()`` usava ``this.$el`` (que dentro de um método chamado por
``@click`` é o botão, não a raiz do form). Ao selecionar uma pessoa já
existente no autocomplete, o listener ``pessoa-selected`` — que trata o
``selected`` do autocomplete como fonte da verdade — descartava todas as
pessoas novas, e o submit enviava a foto com ``pessoa_id`` negativo,
rejeitado pelo backend com "Input should be greater than 0".

O teste dirige os arquivos REAIS do frontend (copiados no momento do teste)
num harness HTML com a API stubada, via Playwright/Chromium headless.

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

# PNG 1x1 válido para simular a foto do abordado
_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fcffffff3f0005fe02fea73581840000000049454e44ae426082"
)


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
    (tmp_path / "foto.png").write_bytes(_PNG_1X1)
    return tmp_path / "abordagem_nova.html"


def _criar_pessoa_inline(page, nome: str) -> None:
    """Cadastra uma pessoa nova pelo fluxo real da UI.

    Busca o nome (sem resultados), abre o form inline via
    "+ Cadastrar novo abordado" e salva.

    Args:
        page: Página Playwright já aberta no harness.
        nome: Nome da pessoa a cadastrar.
    """
    busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
    busca.fill(nome)
    page.wait_for_timeout(500)  # debounce 300ms do autocomplete + busca
    page.get_by_text("+ Cadastrar novo abordado").click()
    page.wait_for_timeout(100)
    page.get_by_role("button", name="Salvar e adicionar").first.click()
    page.wait_for_timeout(200)


def test_pessoas_novas_sobrevivem_a_selecao_de_pessoa_existente(harness: Path) -> None:
    """Cadastrar 3 pessoas inline + selecionar 1 existente não pode perder ninguém.

    Reproduz o cenário do bug: 3 cadastros inline (com foto na primeira),
    seleção de pessoa existente no autocomplete e submit. Verifica que as 4
    pessoas permanecem, que as novas são criadas no banco antes da abordagem,
    que a foto é reindexada para o ID real e que nenhum erro é exibido.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(400)

        for nome in ["PESSOA NOVA UM", "PESSOA NOVA DOIS", "PESSOA NOVA TRES"]:
            _criar_pessoa_inline(page, nome)

        # Foto na primeira pessoa nova (ID temporário -1)
        page.locator('[id="foto-p--1"]').set_input_files(harness.parent / "foto.png")
        page.wait_for_timeout(100)

        # Selecionar pessoa EXISTENTE pelo autocomplete
        busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        busca.fill("FULANO")
        page.wait_for_timeout(500)
        page.get_by_text("FULANO EXISTENTE").first.click()
        page.wait_for_timeout(200)

        estado = page.evaluate("__state()")
        # Núcleo do bug: as 3 pessoas novas sumiam aqui
        assert len(estado["pessoasSelecionadas"]) == 4, (
            f"pessoas visíveis após selecionar existente: {estado['pessoasSelecionadas']}"
        )
        assert len(estado["novasPessoas"]) == 3, (
            f"novasPessoas foi descartada: {estado['novasPessoas']}"
        )

        # Registrar abordagem
        page.get_by_role("button", name="Registrar Abordagem").click()
        page.wait_for_timeout(600)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert estado["erro"] is None, f"erro exibido no submit: {estado['erro']!r}"
    assert estado["showSuccessModal"] is True

    posts_pessoas = [c for c in calls["posts"] if c["url"] == "/pessoas/"]
    posts_abordagem = [c for c in calls["posts"] if c["url"] == "/abordagens/"]
    assert len(posts_pessoas) == 3, "as 3 pessoas novas devem ser criadas no submit"
    assert len(posts_abordagem) == 1

    pessoa_ids = posts_abordagem[0]["body"]["pessoa_ids"]
    assert len(pessoa_ids) == 4
    assert all(pid > 0 for pid in pessoa_ids), f"IDs temporários vazaram: {pessoa_ids}"

    # Foto reindexada do ID temporário (-1) para o ID real
    assert len(calls["uploads"]) == 1
    assert calls["uploads"][0]["fields"]["pessoa_id"] > 0


def test_remover_pessoa_desvincula_veiculo(harness: Path) -> None:
    """Remover pessoa vinculada a veículo deve desfazer o vínculo e travar o submit.

    Regressão do achado do code review: o vínculo veiculo→pessoa ficava
    órfão quando a pessoa saía da seleção, e o submit enviava
    ``veiculo_por_pessoa`` com pessoa_id fora de ``pessoa_ids`` — o backend
    aceita sem validar e cria vínculo órfão no banco.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.goto(f"file://{harness}")
        page.wait_for_timeout(400)

        # Uma pessoa nova inline + uma existente (FULANO, id 77)
        _criar_pessoa_inline(page, "PESSOA NOVA UM")
        busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        busca.fill("FULANO")
        page.wait_for_timeout(500)
        page.get_by_text("FULANO EXISTENTE").first.click()
        page.wait_for_timeout(200)

        # Veículo novo inline (stub POST /veiculos/ devolve id 1)
        placa = page.locator('input[placeholder="Buscar por placa..."]')
        placa.fill("ABC1234")
        page.wait_for_timeout(500)
        page.get_by_text("+ Cadastrar novo veículo").click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Salvar e adicionar").last.click()
        page.wait_for_timeout(300)

        # Vincular veículo → FULANO ("Quem estava no veículo?")
        page.get_by_role("button", name="FULANO EXISTENTE").click()
        page.wait_for_timeout(100)
        estado = page.evaluate("__state()")
        assert estado["veiculoPorPessoa"] == {"1": 77}

        # Remover FULANO pelo fluxo do autocomplete (remove + dispatch do chip ×)
        page.evaluate(
            """() => {
              const el = document.querySelector("[data-autocomplete='pessoa']");
              const ac = Alpine.$data(el);
              ac.remove(77);
              el.dispatchEvent(new CustomEvent('pessoa-selected', {
                detail: { selected: ac.selected }, bubbles: true,
              }));
            }"""
        )
        page.wait_for_timeout(200)

        estado = page.evaluate("__state()")
        # Núcleo do bug: o vínculo ficava órfão apontando para a pessoa removida
        assert estado["veiculoPorPessoa"].get("1") is None, (
            f"vínculo órfão após remover pessoa: {estado['veiculoPorPessoa']}"
        )

        # Submit deve travar exigindo re-vincular o veículo
        page.get_by_role("button", name="Registrar Abordagem").click()
        page.wait_for_timeout(400)
        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert estado["erro"] and "Vincule o veículo" in estado["erro"], (
        f"submit não travou: erro={estado['erro']!r}"
    )
    assert not [c for c in calls["posts"] if c["url"] == "/abordagens/"], (
        "abordagem não deveria ter sido criada com vínculo órfão"
    )
