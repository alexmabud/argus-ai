# Relatório Consolidado de Code Review — Argus AI

> Fonte de verdade da auditoria (`auditoria/code-review-fixes`). Reconstruído a
> partir do relatório original (o paste veio com encoding quebrado); conteúdo
> técnico — caminhos `arquivo:linha` e achados — preservado fielmente.
> Acompanhe o progresso por grupo em [auditoria-status.md](auditoria-status.md).

- **Data:** 2026-06-27
- **Branch / commit:** `main` @ `c1f4c00`
- **Skill:** `.cursor/skills/code-review`
- **Escopo:** revisão paralela de 8 áreas (`alembic/`, `app/`, `docker/`, `frontend/`, `monitoring/`, `scripts/`, `tests/`, root)
- **Modo:** estado atual do repositório (working tree limpo — sem diff pendente)
- **Origem:** consolidação de três revisões independentes (GPT, Opus, Composer), deduplicadas

## Limitações

- Nenhum fixed point de diff informado; agentes usaram `git status`, histórico recente e inspeção estática por escopo.
- Em escopos sem diff ativo, achados refletem riscos do estado atual, não de um patch específico.
- Nenhum agente modificou arquivos durante a revisão.

## Sumário executivo

Base madura em autenticação (JWT com `iss/aud/sid`, bcrypt, TOTP, cookies HttpOnly, sessão exclusiva), validação de config no startup, multi-tenant centralizado, least-privilege no banco (`argus_app` DML-only), portas em loopback, containers non-root e auditoria LGPD.

Consolidados **9 Critical**, **~35 Important** (únicos, pós-dedup) e dezenas de Minor/Nit. Riscos mais urgentes:

1. **Deploy/produção** — healthcheck do Redis autenticado quebrado; `deploy.sh` desatualizado; chave de criptografia placeholder.
2. **Consultas e isolamento** — parâmetros só com whitespace geram buscas globais; lacunas de tenant em fotos/admin/storage.
3. **Frontend offline-first** — criptografia at-rest inativa, cache sensível sem limpeza no logout, fotos offline perdidas, `downloadBlob` quebrado após reload.
4. **Operação silenciosa** — migrations/restore/reporter/scripts que mascaram falha ou deixam serviços parados.
5. **Supply chain** — lock desalinhado, build de produção fora do lock auditado, dependências sem pin.
6. **Migrations** — extensões PG ausentes no bootstrap, backfill incompleto, downgrades corrompidos.
7. **Observabilidade** — alertas com `noDataState: OK` / `execErrState: OK` e métricas inconsistentes.

### Pontos positivos (transversal)

- Núcleo auth/sessão sólido; proxy `/storage` anti-SSRF; SQL parametrizado; redação de PII em logs.
- Cadeia Alembic íntegra com head único; índices HNSW pgvector com `IF NOT EXISTS`.
- Docker: usuário non-root, healthcheck na API, headers de segurança, `.dockerignore` protege `.env`.
- Frontend: XSS mitigado (Alpine `x-text` + `escapeHtml`); tokens em cookie HttpOnly; mutex no refresh.
- Scripts: `create_app_role.sql` least-privilege; backup GPG AES256; confirmação interativa em operações destrutivas.
- Testes: trava se `DATABASE_URL` não termina em `_test`; boa cobertura de injeção SQL e spoofing de XFF.

---

## Blockers (Critical) — Grupo 1 ✅

