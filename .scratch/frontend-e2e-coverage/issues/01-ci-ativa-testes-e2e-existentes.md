Status: ready-for-execution

## Parent

[../spec.md](../spec.md)

## What to build

Declarar `playwright` como dependência de dev do projeto e fazer o job `test` do CI instalar o browser Chromium antes de rodar a suíte. Hoje `tests/e2e/frontend/test_abordagem_nova_pessoas.py` e `tests/e2e/frontend/test_abordagem_nova_gps_bloqueio.py` existem mas são sempre pulados (`pytest.importorskip("playwright.sync_api")` falha) porque `playwright` nunca foi instalado em lugar nenhum do pipeline. Esta fatia não escreve teste novo — só ativa o que já existe.

- `pyproject.toml`: adicionar `playwright` em `[project.optional-dependencies].dev` (mesma lista de `pytest`/`httpx`/etc). Não mexer em `requirements.lock` — ferramenta de teste, não shippada em produção.
- `.github/actions/setup-python-env/action.yml`, step `dev-locked`: incluir `playwright` na linha final de `pip install` (junto de `pytest pytest-asyncio pytest-cov httpx factory-boy`).
- `.github/workflows/ci.yml`, job `test`: novo step "Install Playwright Chromium" (`playwright install --with-deps chromium`) logo após "Setup Python", antes de "Run tests".

## Acceptance criteria

- [ ] `pip install -e ".[dev]"` local instala `playwright`.
- [ ] `playwright install chromium` funciona localmente sem erro (fora do WSL, ou com o contorno já conhecido dentro do WSL).
- [ ] Job `test` do CI tem um step que instala o Chromium antes de "Run tests".
- [ ] Rodando a suíte completa (`pytest -v` ou `pytest tests/e2e/frontend -v`) no CI, os 2 testes existentes aparecem como executados (não `skipped`) e passam.
- [ ] `make lint` continua limpo.

## Blocked by

None — pode começar imediatamente.

## Verification

Push da branch (ou PR) e observar o log do job `test` no GitHub Actions: confirmar que `test_abordagem_nova_pessoas.py` e `test_abordagem_nova_gps_bloqueio.py` rodam e passam, sem `SKIPPED`. Localmente: `pip install -e ".[dev]" && playwright install chromium && pytest tests/e2e/frontend -v`.
