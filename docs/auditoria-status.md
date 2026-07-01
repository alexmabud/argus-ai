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

## Grupo 2 — Important: Segurança/autorização/multi-tenancy ✅ CONCLUÍDO

Plano: `docs/plans/2026-06-27-auditoria-grupo2-seguranca.md` (gitignored).
Decisões: D-G2-1 fail-open + log error · D-G2-2 CPF global · D-G2-3 manter "Geral" (trade-off aceito) · D-G2-4 proxy de geocoding.

**Sub-lote 2A ✅**

| # | Achado | Commit |
|---|--------|--------|
| 2 | admin delegado via usuários de todas as equipes | `aad5c91` |
| 6 | sync vaza `str(e)` + sessão envenenada (sem rollback) | `bd2d8fc` |
| 9 | tasks face/pdf engoliam exceção → sem retry arq | `7fe73b7` |
| 10 | XSS em perfil (`iniciais`/`matrícula` sem escape) | `c22380a` |

**Sub-lote 2B ✅**

| # | Achado | Resolução |
|---|--------|-----------|
| 1 | `login_guard` fail-open silencioso quando Redis cai (D-G2-1) | Mantém fail-open (lockout por conta no DB é a defesa primária) + `logger.error` em `ip_bloqueado` quando o bloqueio por IP é desativado |
| 4 | Mídia de abordagem no `/storage` usava tenant estrito → 403 indevido | **Corrigida para GLOBAL** (`67420a6`, após esclarecimento do dono do produto): foto de abordagem é servida a qualquer usuário autenticado — a **ficha da pessoa** mostra fotos e GPS das abordagens de todas as equipes. O `isolamento_abordagens` atua **só na listagem** de relatórios/consultas (`filtros_abordagem`/`_filtros_consulta`), nunca na mídia. PDF de ocorrência (RAP) segue tenant-scoped |
| 5 | Refresh não rotacionava `sid` → refresh token roubado seguia válido | Rotação de `sid` no refresh p/ usuário comum (admin mantém — sessão multi-dispositivo) + `commit` no router `/refresh` |
| 7 | CPF buscado global (D-G2-2) | Já consistente — **no-op** (`pessoa_service.buscar` passa `guarnicao_id=None`) |
| 8 | Auto-criação da guarnição "Geral" (D-G2-3) | Mantida — trade-off de UX aceito, **no-op** |

> Nota: a mídia de abordagem no `/storage` é **global** — a ficha da pessoa expõe
> fotos/GPS de todas as equipes (regra de negócio). O `isolamento_abordagens` só
> muda a **listagem de relatórios** (não revela quem fez). O teste
> `test_storage_proxy_midia_de_abordagem_e_global_mesmo_com_isolamento` valida que a
> foto de outra equipe é servida mesmo com o isolamento ligado (só o PDF de RAP é tenant).

**Verificação:** `ruff` limpo; testes-alvo verdes por achado (login_guard 1/1;
auth/sessão 41/41; permissions_abordagem 7/7; storage_proxy 15/15;
consulta/abordagens/fotos/analytics 44/44). Suíte completa confirmada ao fim do sub-lote.

**Sub-lote 2C ✅**

| # | Achado | Resolução |
|---|--------|-----------|
| 11 | Rotas admin sem guard client-side (defesa em profundidade) | `navigate()` bloqueia `admin-usuarios` (is_admin/super) e `admins` (super) com fallback p/ home; backend já valida cada chamada |
| 12 | `gps.js` enviava coordenadas precisas direto ao Nominatim/OSM (D-G2-4) | Novo `GET /geocode/reverse` (autenticado) delega ao `GeocodingService`; `gps.js` chama o backend |
| 13 | `sync_from_prod.sh` copiava `ENCRYPTION_KEY` de prod p/ dev | Default não copia (mantém/gera chave local); copiar a chave-mestra vira opt-in `--with-prod-key` (`make sync-from-prod KEY=1`) |
| 14 | `anonimizar_dados.py` não apagava fotos do storage (docstring mentia) | Apaga arquivos (original+thumb) do storage, limpa URLs/embeddings, loga IDs; corrige bug pré-existente `deleted_at`→`desativado_em` que abortava o script |

