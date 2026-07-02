# Argus AI — Guia de Deploy

## Stack de Produção

| Serviço | Como roda hoje |
|---------|----------------|
| Hospedagem | VM Oracle Cloud (Always Free), self-hosted via `docker-compose.prod.yml` |
| Backend (API + worker) | Containers FastAPI (gunicorn/uvicorn) + arq |
| PostgreSQL 16 | Container (pgvector + PostGIS + pg_trgm + unaccent) |
| Redis | Container (cache + fila do arq) |
| Storage | MinIO em container (dados em `/mnt/fotos`) — trocável por R2/AWS S3 via `S3_ENDPOINT` |
| Reverse proxy / HTTPS | Caddy (`docker/Caddyfile`) |
| Monitoramento | Prometheus + Grafana + relatório Telegram |
| Backup | Dump diário + replicação offsite (Oracle Object Storage + Google Drive) |
| CI/CD | GitHub Actions |

## Pré-requisitos

- VM provisionada (ver `scripts/setup_oracle.sh`) com Docker + Docker Compose
- Repositório clonado na VM
- Chave de criptografia gerada (`make encrypt-key`)

## 1. PostgreSQL (container)

O Postgres roda no container `db` (imagem com pgvector + PostGIS — ver `docker/db.Dockerfile`).
As extensões são criadas na primeira subida (`scripts/init_extensions.sql`):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```
As connection strings ficam em `DATABASE_URL` (runtime, papel só-DML `argus_app`) e
`MIGRATION_DATABASE_URL` (migrations, dono `argus`) no `.env`.

## 2. Redis (container)

Redis roda no container `redis` (cache + fila do arq worker). A URL fica em `REDIS_URL`
(ex.: `redis://redis:6379` dentro da rede Docker).

## 3. Storage (MinIO local — S3-compatible)

O Argus armazena fotos e mídias em um bucket S3-compatible. Em produção
hoje rodamos **MinIO** num container Docker dentro da VM (dados em
`/mnt/fotos`). A aplicação é agnóstica: basta trocar `S3_ENDPOINT`,
`S3_ACCESS_KEY` e `S3_SECRET_KEY` para apontar para qualquer provider
S3-compatible (Cloudflare R2, AWS S3, Backblaze B2, etc.).

Para o setup atual (MinIO em container):

1. O serviço `minio` está definido no `docker-compose.prod.yml`.
2. Bucket `argus` é criado automaticamente pelo serviço `minio-init`
   na primeira subida.
3. As credenciais são definidas via `MINIO_ROOT_USER` e `MINIO_ROOT_PASSWORD`
   no `.env`.

### Cache de watermark (prefixo `wm/`)

O sistema de watermark rastreável (camada 2) armazena variantes pré-marcadas sob o
prefixo versionado `wm/<versão>/` (ex.: `wm/v2/`) no mesmo bucket. Um bump da versão
em `WM_PREFIX` invalida o cache (regenera as marcas no próximo acesso). Para evitar
crescimento indefinido, configure a regra de expiração após o primeiro deploy:

```bash
# No servidor, dentro do container MinIO ou via mc configurado:
docker exec -it argus_minio_1 mc ilm rule add argus/argus \
  --prefix "wm/" --expire-days 14
```

> **Por quê 14 dias?** Sessões longas de patrulha dificilmente passam de 2 semanas.
> Após 14 dias, o cache é regenerado automaticamente no próximo acesso.
> Se quiser evitar a regra, o prefixo `wm/` cresce ~1 variante por (usuário × foto)
> — geralmente inofensivo, mas boa prática limpar.

Para migrar para Cloudflare R2 (caso queira no futuro):

