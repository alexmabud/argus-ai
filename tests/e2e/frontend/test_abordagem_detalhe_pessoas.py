"""Teste e2e: adicionar/remover pessoa já cadastrada na tela de detalhe da abordagem.

Cobre o slice "adicionar/remover pessoa existente" da feature de
complementar abordagem pós-registro: botão "+ Adicionar abordado"
visível só para o dono da abordagem ou admin da guarnição, busca por
pessoa já cadastrada via autocomplete, vínculo via POST
/abordagens/{id}/pessoas, e remoção via DELETE
/abordagens/{id}/pessoas/{pessoa_id}.

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

    Copia ``autocomplete.js``, ``person-photo-modal.js``,
    ``cadastro-pessoa-modal.js``, ``abordagem-detalhe.js`` e ``app.css`` do
    projeto (sempre a versão atual do código) junto com o HTML do harness e
    o Alpine vendorado. O CSS real é necessário para pegar bugs de stacking
    context (ex.: backdrop-filter em .glass-card) que inline styles sozinhos
    não reproduzem.

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
    shutil.copy(FRONTEND_JS / "components" / "confirm-dialog.js", tmp_path / "confirm-dialog.js")
    shutil.copy(FRONTEND_JS / "pages" / "abordagem-detalhe.js", tmp_path / "abordagem-detalhe.js")
    shutil.copy(FRONTEND_CSS / "app.css", tmp_path / "app.css")
    shutil.copy(HARNESS_DIR / "alpine.min.js", tmp_path / "alpine.min.js")
    shutil.copy(HARNESS_DIR / "abordagem_detalhe.html", tmp_path / "abordagem_detalhe.html")
    return tmp_path / "abordagem_detalhe.html"


def test_dono_adiciona_pessoa_existente(harness: Path) -> None:
    """Dono da abordagem busca e adiciona pessoa já cadastrada.

    Verifica que o botão "+ Adicionar abordado" está visível, que
    selecionar um resultado do autocomplete chama POST
    /abordagens/{id}/pessoas e que a pessoa aparece na lista de
    abordados sem precisar recarregar a página.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        botao_adicionar = page.get_by_role("button", name="+ Adicionar abordado")
        assert botao_adicionar.is_visible()
        botao_adicionar.click()

        busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        busca.fill("FULANO")
        page.wait_for_timeout(500)
        page.get_by_text("FULANO EXISTENTE").first.click()
        page.wait_for_timeout(200)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 77 in estado["pessoaIds"]
    assert estado["adicionandoAbordado"] is False
    posts = [c for c in calls["posts"] if c["url"] == "/abordagens/42/pessoas"]
    assert len(posts) == 1
    assert posts[0]["body"] == {"pessoa_id": 77}


def test_terceiro_nao_ve_botao_adicionar(harness: Path) -> None:
    """Usuário que não é dono nem admin não vê o botão de adicionar abordado."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        # abordagem.usuario_id é 1 (default do harness); usuário logado é outro,
        # sem is_admin — não deve ver o botão.
        page.add_init_script("window.__authUser = { id: 2 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        botao_adicionar = page.get_by_role("button", name="+ Adicionar abordado")
        visivel = botao_adicionar.count() > 0 and botao_adicionar.is_visible()
        browser.close()

    assert not visivel


def test_admin_ve_e_usa_botao_adicionar(harness: Path) -> None:
    """Admin da guarnição, mesmo não sendo o dono, vê e consegue usar o botão."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 2, is_admin: true };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        botao_adicionar = page.get_by_role("button", name="+ Adicionar abordado")
        assert botao_adicionar.is_visible()
        botao_adicionar.click()

        busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        busca.fill("FULANO")
        page.wait_for_timeout(500)
        page.get_by_text("FULANO EXISTENTE").first.click()
        page.wait_for_timeout(200)

        estado = page.evaluate("__state()")
        browser.close()

    assert 77 in estado["pessoaIds"]