**Verificação:** `ruff` limpo; `bash -n`/`node --check` OK; geocode 3/3, `_storage_key` 3/3,
anonimizar `--dry-run` OK. Suíte completa confirmada ao fim do grupo.

> Decisão #13 (usuário): opt-in via flag — seguro por padrão, chave de prod só sob demanda.

## Grupo 3 — Important: Frontend/offline/PWA ✅ CONCLUÍDO

Fonte: seção "Frontend, offline-first e PWA" do `code-review-consolidado.md` (5 achados).
Frontend sem harness de teste JS → verificação por `node --check` + smoke HTTP + revisão
(mesmo padrão do Grupo 1); confirmação visual final via `make dev` recomendada.

| # | Achado | Resolução | Commit |
|---|--------|-----------|--------|
| G3-1 | Libs de CDN sem SRI + SW ignora cross-origin → 1º uso offline quebra | Self-host (vendoring) de Alpine/ApexCharts/QRCode/Dexie/Leaflet+plugins em `frontend/vendor/` (same-origin) + precache no SW; inclui imagens do Leaflet (exceção no `.gitignore`) | `229e30f` `998cc57` |
| G3-2 | `syncQueue.dados` (PII de campo) em claro no IndexedDB | Cifra o payload (AES-GCM) no enqueue, decripta em `getPendingSync`, tolerante a migração | `dde9a40` |
| G3-3 | Itens `failed` nunca reprocessados → perda silenciosa | `getPendingSync`/`countPending` reprocessam `failed` com `tentativas < MAX_SYNC_ATTEMPTS` (5) | `a566349` |
| G3-4 | Logout agressivo em falha de rede no boot (apaga fila offline) | `fetchMe` só desloga em 401; rede/5xx preservam a sessão | `de82484` |
| G3-5 | Busca decripta todo o cache de pessoas a cada tecla | Memoiza o cache decriptado; invalida em `cachePessoas`/`clearLocalDB` | `ace5665` |

> Decisão G3-1 (usuário): self-host/vendoring (resolve offline-first + supply-chain).
> Tiles do mapa (OSM) seguem externos por natureza (não vendoráveis).

## Grupo 4 — Important: Migrations/banco (Alembic) ✅ CONCLUÍDO

Decisão de escopo (usuário): **forward-path** — corrigir só o caminho que roda em
deploy (`upgrade head`). Migrations já aplicadas e imutáveis; `downgrade` nunca
roda em prod; testes usam `create_all` (não migrations); `env.py` já filtra Tiger
do autogenerate. Validado com `alembic upgrade head` em **banco limpo descartável**
(`argus_migtest`): head único `b7c1d2e3f4a5`, extensões criadas pela migration.

| # | Achado | Resolução | Commit |
|---|--------|-----------|--------|
| G4-1 | Extensões (vector/postgis/pg_trgm) usadas no schema mas nunca criadas por migration | `CREATE EXTENSION IF NOT EXISTS` no topo do upgrade do `schema_inicial` → chain self-contained (no-op se já criadas pelo bootstrap) | `a381f72` |
| G4-3 | `0193ae0cadf6`: `SET NOT NULL` em `bpm_id` sem cobrir guarnições inativas/sem unidade | Seed inclui inativas + fallback BPM "Sem Unidade" antes do NOT NULL | `d62b5fe` |
| G4-4 | `cc1234567890`: `SET NOT NULL` em `guarnicao_id` sem backfill | Backfill dos NULL para a 1ª guarnição antes do NOT NULL | `d62b5fe` |
| G4-5 | `c3d4e5f6a7b8`: cast `detalhes::jsonb` frágil para texto legado | `CASE` tolerante (NULL/''→NULL; JSON→cast; resto→`to_jsonb`) | `f241f12` |

> **Known-debt (G4-2, decisão forward-path):** os `downgrade()` de `schema_inicial`
> (~680 linhas) e `9a79fc5e1da2` (~1000 linhas) recriam tabelas Tiger/PostGIS (lixo
> de autogenerate). Não removido: downgrade nunca roda em prod e os testes não usam
> migrations. `env.py` já filtra esses objetos para migrations futuras. Limpeza
> adiada para o Grupo 10 (Minor) se desejado.


## Grupo 5 — Important: Deploy/restore/scripts ✅ CONCLUÍDO

