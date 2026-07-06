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
| Captura de foto | Camera direta no navegador com upload para MinIO (storage S3-compatible) |
| Reconhecimento facial | Busca por similaridade com InsightFace (embedding 512-dim, IVFFlat pgvector) |
| OCR de placas | Leitura automatica de placas veiculares via EasyOCR |
| Geolocalizacao | GPS automatico + geocoding reverso (Nominatim) |
| Analise geoespacial | Busca por raio e mapa de calor (PostGIS + GiST) |
| Relacionamentos automaticos | Vinculo automatico entre pessoas abordadas juntas, com frequencia calculada |
| Vinculos manuais | Criacao manual de relacionamentos entre pessoas com tipo e descricao |
| Observacoes de pessoa | Anotacoes operacionais livres por pessoa com historico cronologico |
| Consulta unificada | Busca simultanea em pessoas, veiculos e abordagens via unico termo |
| Ocorrencias (BOs em PDF) | Upload, extracao de texto (PyMuPDF) e busca por nome/RAP/data. Um embedding (pgvector 384-dim) e gerado e armazenado como base para busca semantica futura (ainda nao exposta em endpoint) |
| Dashboard analitico | Resumo operacional, pessoas recorrentes, producao diaria/mensal, calendario de atividade |
| Gestao de usuarios | Painel admin para criacao, pausa, reativacao e exclusao de usuarios; geracao de senha unica |
| Gestao de BPMs e equipes | Criacao de batalhoes e equipes com controle de isolamento de dados |
| Admins e permissoes granulares | Super-admin define quem e admin e quais permissoes cada um tem (ex.: gerir equipes) |
| 2FA (TOTP) | Autenticacao de dois fatores opcional via app autenticador (pyotp) |
| Perfil do usuario | Edicao de nome, apelido, posto/graduacao e foto de perfil |
| Sync offline | Fila IndexedDB sincroniza automaticamente ao reconectar (Dexie.js) |
| Sessoes exclusivas | Apenas uma sessao ativa por usuario (session_id validado no JWT) |
| Multi-tenancy | Cada equipe/guarnicao enxerga somente seus proprios dados |
| LGPD compliant | CPF criptografado (Fernet AES-256), audit trail imutavel, soft delete, retencao controlada |

---

## Arquitetura

```
+---------------------------------------------------------+
|                    Frontend (PWA)                       |
|          HTML + Alpine.js + Tailwind + IndexedDB        |
|     Camera . GPS . Voz . OCR . Offline Queue . Sync     |
+----------------------------+----------------------------+
                             | HTTPS
+----------------------------v----------------------------+
|               Backend (FastAPI - Monolito)              |
|                                                         |
|  +----------+  +----------+  +----------+  +--------+   |
|  | Routers  |->| Services |->|  Repos   |->|   DB   |   |
|  | (API v1) |  | (Logica) |  | (Dados)  |  |        |   |
|  +----------+  +----------+  +----------+  +--------+   |
|                                                         |
|  +---------------------------------------------------+  |
|  |              arq Worker (Background)              |  |
|  |       PDF Processing . Face Embedding             |  |
|  +---------------------------------------------------+  |
+----------------------------+----------------------------+
                             |
+----------------------------v----------------------------+
|                    Infraestrutura                       |
|                                                         |
|  PostgreSQL 16          Redis           MinIO           |
|  + pgvector             Cache           S3-compatible   |
|  + PostGIS              + arq Queue     (Fotos + PDFs)  |
|  + pg_trgm                                              |
|  + unaccent                                             |
+---------------------------------------------------------+
```

---

## Tech Stack

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, arq, Uvicorn |
| **Banco** | PostgreSQL 16, pgvector, PostGIS, pg_trgm, unaccent |
| **IA / Busca semantica** | SentenceTransformers (`paraphrase-multilingual-MiniLM-L12-v2`), PyMuPDF (extracao de texto de PDF) |
| **Visao (opcional)** | InsightFace (buffalo_l, 512-dim), EasyOCR, Pillow, ONNX Runtime |
| **Frontend** | PWA, Alpine.js v3, Tailwind CSS (CDN), Dexie.js (IndexedDB), Web Speech API, Leaflet.js, ApexCharts, Service Worker |
| **Infra** | Docker Compose, Redis, MinIO (storage S3-compatible), GitHub Actions CI |
| **Seguranca** | JWT (PyJWT), Fernet AES-256 (cryptography), bcrypt, TOTP 2FA (pyotp), audit logging, slowapi rate limiting |

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

