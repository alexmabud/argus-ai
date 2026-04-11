<p align="center">
  <img src="frontend/images/argus-eye.webp" alt="Argus AI" width="120" />
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

**Argus AI** e uma ferramenta de apoio operacional que funciona como **memoria inteligente de equipe**, permitindo registro rapido de abordagens em campo, consulta instantanea de historico, relacionamento automatico entre pessoas, busca por reconhecimento facial e analise geoespacial.

> O nome faz referencia a **Argus Panoptes**, o gigante de cem olhos da mitologia grega — aquele que tudo ve e nada esquece.

---

## Funcionalidades

| Feature | Descricao |
|---------|-----------|
| Cadastro rapido | Registro de abordagem em < 40 segundos (GPS automatico, voz, camera) |
| Entrada por voz | Ditado de observacoes via Web Speech API |
| Captura de foto | Camera direta no navegador com upload para Cloudflare R2 |
| Reconhecimento facial | Busca por similaridade com InsightFace (embedding 512-dim, IVFFlat pgvector) |
| OCR de placas | Leitura automatica de placas veiculares via EasyOCR |
| Geolocalizacao | GPS automatico + geocoding reverso (Nominatim) |
| Analise geoespacial | Busca por raio e mapa de calor (PostGIS + GiST) |
| Relacionamentos automaticos | Vinculo automatico entre pessoas abordadas juntas, com frequencia calculada |
| Vinculos manuais | Criacao manual de relacionamentos entre pessoas com tipo e descricao |
| Consulta unificada | Busca simultanea em pessoas, veiculos e abordagens via unico termo |
| Ocorrencias PDF | Upload de BOs em PDF com extracao de texto (PyMuPDF) e embedding semantico |
| Dashboard analitico | Resumo operacional, pessoas recorrentes, producao diaria/mensal, calendario de atividade |
| Gestao de usuarios | Painel admin para criacao de usuarios com senha unica, pausar/reativar acesso |
| Perfil do usuario | Edicao de nome, apelido, posto/graduacao e foto de perfil |
| Sync offline | Fila IndexedDB sincroniza automaticamente ao reconectar (Dexie.js) |
| Sessoes exclusivas | Apenas uma sessao ativa por usuario (session_id validado no JWT) |
| Multi-tenancy | Cada guarnicao enxerga somente seus proprios dados |
| LGPD compliant | CPF criptografado (Fernet AES-256), audit trail imutavel, soft delete, retencao controlada |

---

## Arquitetura

```
+---------------------------------------------------------+
|                    Frontend (PWA)                        |
|          HTML + Alpine.js + Tailwind + IndexedDB         |
|     Camera . GPS . Voz . OCR . Offline Queue . Sync     |
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
|  |       PDF Processing . Face Embedding               |  |
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
|  + unaccent                                              |
+---------------------------------------------------------+
```

---

## Tech Stack

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, arq, Uvicorn |
| **Banco** | PostgreSQL 16, pgvector, PostGIS, pg_trgm, unaccent |
| **IA / RAG** | SentenceTransformers (`paraphrase-multilingual-MiniLM-L12-v2`), PyMuPDF, Claude API (Anthropic) / Ollama |
| **Visao (opcional)** | InsightFace (buffalo_l, 512-dim), EasyOCR, Pillow, ONNX Runtime |
| **Frontend** | PWA, Alpine.js v3, Tailwind CSS (CDN), Dexie.js (IndexedDB), Web Speech API, Leaflet.js, ApexCharts, Service Worker |
| **Infra** | Docker Compose, Redis, Cloudflare R2 (MinIO local), GitHub Actions CI |
| **Seguranca** | JWT (python-jose), Fernet AES-256 (cryptography), bcrypt (passlib), audit logging, slowapi rate limiting |

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

Isso sobe 5 servicos: **db** (PostgreSQL + pgvector + PostGIS), **redis**, **minio** (S3 local), **api** (FastAPI) e **worker** (arq).

