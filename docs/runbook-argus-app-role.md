# Runbook — Papel `argus_app` (DML-only) em Produção

> **Objetivo:** provisionar o papel de runtime `argus_app` (só-DML) e migrar a
> aplicação para conectar com ele, mantendo `argus` (dono) exclusivamente para
> migrations. Reduz o blast radius de uma eventual exploração: a aplicação não
> consegue alterar a estrutura do banco (CREATE/DROP/ALTER), apenas ler/escrever.
>
> **Origem:** plano `docs/plans/2026-06-10-role-argus-app-dml.md` (Fase E / item E2).
> **Validado em staging** (container efêmero) antes deste runbook — ver commit
> `test(security): staging valida DEFAULT PRIVILEGES...` na branch
> `security/argus-app-role-2026-06`.

> ⚠️ **Maior risco do plano de segurança.** Uma configuração errada de
> `DEFAULT PRIVILEGES` faz a aplicação **perder acesso ao banco**. O
> provisionamento é **manual e executado pelo operador** (não automatizado no CI).
> Tenha o procedimento de **rollback** (seção 5) à mão antes de começar.

---

## Pré-condições

- A nova `docker-compose.prod.yml` já está na VM (runtime = `argus_app`,
  migrations = `argus` via `MIGRATION_DATABASE_URL`).
- O banco de produção já existe e está populado, dono = `argus`.
- Você tem o `DB_PASSWORD` (senha do dono `argus`) e vai **gerar** uma senha
  forte nova para o `argus_app`:
  ```bash
  openssl rand -hex 24   # exemplo de senha forte para o argus_app
  ```

---

## 1. Pré-deploy — criar o papel (uma vez, como DONO)

O script [`scripts/create_app_role.sql`](../scripts/create_app_role.sql) é
**idempotente** (pode rodar mais de uma vez sem efeito colateral). A senha é
passada por variável psql `app_pwd` **sem aspas no valor** — o script adiciona o
literal com segurança via `:'app_pwd'`.

```bash
cd /opt/argus   # diretório da app na VM (ajuste se necessário)

docker compose -f docker-compose.prod.yml exec -T db \
  psql -U argus -d argus_db -v app_pwd="<SENHA_FORTE_DO_APP>" \
  < scripts/create_app_role.sql
```

> **Por que `\gexec` e não um bloco `DO $$`?** O psql **não** interpola variáveis
> (`:'app_pwd'`) dentro de blocos dollar-quoted (`$$...$$`). O script cria o papel
> condicionalmente via `\gexec` (SQL de nível superior) e depois define a senha com
> `ALTER ROLE argus_app ... PASSWORD :'app_pwd'`. Isso foi descoberto e corrigido no staging.

**O que o script concede ao `argus_app`:**
- `CONNECT` no banco + `USAGE` no schema `public`.
- `SELECT/INSERT/UPDATE/DELETE` em todas as tabelas **existentes** (F1).
- `USAGE, SELECT` em todas as sequences (necessário p/ `INSERT` em colunas serial/identity — F3).
- `EXECUTE` em todas as funções (PostGIS/pgvector — F7).
- **`ALTER DEFAULT PRIVILEGES FOR ROLE argus`** — toda tabela/sequence/função **futura**
  criada por migrations já nasce com DML para o `argus_app` (F2). **É o item que exige staging.**
- `REVOKE CREATE ON SCHEMA public` do `argus_app` e do `PUBLIC` — sem DDL.

Verificação rápida do papel criado:
```bash
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U argus -d argus_db -tAc \
  "SELECT rolname, rolcanlogin, rolsuper FROM pg_roles WHERE rolname='argus_app'"
# esperado: argus_app | t | f
```

---

## 2. Adicionar credenciais ao `.env` da VM

Edite o `.env` (mantenha `chmod 600`):

```dotenv
APP_DB_USER=argus_app
APP_DB_PASSWORD=<SENHA_FORTE_DO_APP>
```

