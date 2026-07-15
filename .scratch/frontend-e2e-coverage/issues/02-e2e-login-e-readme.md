Status: ready-for-execution

## Parent

[../spec.md](../spec.md)

## Blocked by

Issue 01 (precisa do Playwright de fato instalado e rodando no CI antes de escrever teste novo contra ele).

## What to build

Novo arquivo `tests/e2e/frontend/test_login.py`, seguindo o mesmo padrão de harness dos 2 testes existentes (arquivos reais do frontend copiados para um diretório temporário, API estubada, Playwright/Chromium headless via `file://`): cobrir o fluxo de login (`frontend/js/pages/login.js` + `frontend/js/auth.js`).

Cenários mínimos:
- Login com sucesso: API estubada retorna usuário válido em `/auth/login` + `/auth/me`; assert que `onLogin(user)` é chamado no host `[x-data='app()']` com o usuário certo.
- Credenciais inválidas: API estubada retorna erro; assert que `erro` é setado e `onLogin` NÃO é chamado.
- Fluxo 2FA: primeira tentativa sem `totpCode` retorna erro pedindo TOTP; assert que `mostrarTotp` vira `true`; reenviar com código completa o login (mesmo assert de sucesso acima).

Também escrever `tests/e2e/frontend/README.md` curto explicando o padrão de harness (por que `file://` + API estubada, como copiar os arquivos reais do frontend, como rodar localmente, a limitação conhecida de Service Worker/IndexedDB não funcionar em `file://`).

## Acceptance criteria

- [ ] `test_login.py` cobre os 3 cenários acima (sucesso, credenciais inválidas, 2FA).
- [ ] Testes usam arquivos reais de `frontend/js/pages/login.js` e `frontend/js/auth.js` (copiados no harness, não reimplementados/mockados).
- [ ] `tests/e2e/frontend/README.md` existe e documenta o padrão (harness, `file://`, API estubada, como rodar local, limitação de Service Worker).
- [ ] `pytest tests/e2e/frontend/test_login.py -v` passa local e no CI.
- [ ] `make lint` continua limpo.

## Verification

`pytest tests/e2e/frontend/test_login.py -v` local e confirmação no log do job `test` do CI de que os 3 cenários passam.