### 3. Migrations

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
| `make migrate` | Aplica migrations pendentes |
| `make migrate-create msg="desc"` | Cria nova migration Alembic com autogenerate |
| `make seed` | Placeholder — nao ha dados de seed no projeto hoje (alvo vestigial) |
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
|   |   +-- auth.py            # Login, logout, refresh, perfil, foto de perfil
|   |   +-- pessoas.py         # CRUD pessoas, enderecos, vinculos manuais, observacoes
|   |   +-- veiculos.py        # CRUD veiculos
|   |   +-- localidades.py     # Autocomplete de bairros, cidades, estados
|   |   +-- abordagens.py      # Registro e listagem de abordagens
|   |   +-- fotos.py           # Upload de fotos/midias, busca facial, OCR de placa
|   |   +-- consultas.py       # Busca unificada por termo
|   |   +-- ocorrencias.py     # Upload PDF + listagem + busca
|   |   +-- analytics.py       # Dashboard, metricas, calendario
|   |   +-- sync.py            # Sincronizacao offline batch
|   |   +-- admin.py           # Gestao de usuarios, BPMs e equipes (admin)
|   +-- models/                # SQLAlchemy models
|   |   +-- base.py            # Mixins: Timestamp, SoftDelete, MultiTenant
|   |   +-- usuario.py         # Usuario (oficial/membro)
|   |   +-- guarnicao.py       # Equipe/guarnicao (multi-tenancy)
|   |   +-- bpm.py             # Batalhao (agrupador de equipes, com isolamento)
|   |   +-- pessoa.py          # Pessoa abordada (CPF criptografado)
|   |   +-- pessoa_observacao.py # Observacoes livres por pessoa
|   |   +-- endereco.py        # Endereco com PostGIS point
|   |   +-- veiculo.py         # Veiculo (placa normalizada)
|   |   +-- localidade.py      # Hierarquia estado/cidade/bairro
|   |   +-- abordagem.py       # Abordagem (documento raiz)
|   |   +-- foto.py            # Foto/midia (embedding facial 512-dim)
|   |   +-- ocorrencia.py      # Ocorrencia PDF (embedding texto 384-dim)
|   |   +-- relacionamento.py  # Vinculo automatico pessoa-pessoa
|   |   +-- vinculo_manual.py  # Vinculo manual pessoa-pessoa
|   |   +-- audit_log.py       # Trilha de auditoria imutavel
|   +-- schemas/               # Pydantic schemas (request/response)
|   +-- services/              # Logica de negocio (22 servicos, NUNCA importa FastAPI)
|   +-- repositories/          # Acesso a dados com TenantFilter (multi-tenancy)
|   +-- core/                  # Security, crypto, middleware, rate limiting, permissions,
|   |                          #   upload_validation, auth_cookie, logging_config
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
|   |   |   +-- pessoa-detalhe.js   # Detalhe de pessoa + relacionamentos + observacoes
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
|   +-- backfill_thumbnails.py # Reprocessar thumbnails de fotos existentes
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
| POST | `/logout` | Invalida a sessao atual (session_id) |
| GET | `/me` | Dados do usuario autenticado |
| PUT | `/perfil` | Atualizar perfil (nome, nome de guerra, posto/graduacao) |
| POST | `/perfil/foto` | Upload de foto de perfil para o storage S3-compatible |

### Pessoas (`/api/v1/pessoas`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/` | Cadastrar pessoa (CPF criptografado Fernet + hash SHA-256) |
| GET | `/` | Listar pessoas (busca fuzzy nome/apelido, CPF, paginacao) |
| GET | `/{id}` | Detalhe com enderecos, contagem de abordagens, relacionamentos |
| PATCH | `/{id}` | Atualizar dados de uma pessoa |
| DELETE | `/{id}` | Soft delete de pessoa |
| POST | `/{id}/enderecos` | Adicionar endereco com ponto PostGIS |
| PATCH | `/{id}/enderecos/{end_id}` | Atualizar endereco |
| GET | `/{id}/abordagens` | Listar abordagens da pessoa |
| POST | `/{id}/vinculos-manuais` | Criar vinculo manual entre pessoas |
| DELETE | `/{id}/vinculos-manuais/{vinculo_id}` | Remover vinculo manual |
| POST | `/{id}/veiculos/{veiculo_id}` | Vincular veiculo direto a pessoa (fora do contexto de abordagem, com reativacao se ja existiu) |
| DELETE | `/{id}/veiculos/{veiculo_id}` | Remover vinculo direto pessoa-veiculo (soft delete do vinculo, nao do veiculo) |
| GET | `/{id}/veiculos` | Listar veiculos da pessoa (unificado: vinculo direto + derivados de abordagem) |
| GET | `/{id}/observacoes` | Listar observacoes operacionais da pessoa |
| POST | `/{id}/observacoes` | Criar observacao |
| PATCH | `/{id}/observacoes/{obs_id}` | Atualizar observacao |
| DELETE | `/{id}/observacoes/{obs_id}` | Soft delete de observacao |