> `DB_USER`/`DB_PASSWORD` (dono `argus`) permanecem inalterados — a compose os
> usa para montar a `MIGRATION_DATABASE_URL` do serviço `api`.

```bash
chmod 600 .env   # confirmar permissão restrita
```

---

## 3. Deploy

Deploy normal (CI faz `git pull` + `docker compose up -d`; **não** use `scp`):

```bash
docker compose -f docker-compose.prod.yml up -d
```

- **Migrations** rodam dentro do `api` como **dono** (`MIGRATION_DATABASE_URL`),
  pois `alembic/env.py` usa `settings.effective_migration_url`.
- **Runtime** (`api` + ambos os `worker`) sobe conectando como `argus_app`.

---

## 4. Verificação pós-deploy (evidência obrigatória)

```bash
# 4.1 App responde
curl -sf http://localhost:80/health && echo "  health OK"

# 4.2 argus_app NÃO consegue DDL (deve recusar)
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U argus_app -d argus_db -c "CREATE TABLE _x(i int);" \
  || echo "OK: DDL bloqueado para argus_app"

# 4.3 argus_app consegue DML (deve funcionar)
docker compose -f docker-compose.prod.yml exec -T db \
  psql -U argus_app -d argus_db -c "SELECT count(*) FROM guarnicoes;"

# 4.4 logging de DDL ativo (E2): após um deploy, DDL fora de janela é alerta
docker compose -f docker-compose.prod.yml logs db | grep -iE "statement: (create|alter|drop)" | tail
```

Confirme nos logs da `api` que não há `permission denied` em queries normais.

---

## 5. Rollback (F10) — se a app não conectar

O papel `argus_app` pode coexistir inerte; reverter o runtime para o dono leva ~30s:

```bash
# No .env da VM, aponte o runtime de volta para o dono:
#   comente/remova APP_DB_USER/APP_DB_PASSWORD OU defina:
#   APP_DB_USER=argus
#   APP_DB_PASSWORD=<DB_PASSWORD do argus>
# (a compose usa ${APP_DB_USER:-argus_app} — definir APP_DB_USER=argus já reverte)

docker compose -f docker-compose.prod.yml up -d api worker worker-2
curl -sf http://localhost:80/health && echo "  rollback OK"
```

> A `MIGRATION_DATABASE_URL` não muda no rollback — migrations seguem como dono.
> Depois investigue a causa (senha errada no `.env`, role sem grant, etc.) e
> repita do passo 1.

---

## 6. Registro da senha e rotação

1. **Guarde a senha do `argus_app`** no Cryptomator do operador (mesmo cofre das
   demais senhas mestras de produção).
2. **Rotação:** regenere a senha e rode novamente o `create_app_role.sql` (idempotente):
   ```bash
   docker compose -f docker-compose.prod.yml exec -T db \
     psql -U argus -d argus_db -v app_pwd="<NOVA_SENHA>" \
     < scripts/create_app_role.sql
   ```
   Atualize `APP_DB_PASSWORD` no `.env` e `docker compose up -d api worker worker-2`.
   Registre a credencial em [`docs/secret-rotation.md`](secret-rotation.md)
   (criar a seção do `argus_app` lá, caso ainda não exista).

---

## Resumo de modos de falha cobertos

| Item | Mitigação no runbook |
|---|---|
| F1 | Passo 1 — GRANT DML em tabelas existentes |
| F2 | Passo 1 — `ALTER DEFAULT PRIVILEGES` (validado em staging) |
| F3 | Passo 1 — GRANT em sequences |
| F4 | Passo 3 — migrations como dono via `MIGRATION_DATABASE_URL` |
| F7 | Passo 1 — GRANT EXECUTE em funções (PostGIS/pgvector) |
| F8 | Passo 1 — script idempotente, rodado uma vez como dono |
| F10 | Passo 5 — rollback em ~30s revertendo o `.env` |