### 3. Migrations e seed

```bash
docker compose exec api python scripts/init_db.py
```

### 4. Acessar

| Servico | URL |
|---------|-----|
| App (PWA) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
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

# Rodar API com hot-reload
make dev

# Rodar worker (outro terminal)
make worker
```

### Comandos (Makefile)

| Comando | Descricao |
|---------|-----------|
| `make dev` | Sobe infra (db, redis, minio) + API com hot-reload |
| `make worker` | Sobe arq worker |
| `make test` | Roda testes com cobertura (`pytest -v --cov=app`) |
| `make lint` | Ruff lint + mypy type check |
| `make format` | Ruff format (auto-formatacao) |
| `make migrate` | Aplica migrations pendentes (ou `init_db.py` se nao houver versoes) |
| `make migrate-create msg="desc"` | Cria nova migration Alembic com autogenerate |
| `make seed` | Popular passagens |
| `make anonimizar` | Anonimizacao LGPD de dados expirados |
| `make anonimizar-dry` | Simulacao da anonimizacao (sem alterar dados) |
| `make docker-up` | Sobe todos os servicos via Docker Compose |
| `make docker-down` | Para e remove containers |
| `make docker-logs` | Acompanha logs da API e worker |
| `make encrypt-key` | Gera nova ENCRYPTION_KEY (Fernet) |
| `make init-db` | Cria tabelas diretamente (sem Alembic) |

---

## Estrutura do Projeto

```
argus-ai/
+-- app/
|   +-- api/v1/                # Routers (endpoints HTTP)
|   |   +-- router.py          # Agregador de rotas
|   |   +-- auth.py            # Login, refresh, perfil, foto de perfil
|   |   +-- pessoas.py         # CRUD pessoas, enderecos, vinculos manuais
|   |   +-- veiculos.py        # CRUD veiculos
|   |   +-- localidades.py     # Autocomplete de bairros, cidades, estados
|   |   +-- abordagens.py      # Registro de abordagens
|   |   +-- fotos.py           # Upload de fotos + busca facial
|   |   +-- consultas.py       # Busca unificada por termo
|   |   +-- ocorrencias.py     # Upload PDF + listagem + busca
|   |   +-- analytics.py       # Dashboard, metricas, calendario
|   |   +-- sync.py            # Sincronizacao offline batch
|   |   +-- admin.py           # Gestao de usuarios (admin)
|   +-- models/                # SQLAlchemy models
|   |   +-- base.py            # Mixins: Timestamp, SoftDelete, MultiTenant
|   |   +-- usuario.py         # Usuario (oficial/membro)
|   |   +-- guarnicao.py       # Guarnicao (raiz multi-tenancy)
|   |   +-- pessoa.py          # Pessoa abordada (CPF criptografado)
|   |   +-- endereco.py        # Endereco com PostGIS point
|   |   +-- veiculo.py         # Veiculo (placa normalizada)
|   |   +-- abordagem.py       # Abordagem (documento raiz)
|   |   +-- foto.py            # Foto (embedding facial 512-dim)
|   |   +-- ocorrencia.py      # Ocorrencia PDF (embedding texto 384-dim)
|   |   +-- relacionamento.py  # Vinculo automatico pessoa-pessoa
|   |   +-- vinculo_manual.py  # Vinculo manual pessoa-pessoa
|   |   +-- audit_log.py       # Trilha de auditoria imutavel
|   +-- schemas/               # Pydantic schemas (request/response)
|   +-- services/              # Logica de negocio (18 servicos, NUNCA importa FastAPI)
|   +-- repositories/          # Acesso a dados com TenantFilter (multi-tenancy)
|   +-- core/                  # Security, crypto, middleware, rate limiting, permissions
|   +-- tasks/                 # Background jobs arq (PDF, face embedding)
|   +-- database/              # Engine async + session factory
|   +-- config.py              # Settings (Pydantic BaseSettings)
|   +-- dependencies.py        # Injecao de dependencias (get_current_user, get_*_service)
|   +-- main.py                # App factory + lifespan
|   +-- worker.py              # arq worker config + registro de tasks
+-- frontend/                  # PWA offline-first
|   +-- index.html             # App shell (Alpine.js)
|   +-- manifest.json          # PWA manifest
|   +-- sw.js                  # Service Worker (cache + offline)
|   +-- css/app.css            # Estilos customizados + Tailwind
|   +-- js/
|   |   +-- app.js             # Alpine.js principal (rotas, estado)
|   |   +-- api.js             # HTTP client (fetch + token)
|   |   +-- auth.js            # Gestao JWT (localStorage)
|   |   +-- db.js              # IndexedDB (Dexie.js)
|   |   +-- sync.js            # Fila offline + sync batch
|   |   +-- pages/
|   |   |   +-- login.js            # Tela de login
|   |   |   +-- abordagem-nova.js   # Cadastro rapido (< 40s)
|   |   |   +-- abordagem-detalhe.js # Detalhe de abordagem
|   |   |   +-- consulta.js         # Busca unificada
|   |   |   +-- pessoa-detalhe.js   # Detalhe de pessoa + relacionamentos
|   |   |   +-- dashboard.js        # Dashboard analitico (ApexCharts)
|   |   |   +-- ocorrencias.js      # Upload e listagem de BOs (PDF)
|   |   |   +-- perfil.js           # Edicao de perfil do usuario
|   |   |   +-- admin-usuarios.js   # Painel admin de usuarios
|   |   +-- components/
|   |       +-- camera.js           # Captura WebRTC
|   |       +-- gps.js              # Geolocation API
|   |       +-- voice.js            # Web Speech API (ditado)
|   |       +-- ocr-placa.js        # OCR de placas (backend EasyOCR)
|   |       +-- autocomplete.js     # Autocomplete fuzzy (datalist)
|   |       +-- offline-indicator.js # Indicador online/offline
|   |       +-- sync-queue.js       # Contador de itens pendentes
+-- tests/                     # pytest async
|   +-- conftest.py            # Fixtures + setup do banco de teste
|   +-- factories.py           # FactoryBoy (model factories)
|   +-- unit/                  # Testes unitarios
|   +-- integration/           # Testes de integracao (endpoints)
|   +-- repositories/          # Testes de repositorios
|   +-- e2e/                   # Testes end-to-end
+-- scripts/
|   +-- init_db.py             # Criacao de tabelas
|   +-- init_extensions.sql    # Extensoes PostgreSQL (pgvector, PostGIS, pg_trgm, unaccent)
|   +-- generate_encryption_key.py  # Gerar chave Fernet
|   +-- reset_usuario.py       # Reset de senha de usuario
|   +-- anonimizar_dados.py    # Anonimizacao LGPD
|   +-- deploy.sh              # Script de deploy
|   +-- setup_oracle.sh        # Setup de VM Oracle
|   +-- backup_rclone.sh       # Backup com rclone
+-- alembic/                   # Migrations
+-- docker/
|   +-- db.Dockerfile          # PostgreSQL + pgvector + PostGIS
+-- .github/workflows/         # CI (lint + testes)
+-- docker-compose.yml
+-- Dockerfile
+-- Makefile
+-- pyproject.toml
```

---

## Endpoints da API

### Autenticacao (`/api/v1/auth`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/login` | Login por matricula + senha, retorna access + refresh tokens |
| POST | `/refresh` | Renovar access token |
| GET | `/me` | Dados do usuario autenticado |
| PUT | `/perfil` | Atualizar perfil (nome, nome de guerra, posto/graduacao) |
| POST | `/perfil/foto` | Upload de foto de perfil para R2 |