### Veiculos (`/api/v1/veiculos`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/` | Listar veiculos (filtros por placa/modelo/cor) |
| POST | `/` | Cadastrar veiculo (placa normalizada) |
| PUT | `/{id}` | Atualizar veiculo (modelo/cor/ano/tipo/observacoes; placa e imutavel) |
| GET | `/localidades` | Modelos e cores distintos (autocomplete) |

### Abordagens (`/api/v1/abordagens`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/` | Registrar abordagem com pessoas + veiculos + auto-relacionamento |
| GET | `/` | Listar abordagens (paginado, com filtros) |
| GET | `/{id}` | Detalhe de abordagem com pessoas, veiculos e fotos |

### Fotos e Midias (`/api/v1/fotos`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/upload` | Upload de foto de pessoa para o storage S3-compatible (tipos: rosto, evidencia, veiculo, etc — face embedding async via worker so para tipo=rosto) |
| POST | `/midias` | Upload de midia (foto/video) vinculada a abordagem |
| GET | `/pessoa/{pessoa_id}` | Listar fotos de uma pessoa |
| GET | `/abordagem/{abordagem_id}` | Listar midias de uma abordagem |
| POST | `/buscar-rosto` | Busca por similaridade facial (IVFFlat pgvector) |
| POST | `/ocr-placa` | Extrair numero de placa via EasyOCR |
| GET | `/{foto_id}/download` | Download/redirect de midia via URL assinada (S3 presigned URL) |
| DELETE | `/{foto_id}` | Soft delete de foto (corrige fotos categorizadas incorretamente) |

