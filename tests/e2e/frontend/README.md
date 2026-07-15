# Testes e2e de frontend

Testes que dirigem os arquivos **reais** de `frontend/js/` num navegador de verdade (Chromium headless via Playwright), sem precisar do backend rodando. Cobrem regressões e comportamentos difíceis de garantir só por leitura de código (timing, estado do Alpine, condições de corrida).

## Por que esse padrão (harness + API estubada)

- **Sem build step no frontend** (`frontend/` é vanilla JS + Alpine.js, carregado via `<script>` direto) — não há bundler para apontar um test runner tipo Jest/Vitest contra os módulos.
- **`file://` em vez de servidor HTTP** — cada teste copia os arquivos reais do frontend (ex. `login.js`, `auth.js`) para um diretório temporário junto de um harness HTML mínimo, e abre esse HTML direto do disco. Rápido, isolado, sem precisar subir um servidor.
- **API estubada, não o backend real** — o harness define `window.api = { get, post, ... }` substituindo o `ApiClient` real, com respostas controladas por teste (via `page.add_init_script` definindo hooks tipo `window.__loginStub`). Isso testa o frontend isoladamente; não pega regressão de contrato real com o backend (ex. schema de resposta mudar) — é uma limitação aceita, não um objetivo.

## Limitação conhecida: Service Worker e IndexedDB

Service Workers **não registram em origem `file://`** — esse padrão não serve para testar `frontend/js/sync.js` (fila de sincronização offline) ou fluxos que dependem do Service Worker interceptando requisições. Cobrir isso exigiria servir o harness por HTTP (ex. `http.server` num diretório temporário) ou rodar contra o app real. Fora de escopo dos testes atuais.

## Como rodar localmente

```bash
pip install -e ".[dev]"       # instala playwright (entre outras deps de dev)
playwright install chromium   # baixa o browser (~150MB, uma vez só)
make test-db                  # garante que argus_test existe (não é usado por estes testes, mas o conftest.py exige DATABASE_URL apontando pra ele)
DATABASE_URL=postgresql://argus:argus_dev@localhost:5432/argus_test \
  pytest tests/e2e/frontend -v
```

Sem `playwright install chromium`, cada teste é pulado individualmente (`pytest.skip("Chromium indisponível...")`) em vez de falhar — rodar a suíte sem o browser instalado não quebra o CI, só não exercita nada.

**WSL:** o Chromium do Playwright precisa de libs de sistema que a imagem WSL padrão não tem (`libnspr4`, `libnss3`, etc.). Se `playwright install chromium` reclamar de shared library ausente ao rodar:

```bash
sudo apt-get install -y libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
  libgbm1 libpango-1.0-0 libcairo2 libasound2t64
```

Isso é uma particularidade do ambiente de dev local — o runner do CI (`ubuntu-latest`) já vem limpo, sem esse problema.

## Como adicionar um harness novo

1. Crie `harness/<nome>.html`: estuba os globais que o(s) arquivo(s) real(is) dependem (`window.api`, e qualquer outra função global referenciada — ver exemplos em `harness/login.html` e `harness/abordagem_nova.html`), depois carregue os arquivos reais via `<script src="...">`, monte o HTML da página/componente no DOM, e carregue `alpine.min.js` com `defer` por último (o Alpine precisa inicializar depois que o DOM já existe).
2. Crie `test_<nome>.py`: fixture `harness(tmp_path)` copia os arquivos reais de `frontend/js/` + o HTML do harness + `alpine.min.js` para `tmp_path`; cada teste abre `file://{harness}` via `sync_playwright()`, usa `page.add_init_script(...)` para controlar as respostas estubadas daquele cenário específico, interage via `page.locator(...)`/`page.get_by_role(...)`, e inspeciona estado via `page.evaluate("window.__calls")` ou uma função `window.__state()` exposta no harness.
3. Sempre envolva `browser = p.chromium.launch()` num `try/except PlaywrightError: pytest.skip(...)` — mantém a suíte "pulando" graciosamente em vez de falhar quando o Chromium não está disponível no ambiente.