| # | Local | Achado | Impacto |
|---|-------|--------|---------|
| 1 | `docker-compose.prod.yml:47-49,84` | Redis sobe com `--requirepass`, mas healthcheck usa `redis-cli ping` **sem senha**. `api`/`worker` dependem de `redis: service_healthy`. | Stack de produção pode nunca liberar API/worker. |
| 2 | `app/api/v1/consultas.py:128,201`, `app/repositories/veiculo_repo.py:80,181`, `app/services/consulta_service.py:355` | `?q=%20%20` e `?placa=%20%20` passam na validação, normalizam para vazio e geram `ILIKE '%%'` com `guarnicao_id=None`. | Retorno amplo de veículos/vínculos globais sem filtro real. |
| 3 | `frontend/js/db.js:21,49,63` | `initCryptoKey()` **nunca é chamado** → `_cryptoKey` null → `encryptField`/`decryptField` devolvem texto puro. | PII em claro no IndexedDB. |
| 4 | `frontend/sw.js:47-74`, `frontend/js/auth.js:48-55` | SW cacheia GET `/api/*` autenticados sem criptografia; `logout()` não limpa Cache Storage nem IndexedDB. | Dados operacionais acessíveis a outro usuário em dispositivo compartilhado. |
| 5 | `frontend/js/pages/abordagem-nova.js:1114-1123` | Fluxo offline enfileira JSON; `File` de fotos não persiste. | Após reload/sync, abordagem pode subir sem mídia (perda irreversível). |
| 6 | `frontend/js/api.js:172-191` | `downloadBlob()` sem `credentials: "same-origin"`, referencia `this.refreshToken` (inexistente). | Download falha após F5 apesar do cookie HttpOnly. |
| 7 | `scripts/deploy.sh:73-84,128-150` | Referencia Nginx/Certbot e arquivos inexistentes; produção usa **Caddy**. | Comandos `setup`/`ssl` quebram ou deixam VM inconsistente. |
| 8 | `scripts/deploy.sh:61-66,120-122` | Se `cryptography` ausente, `ENCRYPTION_KEY` vira `"GERAR-MANUALMENTE"` e deploy continua; falha de `alembic upgrade head` vira só aviso. | Criptografia LGPD inválida e schema desatualizado com deploy "concluído". |
| 9 | `scripts/security_check.sh:43,50,96` | Com `set -e`, `((ERROS++))` quando `ERROS=0` retorna exit 1 → aborta no primeiro FAIL. | Auditoria de segurança interrompida antes do resumo. |

---

## Important (deduplicados)

### Segurança, autorização e multi-tenancy — Grupo 2 ✅

| Local | Achado |
|-------|--------|
| `app/core/login_guard.py:56-58` | Fail-open do bloqueio por IP quando Redis cai. |
| `app/api/v1/admin.py:139-140` | `listar_usuarios` sem `assert_scope` → admin delegado vê usuários de todas as equipes. |
| `app/api/v1/fotos.py:215,242` | Listagem de fotos por pessoa/abordagem sem checagem de tenant → vazamento cross-tenant. |
| `app/main.py:220-223`, `app/core/permissions.py:56-58` | Proxy `/storage` ignora `isolamento_abordagens`; fotos com `guarnicao_id=None` → 403 indevido. |
| `app/services/auth_service.py:227-230` | Refresh token sem rotação (janela longa de reutilização). |
| `app/services/sync_service.py:68` | Erros internos (`str(e)`) expostos ao cliente no sync. |
| `app/services/pessoa_service.py:254-257` | Busca CPF global com unicidade por guarnição — comportamento ambíguo. |
| `app/dependencies.py:125-147` | Criação automática de guarnição "Geral" pode enfraquecer isolamento. |
| `app/tasks/face_processor.py:85`, `app/tasks/pdf_processor.py:132` | `except Exception` retorna status em vez de relançar → `max_tries=3` do arq nunca dispara. |
| `frontend/js/pages/perfil.js:39,78` | XSS em perfil — template sem `escapeHtml`. |
| `frontend/js/app.js:346-358` | Rotas admin acessíveis por hash sem guard client-side. |
| `frontend/js/components/gps.js:13` | Coordenadas precisas enviadas direto ao Nominatim/OSM, sem proxy. |
| `scripts/sync_from_prod.sh:67-73` | `ENCRYPTION_KEY` de produção copiada para `.env` local → base de prod decifrável no dev. |
| `scripts/anonimizar_dados.py:4-5,104-108,129-132` | Docstring promete remover fotos do S3/R2, mas só zera campos no banco; sem log de IDs. |

### Frontend, offline-first e PWA — Grupo 3 ✅

| Local | Achado |
|-------|--------|
| `frontend/index.html:15-21`, `frontend/sw.js:42-45` | App offline-first depende de CDN externa (sem SRI); SW ignora cross-origin → 1º uso offline pode falhar. |
| `frontend/js/db.js:117`, `frontend/js/pages/abordagem-nova.js:1069` | Fila offline persiste `dados` completos (lat/long, observação, pessoas, veículos) no IndexedDB. |
| `frontend/js/sync.js:132-135` | Itens `failed` nunca reprocessados automaticamente → perda silenciosa de dados de campo. |
| `frontend/js/auth.js:57-66` | Logout agressivo em falha de rede no boot. |
| `frontend/js/db.js:187-195` | Busca faz `toArray()` + decrypt de todos os registros a cada digitação. |

### Migrations e banco (Alembic) — Grupo 4 ⏳

