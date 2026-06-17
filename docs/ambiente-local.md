# Argus AI — Ambiente de Desenvolvimento Local

Guia de como rodar o Argus na sua máquina, as diferenças entre os modos de
execução, e como (e quem pode) carregar os dados reais da VM de produção para
testar localmente.

> **Resumo de uma linha:** o código e as *receitas* (Dockerfiles, compose) vão
> pro Git; os **containers e dados não**. Cada máquina constrói seus próprios
> containers a partir da receita, e começa com **banco vazio** — só o dono
> consegue sincronizar os dados reais da VM.

---

## 1. Os três ambientes

| | `make dev` | `docker compose up` | Produção |
|---|---|---|---|
| **Onde roda** | seu PC | seu PC | VM Oracle |
| **O que sobe** | db + redis + minio (Docker) e a **API no host** | **tudo** em containers (api + worker + db + redis + minio) | tudo em containers |
| **Dockerfile da API** | nenhum (uvicorn no host) | `docker/api.Dockerfile` | `Dockerfile.prod` |
| **Servidor** | `uvicorn --reload` | `uvicorn --reload` (container) | `gunicorn` + 4 workers |
| **Hot-reload** | ✅ instantâneo | ✅ (via bind mount de `./app`) | ❌ (imagem selada) |
| **Compose file** | `docker-compose.yml` | `docker-compose.yml` | `docker-compose.prod.yml` |
| **Quando usar** | desenvolver rápido | rodar tudo isolado / 1ª vez do colaborador | usuários reais |

> ⚠️ **Não rode `make dev` e `docker compose up` ao mesmo tempo** — os dois
> tentam usar as portas `5432`/`6379`/`9000` e dá conflito. Escolha um.

---

## 2. Como os containers chegam na máquina

O `git clone` **não** baixa containers nem imagens — baixa o **código + as
receitas**. Quem constrói é o Docker, localmente:

```
git clone ─→ código + Dockerfiles + docker-compose.yml (as "receitas")
                     │
            docker compose up
                     │
        ┌─ BUILDA as imagens do Argus (api, worker) a partir de docker/api.Dockerfile
        └─ BAIXA do Docker Hub as bases (postgres, redis, minio)
                     │
        Containers equivalentes — construídos do zero nesta máquina
```

Por isso apagar as imagens `argus_ai-api` / `argus_ai-worker` é inofensivo: o
próximo `docker compose up` as reconstrói da receita (leva ~5-10 min na primeira
vez porque baixa `torch` etc; depois fica em cache).

---

## 3. Volumes: onde os dados ficam (e por que persistem)

Os dados **não** ficam dentro do container — ficam em **volumes Docker** que
sobrevivem a `docker compose down` e a reinícios:

| Volume | Conteúdo |
|---|---|
| `argus_ai_pgdata` | banco PostgreSQL local (`argus_db`) |
| `argus_ai_minio_data` | arquivos/fotos do MinIO local |
| `argus_ai_redis_data` | cache do Redis |
| `argus_ai_insightface_models` | cache dos modelos de reconhecimento facial |

**`make dev` e `docker compose up` usam o MESMO container de banco e o MESMO
volume `pgdata`.** Então, depois que você sincroniza os dados (seção 5), eles
aparecem nos dois modos.

> 🛑 Apagar `argus_ai_pgdata` ou `argus_ai_minio_data` = perder o banco/fotos
> locais. Se forem dados sincronizados de produção, é só rodar o sync de novo.

---

## 4. Setup inicial (primeira vez)

```bash
git clone git@github.com:alexmabud/argus-ai.git
cd argus-ai
cp .env.example .env
python scripts/generate_encryption_key.py   # copie a chave e cole em ENCRYPTION_KEY no .env
```

Depois escolha um modo:

### Opção A — Docker completo (mais simples, recomendado p/ começar)
```bash
docker compose up -d                         # sobe tudo
docker compose exec api alembic upgrade head # cria as tabelas
# acesse http://localhost:8000  (Swagger em /docs)
```