def test_dono_remove_pessoa_vinculada_via_foto_ampliada(harness: Path) -> None:
    """Dono da abordagem remove um abordado vinculado via lixeira na foto ampliada.

    Regressão do fluxo antigo (botão "×" direto na miniatura + confirm()
    nativo): agora a remoção exige abrir a foto ampliada (mesmo sem foto —
    o abordado do teste não tem `foto_principal_url`, exercitando o
    fallback de iniciais) e confirmar via modal customizado, não mais
    diálogo nativo do navegador.
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
            window.__abordagem = {
              id: 42,
              data_hora: new Date().toISOString(),
              endereco_texto: 'RUA TESTE, 100',
              observacao: null,
              usuario_id: 1,
              usuario: { id: 1, posto_graduacao: 'SD', nome_guerra: 'TESTE' },
              pessoas: [{ id: 77, nome: 'FULANO EXISTENTE' }],
              veiculos: [],
              fotos: [],
              ocorrencias: [],
            };
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        estado_antes = page.evaluate("__state()")
        assert 77 in estado_antes["pessoaIds"]

        page.get_by_text("FULANO", exact=True).click()
        page.wait_for_timeout(200)
        page.locator('button[title="Remover abordado"]').click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Remover", exact=True).click()
        page.wait_for_timeout(200)

        estado_depois = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 77 not in estado_depois["pessoaIds"]
    deletes = [c for c in calls["deletes"] if c["url"] == "/abordagens/42/pessoas/77"]
    assert len(deletes) == 1


def test_cancelar_confirmacao_nao_remove_pessoa(harness: Path) -> None:
    """Cancelar a confirmação de remoção mantém o abordado vinculado."""
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
              pessoas: [{ id: 77, nome: 'FULANO EXISTENTE' }],
              veiculos: [],
              fotos: [],
              ocorrencias: [],
            };
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_text("FULANO", exact=True).click()
        page.wait_for_timeout(200)
        page.locator('button[title="Remover abordado"]').click()
        page.wait_for_timeout(100)
        page.get_by_role("button", name="Cancelar").click()
        page.wait_for_timeout(200)

        estado_depois = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert 77 in estado_depois["pessoaIds"]
    assert calls["deletes"] == []


def test_terceiro_nao_ve_lixeira_na_foto_ampliada_do_abordado(harness: Path) -> None:
    """Usuário que não é dono nem admin não vê a lixeira na foto ampliada."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script(
            """
            window.__authUser = { id: 2 };
            window.__abordagem = {
              id: 42,
              data_hora: new Date().toISOString(),
              endereco_texto: 'RUA TESTE, 100',
              observacao: null,
              usuario_id: 1,
              usuario: { id: 1, posto_graduacao: 'SD', nome_guerra: 'TESTE' },
              pessoas: [{ id: 77, nome: 'FULANO EXISTENTE' }],
              veiculos: [],
              fotos: [],
              ocorrencias: [],
            };
            """
        )
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_text("FULANO", exact=True).click()
        page.wait_for_timeout(200)
        lixeira = page.locator('button[title="Remover abordado"]')
        visivel = lixeira.count() > 0 and lixeira.is_visible()
        browser.close()

    assert not visivel


def test_dono_cadastra_pessoa_nova_inline_e_vincula(harness: Path) -> None:
    """Dono busca nome sem resultado, cadastra pessoa nova inline e ela é vinculada.

    Reproduz o fluxo completo: "+ Adicionar abordado" → busca sem
    resultado → "+ Cadastrar novo abordado" → modal reaproveitado de
    cadastro-pessoa-modal.js abre com o nome pré-preenchido → salvar
    cria a pessoa (POST /pessoas/) e vincula automaticamente à
    abordagem aberta (POST /abordagens/{id}/pessoas), sem navegar para
    fora da tela de detalhe.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_role("button", name="+ Adicionar abordado").click()

        busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        busca.fill("PESSOA NOVA")
        page.wait_for_timeout(500)

        page.get_by_text("+ Cadastrar novo abordado").click()
        page.wait_for_timeout(100)

        estado_modal = page.evaluate("__state()")
        assert estado_modal["showCadastroPessoa"] is True
        assert estado_modal["novaPessoaNome"] == "PESSOA NOVA"

        page.get_by_role("button", name="SALVAR PESSOA").click()
        page.wait_for_timeout(300)

        estado = page.evaluate("__state()")
        calls = page.evaluate("__calls")
        browser.close()

    assert estado["showCadastroPessoa"] is False
    assert estado["adicionandoAbordado"] is False
    assert 200 in estado["pessoaIds"]

    posts_pessoa = [c for c in calls["posts"] if c["url"] == "/pessoas/"]
    assert len(posts_pessoa) == 1
    assert posts_pessoa[0]["body"]["nome"] == "PESSOA NOVA"

    posts_vinculo = [c for c in calls["posts"] if c["url"] == "/abordagens/42/pessoas"]
    assert len(posts_vinculo) == 1
    assert posts_vinculo[0]["body"] == {"pessoa_id": 200}


def test_reabrir_painel_apos_vincular_pessoa_vem_com_busca_limpa(harness: Path) -> None:
    """Depois de vincular uma pessoa, reabrir "+ Adicionar abordado" deve vir limpo.

    Regressão: selecionar um resultado despachava o evento sem chamar
    select() no componente de autocomplete (que é quem limpa
    query/results/showDropdown), deixando a busca anterior visível ao
    reabrir o painel pra adicionar uma segunda pessoa.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_role("button", name="+ Adicionar abordado").click()
        busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        busca.fill("FULANO")
        page.wait_for_timeout(500)
        page.get_by_text("FULANO EXISTENTE").first.click()
        page.wait_for_timeout(200)

        page.get_by_role("button", name="+ Adicionar abordado").click()
        page.wait_for_timeout(100)
        busca_reaberta = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        valor_reaberto = busca_reaberta.input_value()
        dropdown_visivel = page.get_by_text("FULANO EXISTENTE").count() > 0

        browser.close()

    assert valor_reaberto == ""
    assert not dropdown_visivel