### Consultas (`/api/v1/consultas`)

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/` | Busca unificada (pessoas + veiculos + abordagens por termo) |
| GET | `/pessoas-por-veiculo` | Pessoas vinculadas a veiculos (placa, modelo ou cor) |
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
| GET | `/abordagens-do-dia` | Total de abordagens em data especifica |
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
| PATCH | `/usuarios/{id}/pausar` | Pausar ou reativar acesso de usuario |
| POST | `/usuarios/{id}/gerar-senha` | Gerar nova senha unica para usuario |
| DELETE | `/usuarios/{id}` | Excluir usuario (soft delete) |
| PATCH | `/usuarios/{id}/equipe` | Transferir usuario para outra equipe |
| GET | `/admins` | Listar admins e suas permissoes granulares |
| PUT | `/usuarios/{id}/admin` | Definir/remover admin e permissoes (controlado por super-admin) |
| GET | `/bpms` | Listar batalhoes (BPMs) |
| POST | `/bpms` | Criar novo BPM |
| PATCH | `/bpms/{id}/toggle-isolamento` | Ativar/desativar isolamento de dados por BPM |
| GET | `/equipes` | Listar equipes/guarnicoes |
| POST | `/equipes` | Criar nova equipe |
| PATCH | `/equipes/{id}/toggle-isolamento` | Ativar/desativar isolamento de dados por equipe |
| POST | `/2fa/setup` | Iniciar configuracao de 2FA (TOTP) |
| POST | `/2fa/verify` | Confirmar e ativar 2FA (TOTP) |

---

## Models

| Model | Descricao | Campos-chave |
|-------|-----------|-------------|
| **Usuario** | Usuario/oficial | matricula, senha_hash, session_id, is_admin, guarnicao_id |
| **Guarnicao** | Equipe operacional (raiz multi-tenancy) | nome, unidade, codigo (unique), bpm_id |
| **Bpm** | Batalhao de Policia Militar (agrupa equipes) | nome (unique), isolamento_abordagens |
| **Pessoa** | Pessoa abordada | nome, cpf_encrypted (Fernet), cpf_hash (SHA-256), apelido, foto_principal_url |
| **PessoaObservacao** | Anotacoes operacionais sobre uma pessoa | pessoa_id, texto, guarnicao_id |
| **EnderecoPessoa** | Endereco com geo | endereco, bairro, cidade, estado, localizacao (PostGIS POINT) |
| **Localidade** | Hierarquia geografica (estado/cidade/bairro) | nome, nome_exibicao, tipo, sigla, parent_id |
| **Veiculo** | Veiculo | placa (unique normalizada), modelo, cor, ano, tipo |
| **Abordagem** | Abordagem (doc raiz) | data_hora, latitude, longitude, localizacao (PostGIS POINT), client_id (sync offline) |
| **Foto** | Foto/midia com face | arquivo_url, embedding_face (Vector(512)), pessoa_id, abordagem_id |
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
| `DATABASE_URL` | Conexao do runtime (em prod, papel so-DML `argus_app`) | `postgresql+asyncpg://argus_app:pass@localhost/argus_db` |
| `MIGRATION_DATABASE_URL` | Conexao das migrations (dono `argus`). Opcional em dev (cai para `DATABASE_URL`) | `postgresql://argus:pass@localhost/argus_db` |
| `APP_DB_USER` / `APP_DB_PASSWORD` | Usuario/senha do papel `argus_app` (usados pela compose de prod) | `argus_app` / `<senha-forte>` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | Chave JWT | `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiracao do access token | `480` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Expiracao do refresh token | `30` |
| `ENCRYPTION_KEY` | Chave Fernet para CPF (LGPD) | `make encrypt-key` |
| `S3_ENDPOINT` | Endpoint S3-compatible (MinIO em dev e em prod hoje; trocavel para R2/AWS S3) | `http://localhost:9000` |
| `S3_ACCESS_KEY` | Chave de acesso S3 | — |
| `S3_SECRET_KEY` | Chave secreta S3 | — |
| `S3_BUCKET` | Nome do bucket | `argus` |
| `LLM_PROVIDER` | Reservado — presente no `.env.example`, sem servico LLM ativo hoje | `ollama` |
| `ANTHROPIC_API_KEY` | Reservado — sem uso atual | — |
| `OLLAMA_BASE_URL` | Reservado — sem uso atual | `http://localhost:11434` |
| `OLLAMA_MODEL` | Reservado — sem uso atual | `deepseek-r1:8b` |
| `EMBEDDING_MODEL` | Modelo embeddings (SentenceTransformers) | `paraphrase-multilingual-MiniLM-L12-v2` |
| `EMBEDDING_DIMENSIONS` | Dimensoes do embedding de texto | `384` |
| `EMBEDDING_CACHE_TTL` | TTL do cache Redis para embeddings (s) | `3600` |
| `FACE_SIMILARITY_THRESHOLD` | Limiar de similaridade facial (0.0-1.0) | `0.6` |
| `GEOCODING_PROVIDER` | Provider de geocoding (`nominatim` ou `google`) | `nominatim` |
| `GOOGLE_MAPS_API_KEY` | API key do Google Maps (se provider = google) | — |
| `CORS_ORIGINS` | Origens permitidas (JSON array) | `["https://seu-dominio.com"]` |
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
| **Rate Limiting** | slowapi protege contra abuso (60/min padrao, 10/min auth e operacoes pesadas) |

---

## Backup e Recuperacao

### O que e salvo, onde e com que frequencia

| Item | Origem | Oracle Object Storage (10 GB free) | Google Drive pessoal | Retencao |
|---|---|:---:|:---:|---|
| Dump diario do banco | container `db-backup` (Postgres `pg_dump -Fc` as 07h BRT, em `/mnt/banco/backups`) | replicado | replicado | 7 dias |
| `.env` cifrado (GPG AES256) | `/home/ubuntu/argus-ai/.env` | replicado | replicado | 7 dias |
| Grafana (configs, dashboards, anotacoes) | `/mnt/banco/grafana` em tar.gz | replicado | replicado | 7 dias |
| Fotos / uploads (MinIO) | `/mnt/fotos` (espelhado via `rclone sync`) | nao | sim | espelho |
| Backup local | `/mnt/banco/backups` (na propria VM, sem replicacao para fora) | — | — | 7 dias |

