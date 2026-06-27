# Status da Auditoria — code-review-consolidado.md

Branch: `auditoria/code-review-fixes` (base `c1f4c00`). Abordagem: um grupo por vez,
cada grupo com o ciclo `diagnose → karpathy → tdd → writing-plans → executing → review → verification`.

## Grupo 1 — Blockers (Critical) ✅ CONCLUÍDO

Plano: [docs/plans/2026-06-27-auditoria-grupo1-criticos.md](plans/2026-06-27-auditoria-grupo1-criticos.md)

| # | Achado | Status | Commit |
|---|--------|--------|--------|
| 1 | Redis healthcheck sem senha trava api/worker | ✅ | `826b850` |
| 2 | Consulta com termo só-whitespace → busca global | ✅ | `d691216` |
| 3 | `initCryptoKey()` nunca chamado → PII em claro no IndexedDB | ✅ | `a035a96` |
| 4 | SW cacheia API autenticada; logout não limpa cache/IDB | ✅ | `a035a96` |
| 5 | Fotos de abordagem offline perdidas | ✅ | `06965b8` |
| 6 | `downloadBlob` quebrado (this.refreshToken inexistente) | ✅ | `f8a836a` |
| 7 | `deploy.sh` refere Nginx/Certbot (prod = Caddy) | ✅ | `f8cb0de` |
| 8 | `deploy.sh` ENCRYPTION_KEY placeholder + migration ignorada + env errado | ✅ | `f8cb0de` |
| 9 | `security_check.sh` aborta no 1º FAIL (`((ERROS++))` + `set -e`) | ✅ | `d344cca` |

**Verificação:** `ruff check app/ tests/` limpo; TDD do #2 (q→422, placa→400, `--`→sem match-all);
healthcheck redis verificado por container; `bash -n` em scripts; `node --check` nos JS;
`docker compose config` OK. **Suíte completa: `620 passed, 5 skipped, 0 failed` (pytest exit 0).**

> Nota: a 1ª execução da suíte pegou 2 unit tests de `test_veiculo_repo.py` que
> codificavam o comportamento antigo (match-all sem filtro); foram corrigidos
> para o contrato seguro (commit `22822fb`).

**Itens correlatos adiados (grupo Important):** reprocessamento automático de itens `failed`
na fila offline; documentar variáveis obrigatórias em `.env.production.example`.

## Grupo 2 — Important: Segurança/autorização/multi-tenancy 🔄 EM ANDAMENTO

Plano: `docs/plans/2026-06-27-auditoria-grupo2-seguranca.md` (gitignored).
Decisões: D-G2-1 fail-open + log error · D-G2-2 CPF global · D-G2-3 manter "Geral" (trade-off aceito) · D-G2-4 proxy de geocoding.

**Sub-lote 2A ✅**

| # | Achado | Commit |
|---|--------|--------|
| 2 | admin delegado via usuários de todas as equipes | `aad5c91` |
| 6 | sync vaza `str(e)` + sessão envenenada (sem rollback) | `bd2d8fc` |
| 9 | tasks face/pdf engoliam exceção → sem retry arq | `7fe73b7` |
| 10 | XSS em perfil (`iniciais`/`matrícula` sem escape) | `c22380a` |

**Pendente:** 2B (#3+#4 cascata de isolamento em fotos/storage; #5 rotação de sid; #1 fail-open log; #7 confirmar CPF global) · 2C (#11 guard rota admin; #12 proxy geocoding; #13 sync_from_prod; #14 anonimizar). Verificação: testes-alvo verdes por achado; suíte completa pendente ao fim do grupo.
## Grupo 3 — Important: Frontend/offline/PWA ⏳ PENDENTE
## Grupo 4 — Important: Migrations/banco (Alembic) ⏳ PENDENTE
## Grupo 5 — Important: Deploy/restore/scripts ⏳ PENDENTE
## Grupo 6 — Important: Docker/infra/supply-chain ⏳ PENDENTE
## Grupo 7 — Important: Observabilidade ⏳ PENDENTE
## Grupo 8 — Important: Performance ⏳ PENDENTE
## Grupo 9 — Important: Testes/cobertura ⏳ PENDENTE
## Grupo 10 — Minor/Nit ⏳ PENDENTE