def test_terceiro_nao_ve_botao_salvar_observacao(harness: Path) -> None:
    """Usuário que não é dono nem admin não vê o botão de salvar observação.

    Regressão: o backend passou a exigir 403 nesse endpoint para quem não
    é dono/admin, mas o botão continuava habilitado no frontend.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 2 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        botao_salvar = page.get_by_role("button", name="Salvar observação")
        textarea_desabilitada = page.locator("textarea").is_disabled()
        botao_visivel = botao_salvar.count() > 0 and botao_salvar.is_visible()

        browser.close()

    assert textarea_desabilitada
    assert not botao_visivel


def test_dono_ve_botao_salvar_observacao(harness: Path) -> None:
    """Dono da abordagem continua vendo o botão de salvar observação."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        botao_salvar = page.get_by_role("button", name="Salvar observação")
        visivel = botao_salvar.is_visible()
        textarea_habilitada = not page.locator("textarea").is_disabled()

        browser.close()

    assert visivel
    assert textarea_habilitada


def test_botao_cadastrar_novo_abordado_nao_fica_coberto_pelo_card_veiculos(harness: Path) -> None:
    """O botão "+ Cadastrar novo abordado" precisa estar realmente clicável.

    Regressão: .glass-card usa backdrop-filter, que cria um stacking context
    próprio (spec CSS) — o dropdown do autocomplete (position:absolute,
    z-index interno) ficava preso dentro do card ABORDADOS, e o card
    VEÍCULOS (irmão seguinte, sem z-index) pintava por cima dele sempre que
    o dropdown ultrapassava a borda do card. Playwright's is_visible()/count()
    não pega esse tipo de bug (só checam display/size, não oclusão visual)
    — por isso o teste usa elementFromPoint no centro do botão.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            pytest.skip("Chromium indisponível — rode `playwright install chromium`")

        page = browser.new_page()
        page.add_init_script("window.__authUser = { id: 1 };")
        page.goto(f"file://{harness}")
        page.wait_for_timeout(300)

        page.get_by_role("button", name="+ Adicionar abordado").click()
        busca = page.locator('input[placeholder="Buscar por nome ou CPF..."]')
        busca.fill("NAO EXISTE NA BASE")
        page.wait_for_timeout(500)

        botao = page.get_by_text("+ Cadastrar novo abordado")
        box = botao.bounding_box()
        assert box is not None, "botão não está no DOM"

        elemento_no_topo = page.evaluate(
            """([x, y]) => {
                const el = document.elementFromPoint(x, y);
                return el ? (el.textContent || '').trim() : null;
            }""",
            [box["x"] + box["width"] / 2, box["y"] + box["height"] / 2],
        )
        browser.close()

    assert elemento_no_topo is not None and "Cadastrar novo abordado" in elemento_no_topo, (
        f"botão está coberto por outro elemento — elementFromPoint retornou: {elemento_no_topo!r}"
    )