### Pessoas (`/api/v1/pessoas`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/` | Cadastrar pessoa (CPF criptografado Fernet + hash SHA-256) |
| GET | `/` | Listar pessoas (busca fuzzy nome/apelido, CPF, paginacao) |
| GET | `/{id}` | Detalhe com enderecos, contagem de abordagens, relacionamentos |
| POST | `/{id}/enderecos` | Adicionar endereco com ponto PostGIS |
| GET | `/{id}/abordagens` | Listar abordagens da pessoa |
| POST | `/{id}/vinculos-manuais` | Criar vinculo manual entre pessoas |
| DELETE | `/{id}/vinculos-manuais/{vinculo_id}` | Remover vinculo manual |

### Veiculos (`/api/v1/veiculos`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/` | Cadastrar veiculo (placa normalizada) |
| GET | `/localidades` | Modelos e cores distintos (autocomplete) |

### Abordagens (`/api/v1/abordagens`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/` | Registrar abordagem com pessoas + veiculos + auto-relacionamento |

### Fotos (`/api/v1/fotos`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/upload` | Upload de foto para R2 (face embedding async via worker) |
| GET | `/buscar/rosto` | Busca por similaridade facial (IVFFlat pgvector) |

### Consultas (`/api/v1/consultas`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/` | Busca unificada (pessoas + veiculos + abordagens por termo) |
| GET | `/localidades` | Bairros, cidades, estados distintos (filtros) |

