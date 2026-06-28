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
| 4 | Mídia de abordagem no `/storage` usava tenant estrito, inconsistente com consultas (403 indevido sem isolamento) | `filtros_abordagem` (fonte única equipe>BPM>global) em `permissions.py` + `assert_pode_ver_foto_abordagem`; `_filtros_consulta` passa a delegar |
| 5 | Refresh não rotacionava `sid` → refresh token roubado seguia válido | Rotação de `sid` no refresh p/ usuário comum (admin mantém — sessão multi-dispositivo) + `commit` no router `/refresh` |
| 7 | CPF buscado global (D-G2-2) | Já consistente — **no-op** (`pessoa_service.buscar` passa `guarnicao_id=None`) |
| 8 | Auto-criação da guarnição "Geral" (D-G2-3) | Mantida — trade-off de UX aceito, **no-op** |

> Nota: o fix do #4 mudou o contrato de visibilidade da mídia de abordagem no
> storage (agora segue `isolamento_abordagens`, global por padrão, igual a
> consultas/analytics). O teste `test_storage_proxy_bloqueia_midia_de_abordagem_de_outra_equipe`
> codificava o comportamento estrito antigo e foi substituído por dois casos
> (isolamento ON → 403; OFF → global/200).

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


## Grupo 5 — Important: Deploy/restore/scripts ⏳ PENDENTE
## Grupo 6 — Important: Docker/infra/supply-chain ⏳ PENDENTE
## Grupo 7 — Important: Observabilidade ⏳ PENDENTE
## Grupo 8 — Important: Performance ⏳ PENDENTE
## Grupo 9 — Important: Testes/cobertura ⏳ PENDENTE
## Grupo 10 — Minor/Nit ⏳ PENDENTE
