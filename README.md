<p align="center">
  <img src="docs/assets/argus-logo.png" alt="Argus AI" width="120" />
</p>

<h1 align="center">Argus AI</h1>

<p align="center">
  <strong>Sistema de Apoio Operacional com Inteligência Artificial</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/pgvector-embeddings-blueviolet" alt="pgvector" />
  <img src="https://img.shields.io/badge/PostGIS-geospatial-green" alt="PostGIS" />
  <img src="https://img.shields.io/badge/PWA-offline--first-orange?logo=pwa&logoColor=white" alt="PWA" />
  <img src="https://img.shields.io/badge/license-private-red" alt="License" />
</p>

---

## Sobre

**Argus AI** é uma ferramenta de apoio operacional que funciona como **memória inteligente de equipe**, permitindo registro rápido de abordagens em campo, consulta instantânea de histórico, relacionamento automático entre pessoas, busca por reconhecimento facial, OCR de placas veiculares e geração de relatórios assistida por IA (RAG).

> O nome faz referência a **Argus Panoptes**, o gigante de cem olhos da mitologia grega — aquele que tudo vê e nada esquece.

O sistema **não substitui ferramentas oficiais** — é uma camada de apoio para organização, consulta e produtividade operacional.

---

## Funcionalidades

- ⚡ **Cadastro rápido** — Registro de abordagem em menos de 40 segundos
- 🎤 **Entrada por voz** — Ditado de observações via Web Speech API
- 📷 **Captura de foto** — Câmera direta sem file picker
- 🔍 **Reconhecimento facial** — Busca por similaridade com InsightFace
- 🚗 **OCR de placas** — Extrai placa de foto automaticamente
- 📍 **Geolocalização automática** — GPS + geocoding reverso
- 🗺️ **Análise geoespacial** — Busca por raio e mapa de calor (PostGIS)
- 🔗 **Relacionamentos automáticos** — Vínculo materializado entre pessoas abordadas juntas
- 📄 **RAG para relatórios** — Geração assistida por IA com base em ocorrências anteriores e legislação
- ⚖️ **Consulta de legislação** — Busca semântica no Código Penal e leis extravagantes
- 📊 **Dashboard analítico** — Métricas, horários de pico, pessoas recorrentes
- 📶 **Offline-first** — Funciona sem internet, sincroniza automaticamente
- 🔒 **LGPD compliant** — Criptografia, audit trail, soft delete, retenção controlada

---

## Demonstração

<!-- TODO: Adicionar GIF/vídeo do fluxo de cadastro em campo -->

<p align="center">
  <em>🎬 Demo em breve</em>
</p>

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (PWA)                       │
│          HTML + Alpine.js + Tailwind + IndexedDB        │
│          Câmera · GPS · Voz · OCR · Offline Queue       │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────┐
│               Backend (FastAPI - Monolito)              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐   │
│  │ Routers  │→ │ Services │→ │  Repos   │→ │   DB   │   │
│  │ (API v1) │  │ (Lógica) │  │ (Dados)  │  │        │   │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              arq Worker (Background)             │   │
│  │     PDF Processing · Face Embedding · Sync       │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    Infraestrutura                       │
│                                                         │
│  PostgreSQL 16          Redis           Cloudflare R2   │
│  + pgvector             Cache           Object Storage  │
│  + PostGIS              + arq Queue     (Fotos + PDFs)  │
│  + pg_trgm                                              │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Camada | Tecnologias |
|---|---|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| **Banco** | PostgreSQL 16, pgvector, PostGIS, pg_trgm |
| **IA / RAG** | SentenceTransformers (multilingual), PyMuPDF, Claude API / Ollama |
| **Visão** | InsightFace, EasyOCR, Pillow |
| **Frontend** | PWA, Alpine.js, Tailwind CSS, Dexie.js (IndexedDB) |
| **Infra** | Docker, Redis, Cloudflare R2, GitHub Actions |
| **Segurança** | JWT, Fernet (AES), bcrypt, audit logging, rate limiting |

---

## Pré-requisitos

- Python 3.11+
- Docker e Docker Compose
- Git

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/SEU_USUARIO/argus-ai.git
cd argus-ai
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
python scripts/generate_encryption_key.py  # gera ENCRYPTION_KEY
# Editar .env com suas configurações
```

### 3. Subir com Docker

```bash
docker compose up -d
```

### 4. Rodar migrations e seed

```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_legislacao.py
docker compose exec api python scripts/seed_passagens.py
```

### 5. Acessar

```
App:  http://localhost:8000
API:  http://localhost:8000/api/v1/docs
```

---

## Desenvolvimento

```bash
# Ambiente local (sem Docker para o backend)
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Subir dependências
docker compose up -d db redis minio

# Rodar API
make dev

# Rodar worker (em outro terminal)
make worker

# Testes
make test

# Lint + type check
make lint
```

---

## Estrutura do Projeto

```
argus-ai/
├── app/
│   ├── api/v1/          # Routers (endpoints HTTP)
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Lógica de negócio
│   ├── repositories/    # Acesso a dados
│   ├── core/            # Security, crypto, middleware
│   ├── tasks/           # Background jobs (arq)
│   └── database/        # Engine, sessions
├── frontend/            # PWA (HTML + JS)
├── tests/               # pytest (unit + integration + e2e)
├── scripts/             # Seeds e utilitários
├── docs/                # Documentação e ADRs
├── alembic/             # Migrations
├── CLAUDE.md            # Contexto para Claude Code
├── ARGUS_AI_SPEC.md     # Especificação técnica completa
└── docker-compose.yml
```

---

## Decisões Arquiteturais

As decisões técnicas do projeto estão documentadas em ADRs (Architecture Decision Records) na pasta `docs/adr/`:

| ADR | Decisão |
|---|---|
| 001 | Monolito modular (vs microserviços) |
| 002 | pgvector no PostgreSQL (vs FAISS externo) |
| 003 | PWA (vs React Native) |
| 004 | Embedding multilíngue para PT-BR |
| 005 | Offline-first com IndexedDB + sync |
| 006 | Multi-tenancy por guarnição |

---

## Roadmap

- [x] Especificação técnica e arquitetura
- [ ] **Fase 1** — Fundação (models, auth, migrations)
- [ ] **Fase 2** — Core operacional (CRUD, relacionamentos, geoespacial)
- [ ] **Fase 3** — RAG (embeddings, busca semântica, geração de relatório)
- [ ] **Fase 4** — Visão computacional (face recognition, OCR)
- [ ] **Fase 5** — Frontend PWA (offline, voz, câmera, dashboard)
- [ ] **Fase 6** — Deploy e polimento

---

## Documentação

- [`ARGUS_AI_SPEC.md`](./ARGUS_AI_SPEC.md) — Especificação técnica completa
- [`docs/API.md`](./docs/API.md) — Documentação da API (em breve)
- [`docs/DEPLOY.md`](./docs/DEPLOY.md) — Guia de deploy (em breve)
- [`docs/LGPD.md`](./docs/LGPD.md) — Política de dados (em breve)

---

## Autor

Desenvolvido por **Abud** — AI Automation Engineer & Python Developer

---

<p align="center">
  <sub>Argus Panoptes — o que tudo vê e nada esquece. 👁️</sub>
</p>