### Ocorrencias (`/api/v1/ocorrencias`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/` | Upload de BO em PDF (extracao de texto + embedding via worker) |
| GET | `/` | Listar ocorrencias (paginado) |
| GET | `/buscar` | Buscar por nome, numero RAP, data |

### Analytics (`/api/v1/analytics`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/resumo-hoje` | Totais do dia (abordagens, pessoas) |
| GET | `/resumo-mes` | Totais do mes |
| GET | `/resumo-total` | Totais gerais |
| GET | `/pessoas-recorrentes` | Top pessoas mais abordadas (frequencia + ultima data) |
| GET | `/por-dia` | Serie diaria (ultimos 30 dias) |
| GET | `/por-mes` | Serie mensal (ultimos 12 meses) |
| GET | `/dias-com-abordagem` | Dias do mes com atividade (indicadores de calendario) |
| GET | `/pessoas-do-dia` | Pessoas abordadas em data especifica |

### Sync (`/api/v1/sync`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/batch` | Receber lote offline, deduplicar por client_id |

### Admin (`/api/v1/admin`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/usuarios` | Listar usuarios (ativos + pausados) |
| POST | `/usuarios` | Criar usuario com senha unica auto-gerada |

---

## Models

| Model | Descricao | Campos-chave |
|-------|-----------|-------------|
| **Usuario** | Usuario/oficial | matricula, senha_hash, session_id, is_admin, guarnicao_id |
| **Guarnicao** | Guarnicao (raiz multi-tenancy) | nome, unidade, codigo (unique) |
| **Pessoa** | Pessoa abordada | nome, cpf_encrypted (Fernet), cpf_hash (SHA-256), apelido, foto_principal_url |
| **EnderecoPessoa** | Endereco com geo | endereco, bairro, cidade, estado, localizacao (PostGIS POINT) |
| **Veiculo** | Veiculo | placa (unique normalizada), modelo, cor, ano, tipo |
| **Abordagem** | Abordagem (doc raiz) | data_hora, latitude, longitude, localizacao (PostGIS POINT), client_id (sync offline) |
| **Foto** | Foto com face | arquivo_url, embedding_face (Vector(512)), pessoa_id, abordagem_id |
| **Ocorrencia** | BO em PDF | numero_ocorrencia, arquivo_pdf_url, texto_extraido, embedding (Vector(384)) |
| **RelacionamentoPessoa** | Vinculo automatico | pessoa_id_a, pessoa_id_b, frequencia, primeira/ultima_vez |
| **VinculoManual** | Vinculo manual | pessoa_id, pessoa_vinculada_id, tipo, descricao |
| **AuditLog** | Auditoria imutavel | usuario_id, acao, recurso, recurso_id, detalhes (JSON), ip_address |

