<p align="center">
  <img src="docs/assets/argus-logo.png" alt="Argus AI" width="120" />
</p>

<h1 align="center">Argus AI</h1>

<p align="center">
  <strong>Sistema de Apoio Operacional com Inteligencia Artificial</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/pgvector-embeddings-blueviolet" alt="pgvector" />
  <img src="https://img.shields.io/badge/PostGIS-geospatial-green" alt="PostGIS" />
  <img src="https://img.shields.io/badge/PWA-offline--first-orange?logo=pwa&logoColor=white" alt="PWA" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
  <img src="https://img.shields.io/badge/status-portfolio-blue" alt="Status" />
</p>

---

> **Aviso:** Este e um projeto de portfolio/demonstracao tecnica. Nao use em producao sem auditoria de seguranca completa. LGPD-compliant by design.

---

## Sobre

**Argus AI** e uma ferramenta de apoio operacional que funciona como **memoria inteligente de equipe**, permitindo registro rapido de abordagens em campo, consulta instantanea de historico, relacionamento automatico entre pessoas e busca por reconhecimento facial.

> O nome faz referencia a **Argus Panoptes**, o gigante de cem olhos da mitologia grega — aquele que tudo ve e nada esquece.

---

## Funcionalidades

| Feature | Descricao |
|---------|-----------|
| Cadastro rapido | Registro de abordagem em < 40 segundos |
| Entrada por voz | Ditado de observacoes via Web Speech API |
| Captura de foto | Camera direta no navegador com upload para Cloudflare R2 |
| Reconhecimento facial | Busca por similaridade com InsightFace (embedding 512-dim, IVFFlat) |
| Geolocalizacao | GPS automatico + geocoding reverso |
| Analise geoespacial | Busca por raio e mapa de calor (PostGIS + GiST) |
| Relacionamentos | Vinculo automatico entre pessoas abordadas juntas, com frequencia calculada |
| Consulta unificada | Busca simultanea em pessoas, veiculos e abordagens via unico termo |
| Dashboard analitico | Resumo operacional, mapa de calor, horarios de pico, pessoas recorrentes, producao por periodo |
| Sync offline | Fila IndexedDB sincroniza automaticamente ao reconectar |
| LGPD compliant | CPF criptografado (Fernet), audit trail, soft delete, retencao controlada |

---

## Arquitetura

```
+---------------------------------------------------------+
|                    Frontend (PWA)                        |
|          HTML + Alpine.js + Tailwind + IndexedDB         |
|          Camera . GPS . Voz . OCR . Offline Queue        |
+----------------------------+----------------------------+
                             | HTTPS
+----------------------------v----------------------------+
|               Backend (FastAPI - Monolito)               |
|                                                          |
|  +----------+  +----------+  +----------+  +--------+   |
|  | Routers  |->| Services |->|  Repos   |->|   DB   |   |
|  | (API v1) |  | (Logica) |  | (Dados)  |  |        |   |
|  +----------+  +----------+  +----------+  +--------+   |
|                                                          |
|  +----------------------------------------------------+  |
|  |              arq Worker (Background)                |  |
|  |     PDF Processing . Face Embedding . Sync          |  |
|  +----------------------------------------------------+  |
+----------------------------+----------------------------+
                             |
+----------------------------v----------------------------+
|                    Infraestrutura                        |
|                                                          |
|  PostgreSQL 16          Redis           Cloudflare R2    |
|  + pgvector             Cache           Object Storage   |
|  + PostGIS              + arq Queue     (Fotos + PDFs)   |
|  + pg_trgm                                               |
+---------------------------------------------------------+
```

---

## Tech Stack

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, arq, Uvicorn |
| **Banco** | PostgreSQL 16, pgvector, PostGIS, pg_trgm, unaccent |
| **IA / RAG** | SentenceTransformers (`paraphrase-multilingual-MiniLM-L12-v2`), PyMuPDF, Claude API (Anthropic) / Ollama |
| **Visao** | InsightFace (buffalo_l, 512-dim), EasyOCR, Pillow |
| **Frontend** | PWA, Alpine.js, Tailwind CSS (CDN), Dexie.js (IndexedDB), Web Speech API, Service Worker |
| **Infra** | Docker Compose, Redis, Cloudflare R2 (MinIO local), GitHub Actions |
| **Seguranca** | JWT (python-jose), Fernet AES-256 (cryptography), bcrypt, audit logging, slowapi rate limiting |

---

## Quick Start

### Pre-requisitos

- Docker e Docker Compose
- Git

### 1. Clonar e configurar

```bash
git clone https://github.com/SEU_USUARIO/argus-ai.git
cd argus-ai
cp .env.example .env
python scripts/generate_encryption_key.py  # gera ENCRYPTION_KEY
```

### 2. Subir com Docker

```bash
docker compose up -d
```

### 3. Migrations e seed

```bash
docker compose exec api python scripts/init_db.py
docker compose exec api python scripts/seed_legislacao.py
```

### 4. Acessar

| Servico | URL |
|---------|-----|
| App (PWA) | http://localhost:8000 |
| API Docs | http://localhost:8000/api/v1/docs |
| MinIO Console | http://localhost:9001 |

---

## Desenvolvimento Local