| Local | Achado |
|-------|--------|
| `alembic/versions/08ef2221d8ba_schema_inicial.py:48,87,138,294,941,950` | Usa `VECTOR`/`Geography`/`gin_trgm_ops`, mas extensões `vector`/`postgis`/`pg_trgm` nunca criadas por migration; `downgrade` dropa índices inexistentes e recria lixo PostGIS/Tiger. |
| `alembic/versions/9a79fc5e1da2:106-169`, `alembic/env.py:27` | Mesmo padrão de `downgrade` poluído; objetos externos ignorados pelo autogenerate. |
| `alembic/versions/0193ae0cadf6:54-83` | BPMs seedados só de guarnições ativas com `unidade`; `SET NOT NULL` em `bpm_id` aplica a todas. |
| `alembic/versions/cc1234567890:26` | `SET NOT NULL` sem backfill de NULLs em `guarnicao_id`. |
| `alembic/versions/c3d4e5f6a7b8:32` | Cast `detalhes::jsonb` frágil para dados legados. |

### Deploy, restore, scripts e operação — Grupo 5 ⏳

| Local | Achado |
|-------|--------|
| `scripts/restore_from_backup.sh:115` | Se `pg_restore` falhar após parar `api`/`worker`, `set -e` encerra antes de religar serviços. |
| `scripts/restore_from_backup.sh:161` | Restore do Grafana move diretório ativo antes do `tar`; falha deixa Grafana parado. |
| `scripts/backup_rclone.sh:70` | Retenção remota usa `rclone ls \| sort \| head` — ordenação textual, não por data. |
| Vários scripts | Nomes/paths divergentes (`argus-db` vs `argus-ai-db-1`, `~/argus_ai` vs `~/argus-ai`) → checagens puladas silenciosamente. |
| `scripts/setup_oracle.sh:67` | Referencia `python -m scripts.seed`, módulo inexistente. |
| `scripts/reset_usuario.py:36` | Operação destrutiva sem confirmação explícita/allowlist local. |

### Docker, infra e supply chain — Grupo 6 ⏳

| Local | Achado |
|-------|--------|
| `pyproject.toml:32`, `requirements.lock:419`, `Makefile:99` | Lock desalinhado (`cryptography` 48 vs `>=49`, `slowapi`, `pydantic-settings`); lock em Python 3.12 vs runtime 3.11. |
| `Dockerfile.prod:18-21` | Produção instala via `pip install ".[vision]"` → ignora lock com hashes. |
| `docker/api.Dockerfile:17-18` | `torch`/`torchvision` sem pin; dev sem extra `[vision]`. |
| `docker/db.Dockerfile:1` | Base `pgvector/pgvector:pg16` sem digest/patch fixo. |
| `docker-compose.yml:82,97-98,151` | Bucket MinIO público (dev); API em `0.0.0.0:8000`; volume InsightFace em `/root/.insightface` vs `appuser`. |
| `docker-compose.monitoring.yml:47,120-121,176-188` | `GF_SECURITY_ALLOW_EMBEDDING`; `DB_PASSWORD` não obrigatório no postgres-exporter; bind mounts `/mnt/banco/*` quebram monitoring local. |
| `Makefile:106-107` | `make monitoring` aplica `chmod 777` em dados de Prometheus/Grafana. |
| `.env.production.example` | Não documenta variáveis obrigatórias de prod (`REDIS_PASSWORD`, `APP_DB_*`, `GF_ADMIN_PASSWORD`, `TELEGRAM_*`). |
| `monitoring/reporter/Dockerfile:5-9` | `supercronic` baixado sem checksum/assinatura. |

### Observabilidade — Grupo 7 ⏳

| Local | Achado |
|-------|--------|
| `monitoring/grafana/provisioning/alerting/rules.yml:13-14,167` | Alertas críticos (ex.: "API Offline") com `noDataState: OK` e `execErrState: OK` → exporter/datasource morto mascara falha. |
| Regras de alerta (ausência) | Sem alerta-meta `up == 0`, watchdog Telegram, alerta de backup nuvens (`argus_backup_clouds_last_success_timestamp_seconds`) ou disco `/mnt/banco`. |
| `monitoring/reporter/daily_report.py:31,206,268-269` | Erros Prometheus viram `None`; métrica de latência inconsistente com dashboard (`http_request_duration_highr_seconds_bucket` sem label de rota). |
| `monitoring/grafana/dashboards/argus-main.json:220` | Painel "Latência por endpoint" agrupa por `handler`, mas métrica highr padrão não tem labels de rota. |
| `.github/workflows/deploy-monitoring.yml:72` | Deploy apaga TSDB/Grafana a cada run (destrutivo). |
| Deploy monitoring | `blackbox-exporter` omitido em alguns caminhos (`deploy-monitoring.yml`, `Makefile:111`). |

### Performance — Grupo 8 ⏳