**Tabelas M:N:** `abordagem_pessoa`, `abordagem_veiculo`

**Mixins:** `TimestampMixin` (criado_em, atualizado_em), `SoftDeleteMixin` (ativo, desativado_em), `MultiTenantMixin` (guarnicao_id)

---

## Variaveis de Ambiente

Copie `.env.example` e configure:

| Variavel | Descricao | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://argus:pass@localhost/argus_db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | Chave JWT | `openssl rand -hex 32` |
| `ENCRYPTION_KEY` | Chave Fernet para CPF (LGPD) | `make encrypt-key` |
| `S3_ENDPOINT` | Storage endpoint (MinIO local / R2 prod) | `http://localhost:9000` |
| `S3_ACCESS_KEY` | Chave de acesso S3 | — |
| `S3_SECRET_KEY` | Chave secreta S3 | — |
| `S3_BUCKET` | Nome do bucket | `argus` |
| `S3_PUBLIC_URL` | URL publica do bucket | — |
| `LLM_PROVIDER` | Provider LLM (`ollama` ou `anthropic`) | `ollama` |
| `ANTHROPIC_API_KEY` | API key da Anthropic (se provider = anthropic) | — |
| `OLLAMA_MODEL` | Modelo Ollama para geracao de texto | `deepseek-r1:8b` |
| `EMBEDDING_MODEL` | Modelo embeddings (SentenceTransformers) | `paraphrase-multilingual-MiniLM-L12-v2` |
| `FACE_SIMILARITY_THRESHOLD` | Limiar de similaridade facial (0.0–1.0) | `0.6` |
| `DATA_RETENTION_DAYS` | Retencao LGPD antes da anonimizacao (dias) | `1825` |
| `RATE_LIMIT_DEFAULT` | Rate limit padrao | `60/minute` |
| `RATE_LIMIT_AUTH` | Rate limit autenticacao | `10/minute` |
| `RATE_LIMIT_HEAVY` | Rate limit operacoes pesadas (IA) | `10/minute` |

Ver `.env.example` para lista completa.

---

## LGPD Compliance

| Mecanismo | Implementacao |
|-----------|---------------|
| **Criptografia de CPF** | Fernet AES-256 (campo criptografado) + SHA-256 (hash para busca) |
| **Audit Trail** | Tabela `audit_logs` imutavel — registra usuario, acao, recurso, IP, user-agent |
| **Soft Delete** | Registros nunca sao removidos fisicamente (`ativo` flag + timestamp) |
| **Retencao controlada** | `DATA_RETENTION_DAYS` (padrao 5 anos) + script `anonimizar_dados.py` |
| **Mascaramento** | CPF exibido apenas com ultimos 2 digitos |
| **Sessoes exclusivas** | `session_id` no JWT impede sessoes simultaneas |
| **Rate Limiting** | slowapi protege contra abuso (60/min padrao, 10/min auth e IA) |

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
| [docs/DEPLOY.md](docs/DEPLOY.md) | Guia de deploy |
| [docs/LGPD.md](docs/LGPD.md) | Compliance LGPD e protecao de dados |
| [docs/PRODUCTION_SECURITY.md](docs/PRODUCTION_SECURITY.md) | Seguranca em producao |
| [docs/DATA_SANITIZATION.md](docs/DATA_SANITIZATION.md) | Sanitizacao de dados para publicacao |
| [docs/MAKING_PUBLIC.md](docs/MAKING_PUBLIC.md) | Guia para tornar o repositorio publico |

---

## Autor

Desenvolvido por **Alex Abud** — AI Automation Engineer & Python Developer

---

<p align="center">
  <sub>Argus Panoptes — o que tudo ve e nada esquece.</sub>
</p>