```bash
# Criar virtualenv
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -e ".[dev]"

# Subir apenas infra
docker compose up -d db redis minio

# Rodar API
make dev

# Rodar worker (outro terminal)
make worker
```

### Comandos

| Comando | Descricao |
|---------|-----------|
| `make dev` | Sobe infra (db, redis, minio) + API com hot-reload |
| `make worker` | Sobe arq worker em background |
| `make test` | Roda testes com cobertura |
| `make lint` | Ruff lint + mypy type check |
| `make format` | Ruff format (auto-formatacao) |
| `make migrate` | Aplica migrations pendentes (ou executa init-db se nao houver versoes) |
| `make migrate-create msg="desc"` | Cria nova migration Alembic com autogenerate |
| `make seed` | Popular legislacao e passagens |
| `make anonimizar` | Anonimizacao LGPD de dados expirados |
| `make anonimizar-dry` | Simulacao da anonimizacao (sem alterar dados) |
| `make docker-up` | Sobe todos os servicos via Docker Compose |
| `make docker-down` | Para e remove containers |
| `make docker-logs` | Acompanha logs da API e worker |
| `make encrypt-key` | Gera nova ENCRYPTION_KEY (Fernet) |

---

## Estrutura do Projeto

```
argus-ai/
+-- app/
|   +-- api/v1/            # Routers (endpoints HTTP)
|   |   +-- auth.py        # Login, registro, refresh token
|   |   +-- pessoas.py     # CRUD pessoas
|   |   +-- veiculos.py    # CRUD veiculos
|   |   +-- abordagens.py  # CRUD abordagens
|   |   +-- fotos.py       # Upload + busca facial
|   |   +-- relacionamentos.py  # Vinculos entre pessoas
|   |   +-- consultas.py   # Busca unificada por termo
|   |   +-- ocorrencias.py # Upload PDF + vinculacao
|   |   +-- analytics.py   # Dashboard e metricas
|   |   +-- sync.py        # Sincronizacao offline
|   +-- models/            # SQLAlchemy models (mixins: Timestamp, SoftDelete, MultiTenant)
|   +-- schemas/           # Pydantic schemas (request/response)
|   +-- services/          # Logica de negocio (NUNCA importa FastAPI)
|   +-- repositories/      # Acesso a dados (queries)
|   +-- core/              # Security, crypto, middleware, rate limiting
|   +-- tasks/             # Background jobs (arq worker)
|   +-- database/          # Engine, sessions
|   +-- dependencies.py    # Injecao de dependencias
|   +-- main.py            # App factory
|   +-- worker.py          # Worker arq
+-- frontend/              # PWA offline-first (Alpine.js + Tailwind)
|   +-- js/                # Modulos JS (api, auth, db, sync, pages, components)
|   +-- css/               # Estilos
|   +-- sw.js              # Service Worker
|   +-- manifest.json      # PWA manifest
+-- tests/                 # pytest async (unit + integration)
+-- scripts/               # Seeds, anonimizacao, utilitarios
+-- docs/                  # Documentacao e ADRs
+-- alembic/               # Migrations
+-- docker-compose.yml
+-- Makefile
+-- pyproject.toml
```

---

## Variaveis de Ambiente

Copie `.env.example` e configure:

| Variavel | Descricao | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://argus:pass@localhost/argus_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | Chave JWT | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | Chave Fernet para CPF (LGPD) | `make encrypt-key` |
| `S3_ENDPOINT` | Storage endpoint (MinIO local / R2 prod) | `http://localhost:9000` |
| `LLM_PROVIDER` | Provider LLM (`ollama` ou `anthropic`) | `ollama` |
| `ANTHROPIC_API_KEY` | API key da Anthropic (se `LLM_PROVIDER=anthropic`) | — |
| `OLLAMA_MODEL` | Modelo Ollama para geracao de texto | `deepseek-r1:8b` |
| `EMBEDDING_MODEL` | Modelo de embeddings (SentenceTransformers) | `paraphrase-multilingual-MiniLM-L12-v2` |
| `FACE_SIMILARITY_THRESHOLD` | Limiar de similaridade facial (0.0–1.0) | `0.6` |
| `DATA_RETENTION_DAYS` | Retencao LGPD antes da anonimizacao (dias) | `1825` |

Ver `.env.example` para lista completa.

---

## Decisoes Arquiteturais (ADRs)

| ADR | Decisao |
|-----|---------|
| [001](docs/adr/001-offline-first.md) | Arquitetura offline-first com IndexedDB + sync batch |
| [002](docs/adr/002-pgvector-embeddings.md) | pgvector para embeddings vetoriais (texto + face) |
| [003](docs/adr/003-multi-tenancy.md) | Multi-tenancy por guarnicao via coluna filtrada |

---

## Documentacao

| Documento | Descricao |
|-----------|-----------|
| [ARGUS_AI_SPEC.md](ARGUS_AI_SPEC.md) | Especificacao tecnica completa |
| [docs/API.md](docs/API.md) | Referencia de todos os endpoints |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Guia de deploy (Render + Neon + Upstash + R2) |
| [docs/LGPD.md](docs/LGPD.md) | Compliance LGPD e protecao de dados |

---

## Autor

Desenvolvido por **Alex Abud** — AI Automation Engineer & Python Developer

---

<p align="center">
  <sub>Argus Panoptes — o que tudo ve e nada esquece.</sub>
</p>