1. Criar bucket `argus` no [Cloudflare R2](https://dash.cloudflare.com)
2. Gerar API token com permissões de leitura/escrita
3. Trocar no `.env`:
   - `S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com`
   - `S3_ACCESS_KEY`, `S3_SECRET_KEY` com as credenciais R2
4. Reiniciar a stack — código existente já funciona sem mudanças.

## 4. Backend (API + worker em containers)

A API (gunicorn/uvicorn) e o worker (arq) sobem como serviços no `docker-compose.prod.yml`,
atrás do Caddy (HTTPS automático). O deploy roda via `scripts/deploy.sh`; a esteira de CI
faz `git pull` na VM — **nunca** use `scp` (deixa a árvore suja e quebra o deploy).

```bash
docker compose -f docker-compose.prod.yml up -d
```

### Imagem única (api/worker/worker-2)

Os serviços `api`, `worker` e `worker-2` rodam o **mesmo código** (`Dockerfile.prod`).
Só `api` tem `build:` no compose — ela produz `image: argus-ai-app:latest`, e
`worker`/`worker-2` apenas referenciam essa `image:` (sem `build:` próprio).
Isso builda a imagem **uma única vez** em vez de três vezes em paralelo.

Isso importa porque a VM de produção (Oracle Free Tier) tem **disco pequeno
(~49 GB)**. `torch`/`easyocr`/`insightface` deixam a imagem pesada; buildar 3
cópias idênticas ao mesmo tempo já estourou o disco em produção. O
`Dockerfile.prod` também remove as libs CUDA/NVIDIA (`nvidia-*`, `triton`) do
venv após a instalação — o `requirements.lock` as fixa porque foi gerado
resolvendo o torch do PyPI, mas a wheel **CPU** do torch não as usa; numa VM
sem GPU são ~5 GB de peso morto. Ao alterar `Dockerfile.prod` ou
`requirements.lock`, teste o build direto na VM antes de confiar no deploy
automático — o CI não builda a imagem Docker, só valida testes/lint.

Se um deploy falhar por disco cheio, o `docker compose down` do início do
workflow já derrubou os containers antes do build falhar — **a produção fica
fora do ar até o problema ser corrigido**. Ver `docs/disaster-recovery.md`,
Cenário F.

## Variáveis de Ambiente (Produção)

```env
# App
DEBUG=false

# Database — runtime conecta como papel só-DML (argus_app); migrations como dono (argus).
# Provisionar o papel argus_app antes do 1º deploy: ver docs/runbook-argus-app-role.md
DATABASE_URL=postgresql://argus_app:pass@host/db?sslmode=require
MIGRATION_DATABASE_URL=postgresql://argus:pass@host/db?sslmode=require
APP_DB_USER=argus_app
APP_DB_PASSWORD=<senha-forte>

# Redis (container)
REDIS_URL=redis://redis:6379

# Auth
SECRET_KEY=<gerar-com-openssl-rand-hex-32>
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=30

# LGPD
ENCRYPTION_KEY=<gerar-com-make-encrypt-key>
DATA_RETENTION_DAYS=1825

# Storage (MinIO em prod hoje; trocavel por R2/AWS S3 mudando estas vars)
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=<minio-access-key>
S3_SECRET_KEY=<minio-secret-key>
S3_BUCKET=argus
# Opcional: URL pública para o browser quando S3_ENDPOINT for hostname interno
S3_PUBLIC_URL=https://seu-dominio.com

# LLM (RESERVADO — sem uso; não há serviço LLM no código)
# LLM_PROVIDER=ollama
# ANTHROPIC_API_KEY=

# Embeddings
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# CORS
CORS_ORIGINS=["https://seu-dominio.com"]
```

## 5. Migrations

Após deploy, executar migrations (rodam como dono do banco, via `MIGRATION_DATABASE_URL`):
```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### 5.1. Bootstrap do super-admin (primeira subida)

Há **um único super-admin (dono)**: o único que promove/rebaixa admins e exclui
usuários. Os demais admins são delegados, com permissões granulares definidas
pelo dono na página "Gerenciar admins". A migration adiciona as colunas com
default `false` (ninguém vira super-admin sozinho).

Logo após o `alembic upgrade head`, marque o dono pela matrícula (idempotente,
não-destrutivo, seguro em produção):
```bash
python -m scripts.definir_super_admin --matricula <matricula_do_dono>
```
Admins já existentes (`is_admin=True`) seguem como delegados sem nenhum toggle
ligado — o dono re-habilita o que cada um pode fazer pela tela.

## 6. Seed de Dados

Não há dados de seed no projeto (legislação/passagens foram descontinuadas). O alvo
`make seed` é apenas um placeholder.

## 7. Anonimização (LGPD)

Configurar cron job para executar periodicamente:
```bash
# Semanal (domingo às 3h)
0 3 * * 0 cd /app && python scripts/anonimizar_dados.py
```

## 8. Monitoramento

Stack self-hosted (detalhes em [monitoring/MANUAL_MONITORAMENTO.md](../monitoring/MANUAL_MONITORAMENTO.md)):

- **Prometheus**: coleta de métricas (node, postgres e redis exporters)
- **Grafana**: dashboards + alertas (ex.: backup falho há mais de 26h)
- **Telegram**: relatório diário + alertas críticos
- **`make monitoring`**: sobe a stack de monitoramento (`docker-compose.monitoring.yml`)