| Local | Achado |
|-------|--------|
| `app/api/v1/fotos.py:239,266`, `app/api/v1/pessoas.py:482` | Paginação em memória após carregar todas as linhas. |
| `app/repositories/pessoa_repo.py:228` | Query de localidade sem `LIMIT`. |
| `app/services/abordagem_service.py:96-128` | Race em `client_id` sem handler de `IntegrityError`. |

### Testes e cobertura — Grupo 9 ⏳

| Local | Achado |
|-------|--------|
| `tests/integration/test_db_role_argus_app.py:17-19,60,69` | Suite do papel `argus_app` pulada sem `APP_DATABASE_URL`; teste declarado como DML executa só `SELECT count(*)`. |
| `tests/integration/test_api_sync.py:10-60` | Sync batch sem happy path real → persistência nunca exercida contra DB. |
| `tests/integration/test_api_fotos.py:72-98` | Busca facial/OCR só testam 401; similaridade pgvector nunca exercida. |
| `tests/integration/test_api_auth.py:58,70,169,185,359` | Asserts frouxos (`in (400,401)`) reduzem detecção de regressão. |
| Ausência em `tests/` | Sem testes para `auth_cookie.py`, `crypto.py`, `login_guard.py`, re-login invalidando token anterior, upload PDF (`ocorrencia_service.py`). |
| `tests/conftest.py:62-124` | Fixture global destrutiva `setup_db` acopla unitários puros ao banco. |
| `tests/unit/test_analytics_service.py:84-95` | Teste tautológico de LIMIT 100. |
| `alembic/` | Sem smoke test de `upgrade head` / rollback de migrations críticas em CI. |

---

## Minor / Nit — Grupo 10 ⏳ (destaques)

- **Consultas:** testes para `placa`/`modelo`/`q` só com whitespace; invariante no repositório contra query sem filtros.
- **Alembic:** revision IDs artificiais; `env.py` força asyncpg (offline inviável); downgrades vazios irreversíveis; docstring `Revises:` divergente em `2b532a309319`.
- **App:** commits duplos router + `get_db`; doc desatualizada em `consultas.py`; `/metrics` sem auth; TOTP errado não conta lockout; wildcard injection em `pessoa_repo.py:78`; pool arq recriado por request; body `dict` não-tipado em `admin.py:743`.
- **Docker:** `COPY . .` antes de deps; single-stage com toolchain; `db.Dockerfile` sem `HEALTHCHECK`; roteamento ambíguo no `Caddyfile`; `X-XSS-Protection` obsoleto; worker sem healthcheck (dev); `.dockerignore` não exclui `frontend/`.
- **Frontend:** índices Dexie conflitam com criptografia; sem CSP; `viewport` bloqueia zoom; UX 2FA enganosa; páginas monolíticas (~1165–1600 linhas); componentes mortos (`sync-queue.js`, `offline-indicator.js`); ausência total de testes automatizados.
- **Monitoring:** `render-provisioning.sh` pode subir token literal; `alert-ssl-expirando` dispara errado quando probe falha; `requests==2.31.0` com CVEs; config morta de cAdvisor.
- **Scripts:** `curl | sh` (supply chain); scripts de backup duplicados/divergentes; `trap` com variável não citada; `chmod 755` em diretório de fotos; shebangs inconsistentes; temporários não únicos em `backup_to_clouds.sh:51`.
- **Root:** `.secrets.baseline` órfão; ruff pin defasado; `postgres-exporter` `sslmode=disable` vs `SECURITY.md`; README com árvore defasada.
- **Tests:** duplicação `test_auth.py` vs `test_api_auth.py`; `factories.py` com import quebrado; e2e com sleeps fixos; Redis não resetado entre testes; watermark validada só por desigualdade de bytes.

---

## Mapeamento para os grupos da auditoria

| Grupo | Seção fonte | Status |
|-------|-------------|--------|
| 1 — Blockers (Critical) | Blockers | ✅ |
| 2 — Segurança/autorização/multi-tenancy | Important › Segurança | ✅ |
| 3 — Frontend/offline/PWA | Important › Frontend | ✅ |
| 4 — Migrations/banco (Alembic) | Important › Migrations | ⏳ |
| 5 — Deploy/restore/scripts | Important › Deploy | ⏳ |
| 6 — Docker/infra/supply-chain | Important › Docker | ⏳ |
| 7 — Observabilidade | Important › Observabilidade | ⏳ |
| 8 — Performance | Important › Performance | ⏳ |
| 9 — Testes/cobertura | Important › Testes | ⏳ |
| 10 — Minor/Nit | Minor / Nit | ⏳ |