Verificação: `bash -n` em todos os scripts editados + sintaxe Python + teste do
auto-detect de container. Ground truth de prod (confirmada): dir `~/argus-ai`,
container DB `argus-ai-db-1` (o `deploy.yml` faz `cd ~/argus-ai`; o deploy real
é via CI, não pelo `deploy.sh`).

| # | Achado | Resolução | Commit |
|---|--------|-----------|--------|
| G5-1 | `restore_from_backup.sh`: `set -e` encerrava antes de religar api/worker se `pg_restore` falhasse | Captura o rc do `pg_restore`; sempre religa api/worker; falha depois | `38175a6` |
| G5-2 | Restore do Grafana movia o dir ativo antes do `tar`; falha deixava Grafana sem dados | Extrai para staging e só troca o dir ativo se o `tar` funcionar | `38175a6` |
| G5-3 | `backup_rclone.sh`: retenção remota por ordenação textual (`ls\|sort\|head`) | `rclone delete --min-age Nd` (por data, como o `backup_to_clouds.sh` vivo) + marca o script como deprecado | `bdc8f25` |
| G5-4 | Nomes/paths divergentes (`argus-db` vs `argus-ai-db-1`, `~/argus_ai`/`/opt/argus_ai` vs `~/argus-ai`) | `deploy.sh`/`setup_oracle.sh` → `~/argus-ai`; `security_check.sh` auto-detecta o container (dev/prod) | `c0e6af5` |
| G5-5 | `setup_oracle.sh` referencia `python -m scripts.seed` (inexistente) | Próximos-passos corrigidos: `alembic upgrade head` + `definir_super_admin`; aponta `setup_rclone.sh` | `c0e6af5` |
| G5-6 | `reset_usuario.py` destrutivo sem confirmação explícita | Confirmação interativa ("digite 'apagar'") além do guard de ambiente; `--yes` p/ automação | `fe47d1d` |

> Nota: o script vivo de backup offsite (`backup_to_clouds.sh`) já fazia retenção
> correta por `--min-age`; o bug do G5-3 estava só no `backup_rclone.sh` (duplicado,
> agora marcado como deprecado — remoção pode ir pro Grupo 10).


## Grupo 6 — Important: Docker/infra/supply-chain ✅ CONCLUÍDO

Decisão (usuário): **subir runtime para Python 3.12** (alinha lock + dev + prod).
Verificação: `docker compose config` OK (dev, prod, prod+monitoring); lock
regenerado e inspecionado. ⚠️ O **build da imagem de prod** (G6-2 `--require-hashes`
+ torch cpu) não é validável localmente sem rebuild pesado — o gate é o build da
CI no deploy (uma falha aborta o deploy; prod segue na imagem antiga).

| # | Achado | Resolução | Commit |
|---|--------|-----------|--------|
| G6-1 | Lock desalinhado (cryptography 48 vs >=49; Python 3.12 vs runtime 3.11) | Runtime → 3.12; `make lock` com `--extra vision`; lock regenerado (cryptography→49, inclui vision) | `9e5977e` `7ef7325` |
| G6-2 | `Dockerfile.prod` instalava `.[vision]` ignorando o lock com hashes | `pip install --require-hashes -r requirements.lock` (copia o lock) | `9e5977e` |
| G6-3 | torch/torchvision sem pin; dev sem `[vision]` | torch/torchvision pinados (cpu, == lock); api dev instala `.[vision]` | `9e5977e` |
| G6-4 | `db.Dockerfile` base sem digest | Pin por digest (manifest-list multi-arch) | `9717bef` |
| G6-5 | Volume InsightFace em `/root/.insightface` (worker roda como appuser) | → `/home/appuser/.insightface`. MinIO público no dev mantido (intencional; prod já privado) | `4cf526f` |
| G6-6 | Grafana embedding; postgres-exporter `DB_PASSWORD` opcional; bind mounts `/mnt/banco` quebram local | `GF_SECURITY_ALLOW_EMBEDDING=false`; `DB_PASSWORD` obrigatório (`:?`); device dos volumes configurável | `4cf526f` `7ef7325` |
| G6-7 | `make monitoring` aplicava `chmod 777` | `chown` aos UIDs dos containers (65534/472) | `7ef7325` |
| G6-8 | `.env.production.example` sem vars obrigatórias | Adiciona APP_DB_*, MIGRATION_DATABASE_URL, REDIS_PASSWORD, DOMAIN, GF_*, TELEGRAM_*; marca LLM como legado | `84b1f2c` |
| G6-9 | `supercronic` baixado sem checksum | Verifica sha256 (`sha256sum -c`) com ARG de versão/hash | `9717bef` |