### Opção B — `make dev` (hot-reload, dev do dia a dia)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                      # use ".[dev,vision]" se for mexer com face/OCR
docker compose up -d db redis minio          # só a infra no Docker
make migrate                                 # cria as tabelas (alembic upgrade head)
make dev                                      # API no host com --reload
make worker                                   # em OUTRO terminal (tarefas async)
```

> ⚠️ **Pegadinha do `make dev`:** o `.env.example` traz `DATABASE_URL` apontando
> para o papel de produção (`argus_app:CHANGE_ME`), que **não existe no banco
> local**. Para o `make dev` (API no host) conectar, ajuste no `.env`:
> ```
> DATABASE_URL=postgresql://argus:argus_dev@localhost:5432/argus_db
> ```
> No `docker compose up` isso não importa — o compose sobrescreve a URL.

---

## 5. Carregar dados reais da VM (`make sync-from-prod`) — **só o dono**

Para testar com dados de verdade sem mexer em produção:

```bash
make sync-from-prod   # SSH na VM → pg_dump + fotos → restaura nos volumes locais
                      # + troca sua ENCRYPTION_KEY pela de produção (pra ler CPFs)
make dev              # roda a API local JÁ com os dados de produção
```

O que o script (`scripts/sync_from_prod.sh`) faz, passo a passo:

1. `pg_dump -Fc` do banco na VM (via `ssh argus`)
2. `rsync` das fotos de `/mnt/fotos` (MinIO)
3. Faz backup do seu `.env` em `.env.bak.<timestamp>`
4. Substitui sua `ENCRYPTION_KEY` local pela **de produção** (senão os CPFs não
   descriptografam)
5. Recria o banco `argus_db` local e restaura o dump
6. Restaura as fotos no volume `argus_ai_minio_data`

**Pré-requisitos (só o dono tem):**
- Alias SSH `argus` no `~/.ssh/config` apontando para a VM
- Acesso à VM (chave SSH autorizada)

> 🔐 **LGPD:** depois do sync, seu `.env` local guarda a **chave de produção** e o
> disco passa a ter **CPFs reais**. Exija criptografia de disco (LUKS/BitLocker)
> e bloqueio de tela. Veja `docs/LGPD.md`.

---

## 6. Dono vs Colaborador (por que o colaborador NÃO vê dados reais)

| | Dono (você) | Colaborador |
|---|---|---|
| Acesso SSH à VM | ✅ | ❌ |
| `make sync-from-prod` | ✅ funciona | ❌ sem SSH, não roda |
| `ENCRYPTION_KEY` de produção | ✅ | ❌ |
| Banco local | vazio **ou** dados reais (se sincronizar) | **sempre vazio** (cria dados de teste) |

Isso é **proposital**: os CPFs reais ficam só com o dono. Mesmo que um dump
vazasse, sem a `ENCRYPTION_KEY` ninguém lê. O colaborador desenvolve contra um
banco vazio que ele mesmo popula com dados fictícios.

---

## 7. Cheatsheet

```bash
# Rodar
make dev                 # API no host (hot-reload) — precisa de db/redis/minio no Docker
make worker              # worker arq (outro terminal)
docker compose up -d     # tudo em containers
docker compose down      # derruba os containers (volumes/dados ficam)

# Banco
make migrate             # aplica migrations (alembic upgrade head)
make migrate-create msg="descricao"   # cria nova migration (autogenerate)

# Dados de produção (só o dono)
make sync-from-prod      # puxa banco + fotos da VM pro local

# Qualidade
make test                # pytest (usa banco argus_test isolado)
make lint                # ruff + mypy

# Limpeza Docker
docker system df         # quanto cada coisa ocupa
docker builder prune -f  # limpa cache de build (seguro)
```

> ⚠️ **Nunca** rode `docker system prune -a --volumes` sem pensar: o `--volumes`
> apaga `pgdata`/`minio_data` (seus dados locais).

---

## 8. Pegadinhas rápidas

- **Banco vazio depois do `make dev`?** Normal — só o `make sync-from-prod`
  (dono) traz dados. O colaborador cria os próprios.
- **Primeira subida lenta?** A imagem baixa `torch` + modelos de ML. Depois fica
  em cache.
- **Reconhecimento facial / OCR não funciona no Docker?** A imagem padrão
  (`docker/api.Dockerfile`) instala só as deps base (`pip install "."`).
  InsightFace/EasyOCR são extras `[vision]` — instale `".[vision]"` no host se a
  feature precisar.
- **Conflito de porta?** Você provavelmente está com `make dev` e
  `docker compose up` rodando juntos. Derrube um.

---

## Veja também

- `docs/DEPLOY.md` — como produção roda na VM
- `docs/MEU_GUIA_DE_ESTUDOS.md` — visão geral do sistema para onboarding
- `docs/LGPD.md` — tratamento de dados pessoais
- `docs/disaster-recovery.md` — backup e restauração
