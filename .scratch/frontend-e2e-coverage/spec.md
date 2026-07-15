# Spec

## Problem

Hoje o frontend (`frontend/` — PWA Alpine.js + Tailwind, sem build step) não tem nenhuma cobertura de teste automatizada que realmente rode. Já existem 2 arquivos de teste e2e escritos com Playwright via harness ([tests/e2e/frontend/test_abordagem_nova_pessoas.py](tests/e2e/frontend/test_abordagem_nova_pessoas.py), [tests/e2e/frontend/test_abordagem_nova_gps_bloqueio.py](tests/e2e/frontend/test_abordagem_nova_gps_bloqueio.py)), mas `playwright` nunca foi declarado como dependência do projeto (fora de `pyproject.toml` e `requirements.lock`), e o step `dev-locked` de [.github/actions/setup-python-env/action.yml](.github/actions/setup-python-env/action.yml#L46-L67) nunca instala o pacote nem o browser Chromium. Por isso `pytest.importorskip("playwright.sync_api")` sempre falha em CI e localmente (a menos que um dev instale manualmente) — esses 2 testes nunca rodaram em CI desde que foram escritos, criando falsa sensação de cobertura. A única verificação real de frontend hoje é manual, em navegador (skill `frontend-testing`).

## Scope

- Declarar `playwright` como dependência de dev em `pyproject.toml` (`[project.optional-dependencies].dev`), sem tocar `requirements.lock` — mesma trilha já usada por `pytest`/`httpx` no step `dev-locked` (ferramenta de teste, não shippada em produção).
- Instalar o browser Chromium do Playwright no job `test` de [.github/workflows/ci.yml](.github/workflows/ci.yml#L70-L190), após o step "Setup Python" e antes de "Run tests".
- Isso sozinho já ativa os 2 testes existentes — passam a rodar de verdade em todo PR/push na main.
- Cobertura nova: fluxo de **login** ([frontend/js/pages/login.js](frontend/js/pages/login.js#L91-L131) + [frontend/js/auth.js](frontend/js/auth.js#L33-L48)), no mesmo padrão de harness (arquivos reais do frontend copiados para um HTML isolado, API estubada, Playwright/Chromium headless via `file://`): login com sucesso, credenciais inválidas, fluxo de 2FA/TOTP (`mostrarTotp`).
- README curto em `tests/e2e/frontend/` documentando o padrão de harness, para o próximo dev (ou eu, numa próxima sessão) não precisar redescobrir a convenção.

## Out of scope

- Sync offline (`frontend/js/sync.js`, `frontend/js/db.js`, IndexedDB/Dexie, Service Worker). O harness atual abre o HTML via `file://`, e Service Workers não registram em origem `file://` — cobrir esse fluxo exige servir o harness por HTTP ou rodar contra o app real (uvicorn + Postgres/Redis/MinIO, como o job `test` já faz para pytest). Registrado como próximo passo, não nesta entrega.
- Rodar os testes de frontend contra o backend real — o padrão atual estuba a API deliberadamente (rápido, isolado, sem infra); trocar de abordagem é decisão separada.
- Ampliar cobertura além de login (consulta, ocorrências, admin, etc.) — próxima fatia, depois que o padrão estiver rodando em CI de verdade.
- Testes unitários de JS (Vitest/jsdom) para lógica pura — descartado nesta rodada (usuário escolheu e2e Playwright como primeira fatia, ver decisão registrada na conversa).

## Acceptance criteria

1. `pyproject.toml` declara `playwright` em `[project.optional-dependencies].dev`; `pip install -e ".[dev]"` local instala o pacote.
2. Job `test` do CI instala o Chromium do Playwright antes de "Run tests".
3. `pytest tests/e2e/frontend -v` em CI executa os 2 testes existentes de verdade (não aparecem como `skipped`) e passam.
4. Novo `tests/e2e/frontend/test_login.py` cobre no mínimo: (a) login com sucesso chama `onLogin` com o usuário retornado pela API estubada; (b) credenciais inválidas mostra `erro` sem chamar `onLogin`; (c) resposta pedindo 2FA ativa `mostrarTotp`, e reenviar com o código completa o login.
5. `make test` local roda os mesmos testes sem infra extra além de `playwright install chromium` (documentado no README novo).
6. CI continua verde; timeout do job `test` (hoje 40min) mantém folga. **Atualização pós-review:** em vez de medir o tempo real e decidir depois, o `code-review` da branch já flagou o custo (~150MB de Chromium sem cache) e o risco de um step obrigatório derrubar o job inteiro numa falha transiente de rede/apt — decisão tomada direto: `actions/cache` em `~/.cache/ms-playwright` (chave pinada em `playwright-chromium-${{ runner.os }}-1.60.0`) + `continue-on-error: true` no step de instalação, preservando a degradação graciosa que os testes já tinham via `pytest.importorskip`/`try-except` em `chromium.launch()`.

## Decisions

- Reusa o padrão de harness já existente em vez de introduzir Vitest/jsdom ou apontar Playwright contra o app real — menor risco, consistente com o que já existe e já provou valor (2 regressões reais pegas por esse padrão antes de serem mescladas).
- `playwright` entra como dependência de dev não hash-pinada (mesma trilha de `pytest`/`httpx` no step `dev-locked`) — não entra em `requirements.lock`, não é shippado em produção.
- Primeira fatia nova de cobertura = login: é o gate de entrada de todo o resto do app e é mais simples de estubar que sync offline (sem IndexedDB/Service Worker envolvidos).

## Risks

- `playwright install --with-deps chromium` no CI baixa/instala pacotes de sistema no runner — aumenta o tempo do job `test`, que já roda com timeout de 40min por causa da instalação do lock completo (torch/insightface/etc). Mitigação: medir o tempo real adicionado no Build; considerar cache do Playwright entre runs se for significativo.
- Ambiente de dev local do usuário (WSL) já teve problema conhecido com Chromium do Playwright sem libs de sistema (registrado em memória própria — WSL sem libs, contornado dirigindo o Edge do Windows). Isso não afeta o CI (`ubuntu-latest` é limpo), mas pode significar que rodar esses testes localmente no WSL exige o mesmo contorno. Anotar no README novo.
- Harness estuba a API — testa o frontend isoladamente, não pega regressão de contrato real com o backend (ex.: schema de resposta de `/auth/login` mudar). Esse gap já existia nos 2 testes atuais; aceito conscientemente (mesma limitação, não piora nem resolve nesta entrega).

## Verification

- `pytest tests/e2e/frontend -v` local (após `pip install -e ".[dev]"` e `playwright install chromium`) — todos os testes (2 existentes + login novo) passam, nenhum `skipped`.
- Push da branch e observação do job `test` do CI numa PR de verdade — confirmar no log que os testes de `tests/e2e/frontend` aparecem executados (não skipped) e verdes.
- `make lint` limpo.
- Se algum teste falhar no CI, revisão manual do output do Playwright para confirmar que é falha real, não infra quebrada (ex.: Chromium não instalado).