## Grupo 7 — Important: Observabilidade ✅ CONCLUÍDO

Verificação: YAML do `rules.yml` (18 alertas, 5 grupos) e do `deploy-monitoring.yml`
OK; JSON do dashboard OK; `daily_report.py` ruff limpo.

| # | Achado | Resolução | Commit |
|---|--------|-----------|--------|
| G7-1 | Alertas com `noDataState/execErrState: OK` → exporter morto mascara falha | Os 5 críticos de disponibilidade/backup (API/PostgreSQL/Redis/MinIO Offline, Backup Atrasado) → `Alerting`. CPU/Disco críticos ficam cobertos pelo meta `up==0` | `efdc137` |
| G7-2 | Faltam alertas `up==0`, watchdog, backup-nuvens, disco `/mnt/banco` | + `alert-target-down` (up==0, noData=OK pois vazio=saudável), `alert-backup-clouds-falhou`, `alert-disco-banco`. Watchdog Telegram dead-man = follow-up (precisa receptor externo) | `efdc137` |
| G7-3 | Reporter: erros do Prometheus viram `None` silencioso | `raise_for_status()` + log em stderr (erro ≠ sem-dados) | `6ac14dc` |
| G7-4 | Painel "Latência por endpoint" usa `highr` (sem label de rota) | → `http_request_duration_seconds_bucket` por `handler`; p95 global segue no highr | `6ac14dc` |
| G7-5 | `deploy-monitoring.yml` apagava TSDB/Grafana a cada run | Remove o `rm -rf`; chown/chmod corrigem perms sem perder dados | `25715c1` |
| G7-6 | `blackbox-exporter` (já no compose) omitido do deploy/Makefile | Adicionado ao `deploy-monitoring.yml` e aos targets `monitoring`/`-local`/`-down` | `25715c1` |


## Grupo 8 — Important: Performance ✅ CONCLUÍDO

Verificação: ruff limpo; testes-alvo (abordagem/foto/consulta/fotos-api) **42 passed**;
suíte completa confirmada ao fim. Mudanças backward-compatible (params com default).

| # | Achado | Resolução | Commit |
|---|--------|-----------|--------|
| G8-1 | Paginação em memória após carregar todas as linhas (fotos, abordagens por pessoa) | `OFFSET/LIMIT` no SQL: `get_by_pessoa`/`get_by_abordagem` (foto) e `list_by_pessoa` (abordagem, selectinload) recebem skip/limit; routers param de fatiar `[skip:skip+limit]` em memória | `b9f51fd` `571ebf4` |
| G8-2 | Query de localidade sem `LIMIT` (carregava milhares) | `search_by_localidade_ids_com_endereco` recebe skip/limit + `OFFSET/LIMIT`; alinha à busca por bairro/cidade | `3552a6f` |
| G8-3 | Race em `client_id` sem handler de `IntegrityError` | `criar_abordagem` captura `IntegrityError` no flush (índice único parcial), faz rollback e retorna a abordagem vencedora — idempotente sob concorrência em vez de 500 | `571ebf4` |

> Nota infra: durante a verificação o container `argus-db` caiu e travou os testes
> (conexão pendurada). Resolvido com `make test-db`; os fixes não tinham relação.


## Grupo 9 — Important: Testes/cobertura ✅ CONCLUÍDO

Verificação: ruff limpo; testes-alvo **39 passed, 3 skipped** (argus_app skip sem
APP_DATABASE_URL); suíte completa confirmada ao fim. ci.yml validado (YAML).