### Como funciona

Tres camadas independentes:

1. **Container `db-backup`** (interno ao `docker-compose.prod.yml`): faz `pg_dump` todo
   dia as **07h BRT** e mantem os ultimos 7 dumps em `/mnt/banco/backups`. Atualiza a
   metrica `argus_backup_last_success_timestamp_seconds` para o Prometheus.

2. **Script `scripts/backup_to_clouds.sh`** (rodado via cron como root as **03h BRT**):
   - Pega o dump mais recente do banco
   - Cifra o `.env` com GPG (senha em `/root/.argus_gpg_passphrase`, chmod 600)
   - Empacota `/mnt/banco/grafana` em tar.gz
   - Replica para `oracle:argus-backups` e `gdrive:Argus_Backups`
   - Faz `rclone sync` das fotos apenas para Google Drive
   - Aplica retencao de 7 dias nos dois destinos
   - Atualiza metrica `argus_backup_clouds_last_success_timestamp_seconds`

3. **Alertas no Grafana**:
   - `alert-backup-falhou` dispara se o backup local nao atualizar por mais de 26h.
   - (TODO) Alerta analogo para `argus_backup_clouds_last_success_timestamp_seconds`.

### Restauracao

Use `scripts/restore_from_backup.sh` (interativo, requer `sudo`). O script lista os
backups disponiveis em Oracle ou Google Drive, pede a data, pergunta o que restaurar
(banco / `.env` / Grafana / fotos / tudo) e executa com confirmacao por item.

### Resiliencia coberta

| Cenario | Recuperacao |
|---|---|
| Dado perdido ou tabela corrompida | Restore do dump mais recente (`/mnt/banco/backups`, ou Oracle/GDrive) |
| VM Oracle terminada | Recreacao da VM + restore completo via Google Drive (banco + env + grafana + fotos) |
| Perda da conta Oracle | Backups continuam acessiveis no Google Drive |
| Perda da conta Google | Banco, env e grafana ainda no Oracle; fotos ficam perdidas se a VM tambem morreu |
| Perda da senha GPG | `.env` no backup vira inutilizavel — manter copia da senha em gerenciador seguro com backup redundante |

Detalhes operacionais (passos exatos de restore, checklist mensal de validacao,
contatos): ver [docs/disaster-recovery.md](docs/disaster-recovery.md).

### Setup inicial em uma VM nova

`bash scripts/setup_rclone.sh` imprime o roteiro completo (instalar rclone, configurar
os dois remotes, salvar senha GPG, ativar cron).

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
| [docs/MEU_GUIA_DE_ESTUDOS.md](docs/MEU_GUIA_DE_ESTUDOS.md) | Guia didatico de onboarding (camadas, IA, auth, offline, fluxos) |
| [docs/ambiente-local.md](docs/ambiente-local.md) | Rodar local (make dev x docker compose), volumes e sync de dados da VM |
| [docs/API.md](docs/API.md) | Referencia de todos os endpoints |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Guia de deploy |
| [docs/disaster-recovery.md](docs/disaster-recovery.md) | Plano de backup duplo (Oracle + Google Drive) e recuperacao em 5 cenarios |
| [docs/LGPD.md](docs/LGPD.md) | Compliance LGPD e protecao de dados |
| [docs/PRODUCTION_SECURITY.md](docs/PRODUCTION_SECURITY.md) | Seguranca em producao |
| [docs/runbook-argus-app-role.md](docs/runbook-argus-app-role.md) | Provisionamento do papel DB so-DML `argus_app` |
| [docs/secret-rotation.md](docs/secret-rotation.md) | Rotacao de chaves e segredos |
| [docs/oci-disk-encryption.md](docs/oci-disk-encryption.md) | Criptografia de disco em repouso (OCI Vault) |
| [monitoring/MANUAL_MONITORAMENTO.md](monitoring/MANUAL_MONITORAMENTO.md) | Stack de monitoramento (Prometheus + Grafana + alertas) |
| [docs/DATA_SANITIZATION.md](docs/DATA_SANITIZATION.md) | Sanitizacao de dados para publicacao |

---

## Autor

Desenvolvido por **Alex Abud** — AI Automation Engineer & Python Developer

---

<p align="center">
  <sub>Argus Panoptes — o que tudo ve e nada esquece.</sub>
</p>
