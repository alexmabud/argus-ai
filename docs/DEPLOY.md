# Argus AI — Guia de Deploy

## Stack de Produção

| Serviço | Provider | Plano |
|---------|----------|-------|
| Backend | Render ou Railway | Web Service |
| PostgreSQL | Neon (pgvector + PostGIS) | Free/Pro |
| Redis | Upstash | Free/Pay-as-you-go |
| Storage | Cloudflare R2 | Free tier (10GB) |
| CI/CD | GitHub Actions | Free |

## Pré-requisitos

- Conta no GitHub com repositório
- Contas nos providers acima
- Chave de criptografia gerada (`make encrypt-key`)

## 1. PostgreSQL (Neon)

1. Criar projeto no [Neon](https://neon.tech)
2. Habilitar extensões no console SQL:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```
3. Copiar a connection string: `postgresql://user:pass@host/db?sslmode=require`

## 2. Redis (Upstash)

1. Criar database no [Upstash](https://upstash.com)
2. Copiar a URL Redis: `rediss://default:token@host:port`

## 3. Storage (Cloudflare R2)

1. Criar bucket `argus` no [Cloudflare R2](https://dash.cloudflare.com)
2. Criar API token com permissões de leitura/escrita
3. Anotar: Account ID, Access Key, Secret Key, endpoint

## 4. Backend (Render)

1. Conectar repositório GitHub
2. Configurar:
   - **Build Command**: `pip install .`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Configurar variáveis de ambiente (ver abaixo)
4. Criar segundo serviço (Worker):
   - **Start Command**: `arq app.worker.WorkerSettings`
   - Mesmas env vars

## Variáveis de Ambiente (Produção)

```env
# App
DEBUG=false

# Database (Neon)
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require

# Redis (Upstash)
REDIS_URL=rediss://default:token@host:port

# Auth
SECRET_KEY=<gerar-com-openssl-rand-hex-32>
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=30

# LGPD
ENCRYPTION_KEY=<gerar-com-make-encrypt-key>
DATA_RETENTION_DAYS=1825

# Storage (Cloudflare R2)
S3_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY=<r2-access-key>
S3_SECRET_KEY=<r2-secret-key>
S3_BUCKET=argus

# LLM
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=<claude-api-key>

# Embeddings
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2

# CORS
CORS_ORIGINS=["https://seu-dominio.com"]
```

## 5. Migrations

Após deploy, executar migrations:
```bash
# Via Render Shell ou Railway CLI
alembic upgrade head
```

## 6. Seed de Dados

```bash
python scripts/seed_legislacao.py
```

## 7. Anonimização (LGPD)

Configurar cron job para executar periodicamente:
```bash
# Semanal (domingo às 3h)
0 3 * * 0 cd /app && python scripts/anonimizar_dados.py
```

## 8. Monitoramento

- **Render**: Logs nativos + métricas de CPU/memória
- **Neon**: Dashboard de queries + storage
- **Upstash**: Dashboard Redis + alertas
- **Sentry** (opcional): Captura de erros em produção