| # | Achado | Resolução | Commit |
|---|--------|-----------|--------|
| G9-1 | Suite `argus_app` pulada sem `APP_DATABASE_URL`; teste DML só fazia SELECT | Teste DML fortalecido p/ INSERT/UPDATE/DELETE reais (net-zero). Un-skip no CI (provisionar `argus_app` + APP_DATABASE_URL com default privileges) fica como **follow-up** | `b83b3e3` |
| G9-2 | Sync batch sem happy path real | `/sync/batch` cria pessoa de fato + verifica no banco | `b83b3e3` |
| G9-3 | Busca facial/OCR só testava 401 | Similaridade pgvector exercitada com embeddings 512-dim sintéticos (sem InsightFace) | `b83b3e3` |
| G9-4 | Asserts frouxos `in (400,401)` em auth | `== 401` (todos são `CredenciaisInvalidasError`) | `5f5ed90` |
| G9-5 | Sem testes p/ crypto/login_guard/auth_cookie | Novos testes: crypto (round-trip+hash), auth_cookie (flags), login_guard (bloqueio+reset) | `fd9161a` |
| G9-6 | Fixture `setup_db` autouse acopla unit ao banco | **Known-debt documentado**: desacoplar exige opt-in em ~94 arquivos de teste (autouse session-scoped); risco alto vs valor — adiado | — |
| G9-7 | Teste tautológico de LIMIT | Inspeciona a statement compilada, exige `LIMIT 100` (cap) | `5f5ed90` |
| G9-8 | Sem smoke de migrations no CI | Passo no CI: `alembic upgrade head` em banco limpo, exige head único | `cf00252` |

> Follow-ups (gaps conscientes): un-skip do `argus_app` no CI (G9-1); teste de
> upload de PDF do `ocorrencia_service` (G9-5, pesado — PDF + arq); refactor do
> `conftest.setup_db` (G9-6). Nenhum bloqueia; documentados para não se perderem.


## Grupo 10 — Minor/Nit ✅ CONCLUÍDO

Abordagem: priorizados os nits de **segurança** + wins fáceis de limpeza; o restante
(cosmético/arriscado) documentado como aceito/adiado. Verificação: ruff limpo;
testes-alvo 52/52 (inclui `test_totp_lockout`); **suíte completa 655 passed, 5
skipped, 0 failed**.

### Corrigidos

| Tema | Achado | Resolução | Commit |
|------|--------|-----------|--------|
| Segurança | TOTP errado não contava lockout | TOTP incorreto (senha certa) incrementa `tentativas_falhas` e bloqueia; + `test_totp_lockout` | `7275f84` |
| Segurança | Wildcard injection em `pessoa_repo.py:78` | Escapa `% _ \` dos tokens + `ESCAPE` no LIKE | `7275f84` |
| Segurança | `X-XSS-Protection` obsoleto | `1; mode=block` → `0` (proteção real = CSP) | `7275f84` |
| Limpeza | Componentes JS mortos (`sync-queue.js`, `offline-indicator.js`) | Removidos (sem caller) + tags no index | `7275f84` |
| Limpeza | `db.Dockerfile` sem `HEALTHCHECK` | `HEALTHCHECK pg_isready` no nível da imagem | `5d1da7d` |
| Supply chain | `requests==2.31.0` (CVEs) no reporter | → `2.32.4` | `5d1da7d` |
| Testes | `factories.py` com import quebrado (`Passagem`) | Remove `PassagemFactory` + import (feature descontinuada) | `5d1da7d` |

### Já resolvidos antes / no-op
- `/metrics` sem auth → o `Caddyfile` já faz `respond /metrics 403` (externo); Prometheus scrapeia interno.
- Testes de whitespace em consultas → já adicionados no Grupo 1 (`test_consulta_q_so_whitespace_*`).

### Nits aceitos / adiados (cosméticos ou de risco desproporcional)
- **Frontend**: CSP mais restritiva (risco de quebrar o app), `viewport` bloqueia zoom, UX 2FA, páginas monolíticas, índices Dexie vs cripto, ausência de harness de testes JS.
- **Alembic**: revision IDs artificiais, downgrades vazios (known-debt do Grupo 4), docstring `Revises:` divergente.
- **App**: doc desatualizada em `consultas.py`, pool arq por request, body `dict` não-tipado em `admin.py`.
- **Docker/infra**: `COPY . .` antes de deps, single-stage dev, roteamento do `Caddyfile`, `postgres-exporter sslmode=disable` (conexão interna — aceito), `.dockerignore` não exclui `frontend/` (o prod precisa do frontend).
- **Monitoring/scripts/root**: `render-provisioning.sh` token literal, `alert-ssl-expirando`, config morta cAdvisor, `curl | sh`, shebangs, `.secrets.baseline` órfão, README/árvore defasada.


