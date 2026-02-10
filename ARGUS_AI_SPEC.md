# ARGUS AI — Especificação Técnica Completa

> **Documento de referência para desenvolvimento com Claude Code**
> Versão: 1.0
> Última atualização: Fevereiro 2026

---

## ÍNDICE

1. [Visão Geral](#1-visão-geral)
2. [Stack Tecnológica](#2-stack-tecnológica)
3. [Estrutura do Projeto](#3-estrutura-do-projeto)
4. [Setup do Ambiente](#4-setup-do-ambiente)
5. [Banco de Dados](#5-banco-de-dados)
6. [Backend — FastAPI](#6-backend--fastapi)
7. [Módulo RAG](#7-módulo-rag)
8. [Visão Computacional](#8-visão-computacional)
9. [Frontend PWA](#9-frontend-pwa)
10. [Modo Offline e Sincronização](#10-modo-offline-e-sincronização)
11. [Autenticação e Segurança](#11-autenticação-e-segurança)
12. [LGPD e Compliance](#12-lgpd-e-compliance)
13. [Dashboard Analítico](#13-dashboard-analítico)
14. [Testes](#14-testes)
15. [Deploy e Infraestrutura](#15-deploy-e-infraestrutura)
16. [Convenções e Padrões de Código](#16-convenções-e-padrões-de-código)
17. [Decisões Arquiteturais (ADR)](#17-decisões-arquiteturais-adr)
18. [Roadmap de Desenvolvimento](#18-roadmap-de-desenvolvimento)
19. [Comandos Úteis](#19-comandos-úteis)
20. [Referência de Variáveis de Ambiente](#20-referência-de-variáveis-de-ambiente)
21. [CLAUDE.md](#21-claudemd)

---

## 1. VISÃO GERAL

### O que é

**Argus AI** é um sistema de apoio operacional para equipes de patrulhamento que funciona como **memória operacional da guarnição**, permitindo cadastro rápido de abordagens, consulta de histórico, relacionamento automático entre pessoas, armazenamento de ocorrências em PDF, auxílio na escrita de relatórios via RAG e análise geoespacial de padrões.

O nome faz referência a Argus Panoptes, o gigante de cem olhos da mitologia grega — aquele que tudo vê e nada esquece.

### Princípios inegociáveis

1. Cadastro de abordagem em **menos de 40 segundos**
2. Mínima digitação possível (voz, câmera, GPS automático, OCR de placa)
3. **Mobile-first** — funciona no smartphone durante patrulhamento
4. **Offline-first** — funciona sem sinal e sincroniza depois
5. IA apenas organiza informações existentes — **nunca inventa fatos**
6. Abordagem ≠ Ocorrência (conceitos distintos)
7. **Não substitui sistemas oficiais**
8. **LGPD desde o dia zero** — dados sensíveis tratados com criptografia, auditoria e retenção controlada
9. Cada guarnição/equipe só vê seus próprios dados (multi-tenancy)

### Conceitos de domínio

| Conceito | Definição |
|---|---|
| **Abordagem** | Registro operacional básico feito em campo (pessoas, veículos, local, fotos) |
| **Ocorrência** | Registro formal — PDF do sistema oficial, vinculado a uma abordagem |
| **Passagem** | Enquadramento legal (lei + artigo + crime) associado a pessoa numa abordagem |
| **Relacionamento** | Vínculo materializado entre pessoas que aparecem juntas em abordagens — com frequência calculada |
| **Guarnição** | Unidade/equipe operacional — define escopo de visibilidade dos dados |

---

## 2. STACK TECNOLÓGICA

### Backend

| Tecnologia | Versão | Propósito |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| FastAPI | 0.110+ | Framework web assíncrono |
| SQLAlchemy | 2.0+ | ORM (async) |
| Alembic | 1.13+ | Migrations do banco |
| Pydantic | 2.0+ | Validação e serialização |
| Uvicorn | 0.27+ | ASGI server |
| arq | 0.26+ | Worker assíncrono (background tasks) |
| python-multipart | latest | Upload de arquivos |
| python-jose | latest | JWT tokens |
| passlib[bcrypt] | latest | Hash de senhas |
| httpx | latest | HTTP client async |
| cryptography | latest | Criptografia de campos sensíveis (Fernet) |
| slowapi | latest | Rate limiting |

### Banco de Dados

| Tecnologia | Propósito |
|---|---|
| PostgreSQL 16 | Banco principal |
| pgvector | Extensão para embeddings vetoriais |
| PostGIS | Extensão para queries geoespaciais |
| pg_trgm | Busca textual fuzzy |
| unaccent | Normalização de acentos |

### IA / RAG

| Tecnologia | Propósito |
|---|---|
| sentence-transformers | Geração de embeddings de texto |
| Modelo: `paraphrase-multilingual-MiniLM-L12-v2` | Embedding model multilíngue (384 dim) |
| PyMuPDF (fitz) | Extração de texto de PDFs |
| LLM via API | Claude API ou Ollama local para geração de texto |

### Visão Computacional

| Tecnologia | Propósito |
|---|---|
| insightface | Detecção e embedding facial |
| onnxruntime | Runtime para modelos ONNX |
| Pillow | Manipulação de imagens |
| Tesseract / EasyOCR | OCR de placas veiculares |

### Frontend

| Tecnologia | Propósito |
|---|---|
| HTML5 + CSS3 + JS | PWA base |
| Alpine.js | Interatividade leve e reativa |
| Tailwind CSS (via CDN) | Estilização utilitária |
| IndexedDB (Dexie.js) | Fila offline local |
| Service Worker | Cache + sync em background |
| Web Speech API | Entrada por voz |
| Web App Manifest | Instalação como app |

### Infraestrutura

| Serviço | Propósito |
|---|---|
| Render ou Railway | Backend hosting |
| Neon ou Supabase | PostgreSQL gerenciado com pgvector + PostGIS |
| Upstash Redis | Cache + fila do arq worker |
| Cloudflare R2 | Storage de fotos e PDFs (S3-compatible) |
| GitHub Actions | CI/CD |

---

## 3. ESTRUTURA DO PROJETO

```
argus-ai/
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
├── app/
│   ├── __init__.py
│   ├── main.py                       # FastAPI app factory
│   ├── config.py                     # Settings via Pydantic BaseSettings
│   ├── dependencies.py               # Dependency injection
│   ├── worker.py                     # arq worker (background tasks)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # Agrupa todos os routers v1
│   │   │   ├── auth.py               # Login, registro, refresh token
│   │   │   ├── pessoas.py            # CRUD pessoas
│   │   │   ├── veiculos.py           # CRUD veículos
│   │   │   ├── abordagens.py         # CRUD abordagens
│   │   │   ├── ocorrencias.py        # Upload PDF, vinculação
│   │   │   ├── fotos.py              # Upload e busca por foto
│   │   │   ├── consultas.py          # Busca unificada, histórico
│   │   │   ├── relacionamentos.py    # Consulta de vínculos entre pessoas
│   │   │   ├── rag.py                # Geração de relatório
│   │   │   ├── legislacao.py         # Consulta de legislação
│   │   │   ├── analytics.py          # Dashboard analítico
│   │   │   └── sync.py               # Endpoint de sincronização offline
│   │   └── health.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                   # Base + mixins (Timestamp, SoftDelete, Audit)
│   │   ├── usuario.py
│   │   ├── guarnicao.py              # Multi-tenancy
│   │   ├── pessoa.py
│   │   ├── endereco.py
│   │   ├── veiculo.py
│   │   ├── abordagem.py
│   │   ├── foto.py
│   │   ├── passagem.py
│   │   ├── ocorrencia.py
│   │   ├── legislacao.py
│   │   ├── relacionamento.py         # Tabela materializada de vínculos
│   │   └── audit_log.py              # Log de auditoria
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── pessoa.py
│   │   ├── veiculo.py
│   │   ├── abordagem.py
│   │   ├── foto.py
│   │   ├── ocorrencia.py
│   │   ├── consulta.py
│   │   ├── relacionamento.py
│   │   ├── rag.py
│   │   ├── legislacao.py
│   │   ├── analytics.py
│   │   └── sync.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── pessoa_service.py
│   │   ├── veiculo_service.py
│   │   ├── abordagem_service.py
│   │   ├── relacionamento_service.py # Materialização de vínculos
│   │   ├── ocorrencia_service.py     # Upload PDF + extração
│   │   ├── rag_service.py            # Pipeline RAG completo
│   │   ├── embedding_service.py      # Geração de embeddings (com cache)
│   │   ├── face_service.py           # Reconhecimento facial
│   │   ├── ocr_service.py            # OCR de placas
│   │   ├── storage_service.py        # Upload/download S3
│   │   ├── legislacao_service.py
│   │   ├── llm_service.py            # Abstração da LLM
│   │   ├── analytics_service.py      # Agregações para dashboard
│   │   ├── crypto_service.py         # Criptografia de campos sensíveis
│   │   ├── audit_service.py          # Log de auditoria
│   │   ├── geocoding_service.py      # Geocodificação reversa
│   │   └── sync_service.py           # Sincronização offline
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py                   # Repository base genérico
│   │   ├── pessoa_repo.py
│   │   ├── veiculo_repo.py
│   │   ├── abordagem_repo.py
│   │   ├── ocorrencia_repo.py
│   │   ├── foto_repo.py
│   │   ├── relacionamento_repo.py
│   │   ├── legislacao_repo.py
│   │   └── audit_repo.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── session.py                # Engine + async session
│   │   └── init_db.py                # Extensões + seed
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py               # JWT, hashing
│   │   ├── crypto.py                 # Fernet encrypt/decrypt
│   │   ├── exceptions.py             # Exceções customizadas
│   │   ├── middleware.py              # Logging, CORS, rate limit, audit
│   │   ├── rate_limit.py             # SlowAPI config
│   │   ├── permissions.py            # Controle de acesso por guarnição
│   │   └── logging_config.py
│   │
│   └── tasks/                        # Background tasks (arq)
│       ├── __init__.py
│       ├── pdf_processor.py          # Extração texto + embedding de PDF
│       ├── face_processor.py         # Embedding facial
│       └── embedding_generator.py    # Geração batch de embeddings
│
├── frontend/
│   ├── index.html
│   ├── manifest.json
│   ├── sw.js                         # Service Worker (cache + background sync)
│   ├── css/
│   │   └── app.css
│   ├── js/
│   │   ├── app.js                    # Inicialização + router SPA
│   │   ├── api.js                    # HTTP client com retry
│   │   ├── auth.js
│   │   ├── db.js                     # IndexedDB via Dexie.js (fila offline)
│   │   ├── sync.js                   # Sincronização com backend
│   │   ├── pages/
│   │   │   ├── login.js
│   │   │   ├── abordagem-nova.js
│   │   │   ├── abordagem-detalhe.js
│   │   │   ├── consulta.js
│   │   │   ├── pessoa-detalhe.js
│   │   │   ├── ocorrencia-upload.js
│   │   │   ├── rag-relatorio.js
│   │   │   └── dashboard.js
│   │   └── components/
│   │       ├── camera.js             # Captura direta (getUserMedia)
│   │       ├── gps.js                # Geolocalização + geocoding reverso
│   │       ├── voice.js              # Web Speech API (ditado)
│   │       ├── ocr-placa.js          # OCR de placa no frontend
│   │       ├── autocomplete.js
│   │       ├── offline-indicator.js  # Badge de status offline
│   │       └── sync-queue.js         # UI da fila de sincronização
│   └── icons/
│
├── scripts/
│   ├── seed_legislacao.py
│   ├── seed_passagens.py
│   ├── update_legislacao.py          # Atualizar via LexML
│   └── generate_encryption_key.py    # Gerar chave Fernet
│
├── tests/
│   ├── conftest.py
│   ├── factories.py                  # Factory Boy
│   ├── unit/
│   │   ├── test_pessoa_service.py
│   │   ├── test_abordagem_service.py
│   │   ├── test_relacionamento.py
│   │   ├── test_rag_service.py
│   │   ├── test_embedding.py
│   │   ├── test_crypto.py
│   │   ├── test_audit.py
│   │   └── test_sync.py
│   ├── integration/
│   │   ├── test_api_abordagem.py
│   │   ├── test_api_ocorrencia.py
│   │   ├── test_api_consulta.py
│   │   ├── test_api_sync.py
│   │   └── test_api_analytics.py
│   └── e2e/
│       └── test_fluxo_completo.py
│
├── docs/
│   ├── API.md
│   ├── DEPLOY.md
│   ├── ARCHITECTURE.md
│   ├── LGPD.md                       # Política de dados
│   └── adr/                          # Architecture Decision Records
│       ├── 001-monolito-modular.md
│       ├── 002-pgvector-vs-faiss.md
│       ├── 003-pwa-vs-react-native.md
│       ├── 004-embedding-multilingual.md
│       ├── 005-offline-first.md
│       └── 006-multi-tenancy.md
│
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── CLAUDE.md                         # Instruções para Claude Code
└── README.md
```

---

## 4. SETUP DO AMBIENTE

### Pré-requisitos

- Python 3.11+
- PostgreSQL 16 com pgvector + PostGIS
- Redis (para arq worker + cache)
- Docker e Docker Compose (recomendado para dev)
- Tesseract OCR (`apt install tesseract-ocr tesseract-ocr-por`)

### docker-compose.yml

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: argus
      POSTGRES_PASSWORD: argus_dev
      POSTGRES_DB: argus_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init_extensions.sql:/docker-entrypoint-initdb.d/init.sql

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

  worker:
    build: .
    command: arq app.worker.WorkerSettings
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin

volumes:
  pgdata:
```

### Script de inicialização do PostgreSQL

```sql
-- scripts/init_extensions.sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Setup rápido

```bash
git clone <repo-url>
cd argus-ai

cp .env.example .env
python scripts/generate_encryption_key.py  # gerar ENCRYPTION_KEY

docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python scripts/seed_legislacao.py
docker compose exec api python scripts/seed_passagens.py
```

---

## 5. BANCO DE DADOS

### Extensões obrigatórias

| Extensão | Propósito |
|---|---|
| `vector` | Embeddings vetoriais (RAG + face) |
| `postgis` | Queries geoespaciais (abordagens por raio, mapa de calor) |
| `pg_trgm` | Busca fuzzy em nomes |
| `unaccent` | Normalização de acentos na busca |
| `pgcrypto` | Funções criptográficas no banco |

### Modelo completo — SQLAlchemy 2.0

#### Base e Mixins

```python
# app/models/base.py
from datetime import datetime
from typing import Optional
from sqlalchemy import func, Boolean, DateTime, String, Integer, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin para campos de auditoria temporal."""
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class SoftDeleteMixin:
    """Mixin para exclusão lógica — dados nunca são deletados."""
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    desativado_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    desativado_por_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )


class MultiTenantMixin:
    """Mixin para isolamento por guarnição."""
    guarnicao_id: Mapped[int] = mapped_column(
        ForeignKey("guarnicoes.id"),
        index=True
    )
```

#### Guarnição (Multi-tenancy)

```python
# app/models/guarnicao.py
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Guarnicao(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "guarnicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))        # ex: "3ª Cia - GU 01"
    unidade: Mapped[str] = mapped_column(String(200))      # ex: "3º BPM"
    codigo: Mapped[str] = mapped_column(String(50), unique=True)  # ex: "3BPM-3CIA-GU01"

    membros = relationship("Usuario", back_populates="guarnicao")
```

#### Usuário

```python
# app/models/usuario.py
from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class Usuario(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    matricula: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), unique=True, nullable=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    guarnicao_id: Mapped[int] = mapped_column(ForeignKey("guarnicoes.id"))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    guarnicao = relationship("Guarnicao", back_populates="membros")
```

#### Audit Log

```python
# app/models/audit_log.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AuditLog(Base):
    """Log imutável de todas as ações no sistema.
    Registra quem fez o quê, quando, de onde."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    acao: Mapped[str] = mapped_column(String(50), index=True)
        # CREATE, READ, UPDATE, DELETE, LOGIN, EXPORT, SEARCH, SYNC
    recurso: Mapped[str] = mapped_column(String(100))  # ex: "pessoa", "abordagem"
    recurso_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detalhes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        # JSON com campos alterados, query executada etc.
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
```

#### Pessoa (com campos criptografados)

```python
# app/models/pessoa.py
from datetime import date
from typing import Optional
from sqlalchemy import String, Date, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin


class Pessoa(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    __tablename__ = "pessoas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(300), index=True)
    cpf_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
        # CPF criptografado com Fernet
    cpf_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
        # SHA-256 do CPF para busca exata sem descriptografar
    data_nascimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    apelido: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    foto_principal_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    enderecos = relationship("EnderecoPessoa", back_populates="pessoa", lazy="selectin")
    abordagens = relationship("AbordagemPessoa", back_populates="pessoa", lazy="selectin")
    fotos = relationship("Foto", back_populates="pessoa", lazy="selectin")

    # Relacionamentos onde esta pessoa é participante
    relacionamentos_como_a = relationship(
        "RelacionamentoPessoa",
        foreign_keys="RelacionamentoPessoa.pessoa_id_a",
        back_populates="pessoa_a",
        lazy="selectin"
    )
    relacionamentos_como_b = relationship(
        "RelacionamentoPessoa",
        foreign_keys="RelacionamentoPessoa.pessoa_id_b",
        back_populates="pessoa_b",
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_pessoa_nome_trgm", "nome", postgresql_using="gin",
              postgresql_ops={"nome": "gin_trgm_ops"}),
        Index("idx_pessoa_guarnicao", "guarnicao_id"),
    )
```

#### Endereço da Pessoa

```python
# app/models/endereco.py
from datetime import date
from typing import Optional
from sqlalchemy import String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from app.models.base import Base, TimestampMixin


class EnderecoPessoa(Base, TimestampMixin):
    __tablename__ = "enderecos_pessoa"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(ForeignKey("pessoas.id", ondelete="CASCADE"))
    endereco: Mapped[str] = mapped_column(String(500))
    localizacao = mapped_column(Geography("POINT", srid=4326), nullable=True)
    data_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    pessoa = relationship("Pessoa", back_populates="enderecos")
```

#### Veículo

```python
# app/models/veiculo.py
from typing import Optional
from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin


class Veiculo(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    __tablename__ = "veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    placa: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    modelo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cor: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ano: Mapped[Optional[int]] = mapped_column(nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("idx_veiculo_guarnicao", "guarnicao_id"),
    )
```

#### Abordagem (com geoespacial)

```python
# app/models/abordagem.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography
from app.models.base import Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin


class Abordagem(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    __tablename__ = "abordagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    localizacao = mapped_column(Geography("POINT", srid=4326), nullable=True)
        # PostGIS point para queries geoespaciais
    endereco_texto: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    origem: Mapped[str] = mapped_column(String(20), default="online")
        # "online" | "offline_sync" — indica se veio de sincronização
    client_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
        # UUID gerado no frontend para deduplicação de sync

    pessoas = relationship("AbordagemPessoa", back_populates="abordagem",
                          lazy="selectin", cascade="all, delete-orphan")
    veiculos = relationship("AbordagemVeiculo", back_populates="abordagem",
                           lazy="selectin", cascade="all, delete-orphan")
    fotos = relationship("Foto", back_populates="abordagem", lazy="selectin")
    passagens = relationship("AbordagemPassagem", back_populates="abordagem",
                            lazy="selectin", cascade="all, delete-orphan")
    ocorrencias = relationship("Ocorrencia", back_populates="abordagem", lazy="selectin")

    __table_args__ = (
        Index("idx_abordagem_guarnicao_data", "guarnicao_id", "data_hora"),
        Index("idx_abordagem_localizacao", "localizacao", postgresql_using="gist"),
        Index("idx_abordagem_client_id", "client_id", unique=True,
              postgresql_where="client_id IS NOT NULL"),
    )


class AbordagemPessoa(Base):
    __tablename__ = "abordagem_pessoas"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(
        ForeignKey("abordagens.id", ondelete="CASCADE"))
    pessoa_id: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"))

    abordagem = relationship("Abordagem", back_populates="pessoas")
    pessoa = relationship("Pessoa", back_populates="abordagens")

    __table_args__ = (
        Index("uq_abordagem_pessoa", "abordagem_id", "pessoa_id", unique=True),
    )


class AbordagemVeiculo(Base):
    __tablename__ = "abordagem_veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(
        ForeignKey("abordagens.id", ondelete="CASCADE"))
    veiculo_id: Mapped[int] = mapped_column(
        ForeignKey("veiculos.id", ondelete="CASCADE"))

    abordagem = relationship("Abordagem", back_populates="veiculos")
    veiculo = relationship("Veiculo")

    __table_args__ = (
        Index("uq_abordagem_veiculo", "abordagem_id", "veiculo_id", unique=True),
    )
```

#### Foto (com embedding facial)

```python
# app/models/foto.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base


class Foto(Base):
    __tablename__ = "fotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    arquivo_url: Mapped[str] = mapped_column(String(500))
    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pessoa_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("pessoas.id"), nullable=True)
    abordagem_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("abordagens.id"), nullable=True)
    embedding_face = mapped_column(Vector(512), nullable=True)
        # InsightFace = 512 dimensões
    face_processada: Mapped[bool] = mapped_column(default=False)
        # Flag para o worker saber se já processou

    pessoa = relationship("Pessoa", back_populates="fotos")
    abordagem = relationship("Abordagem", back_populates="fotos")
```

#### Relacionamento materializado entre pessoas

```python
# app/models/relacionamento.py
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, ForeignKey, DateTime, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class RelacionamentoPessoa(Base):
    """Tabela materializada de vínculos entre pessoas.
    Atualizada automaticamente quando abordagens são criadas.
    pessoa_id_a < pessoa_id_b para evitar duplicatas."""
    __tablename__ = "relacionamento_pessoas"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id_a: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True)
    pessoa_id_b: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True)
    frequencia: Mapped[int] = mapped_column(Integer, default=1)
        # Quantas vezes foram abordadas juntas
    primeira_abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id"))
    ultima_abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id"))
    primeira_vez: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultima_vez: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now())

    pessoa_a = relationship("Pessoa", foreign_keys=[pessoa_id_a],
                           back_populates="relacionamentos_como_a")
    pessoa_b = relationship("Pessoa", foreign_keys=[pessoa_id_b],
                           back_populates="relacionamentos_como_b")

    __table_args__ = (
        UniqueConstraint("pessoa_id_a", "pessoa_id_b", name="uq_relacionamento"),
        Index("idx_relacionamento_freq", "frequencia"),
    )
```

#### Passagem e vinculação

```python
# app/models/passagem.py
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Passagem(Base):
    __tablename__ = "passagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    lei: Mapped[str] = mapped_column(String(100), index=True)
    artigo: Mapped[str] = mapped_column(String(50))
    nome_crime: Mapped[str] = mapped_column(String(300))

    __table_args__ = (
        Index("uq_passagem_lei_artigo", "lei", "artigo", unique=True),
    )


class AbordagemPassagem(Base):
    __tablename__ = "abordagem_passagens"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(
        ForeignKey("abordagens.id", ondelete="CASCADE"))
    pessoa_id: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"))
    passagem_id: Mapped[int] = mapped_column(ForeignKey("passagens.id"))

    abordagem = relationship("Abordagem", back_populates="passagens")
    pessoa = relationship("Pessoa")
    passagem = relationship("Passagem")
```

#### Ocorrência

```python
# app/models/ocorrencia.py
from typing import Optional
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.models.base import Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin


class Ocorrencia(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    __tablename__ = "ocorrencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_ocorrencia: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id"))
    arquivo_pdf_url: Mapped[str] = mapped_column(String(500))
    texto_extraido: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(384), nullable=True)
        # paraphrase-multilingual-MiniLM-L12-v2 = 384 dim
    processada: Mapped[bool] = mapped_column(default=False)
        # Flag para o worker saber se já extraiu texto + embedding
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))

    abordagem = relationship("Abordagem", back_populates="ocorrencias")
```

#### Legislação

```python
# app/models/legislacao.py
from typing import Optional
from sqlalchemy import String, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.models.base import Base, TimestampMixin


class Legislacao(Base, TimestampMixin):
    __tablename__ = "legislacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lei: Mapped[str] = mapped_column(String(100), index=True)
    artigo: Mapped[str] = mapped_column(String(50))
    nome: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    texto: Mapped[str] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding = mapped_column(Vector(384), nullable=True)

    __table_args__ = (
        Index("uq_legislacao_lei_artigo", "lei", "artigo", unique=True),
    )
```

### Índices críticos

```sql
-- Busca textual fuzzy em nomes (já no model)
CREATE INDEX idx_pessoa_nome_trgm ON pessoas USING gin (nome gin_trgm_ops);

-- Busca vetorial — ocorrências
CREATE INDEX idx_ocorrencia_embedding
    ON ocorrencias USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Busca vetorial — faces
CREATE INDEX idx_foto_face_embedding
    ON fotos USING ivfflat (embedding_face vector_cosine_ops) WITH (lists = 100);

-- Busca vetorial — legislação
CREATE INDEX idx_legislacao_embedding
    ON legislacoes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- Geoespacial — abordagens por raio
CREATE INDEX idx_abordagem_localizacao
    ON abordagens USING gist (localizacao);

-- Audit log — busca por período + usuário
CREATE INDEX idx_audit_timestamp_usuario
    ON audit_logs (timestamp DESC, usuario_id);
```

---

## 6. BACKEND — FastAPI

### App Factory

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database.session import engine
from app.api.v1.router import api_router
from app.api.health import router as health_router
from app.core.middleware import LoggingMiddleware, AuditMiddleware
from app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: carregar modelos de ML em memória
    from app.services.embedding_service import EmbeddingService
    from app.services.face_service import FaceService
    app.state.embedding_service = EmbeddingService()
    app.state.face_service = FaceService()
    yield
    # Shutdown
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Argus AI",
        description="Sistema de apoio operacional com IA",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Rate limiting
    app.state.limiter = limiter

    # Middlewares (ordem importa — último adicionado executa primeiro)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    # Frontend PWA
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

    return app


app = create_app()
```

### Configuração

```python
# app/config.py
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Argus AI"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas (turno completo)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # Encryption (LGPD)
    ENCRYPTION_KEY: str  # Fernet key para campos sensíveis

    # Storage
    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str = "argus"
    S3_REGION: str = "auto"

    # LLM
    LLM_PROVIDER: str = "anthropic"  # anthropic | ollama
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-r1:8b"

    # Embeddings
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSIONS: int = 384
    EMBEDDING_CACHE_TTL: int = 3600  # 1h cache de embeddings de busca

    # Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = 0.6

    # Geocoding
    GEOCODING_PROVIDER: str = "nominatim"  # nominatim (free) | google
    GOOGLE_MAPS_API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_HEAVY: str = "10/minute"  # endpoints de IA

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # LGPD
    DATA_RETENTION_DAYS: int = 1825  # 5 anos

    class Config:
        env_file = ".env"


settings = Settings()
```

### Async Database Session

```python
# app/database/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Rate Limiting

```python
# app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.REDIS_URL,
)
```

### Permissões por Guarnição

```python
# app/core/permissions.py
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.usuario import Usuario


class TenantFilter:
    """Garante que usuário só acessa dados da sua guarnição."""

    @staticmethod
    def apply(query, model_class, user: Usuario):
        """Adiciona filtro de guarnição em qualquer query."""
        if hasattr(model_class, "guarnicao_id"):
            return query.where(model_class.guarnicao_id == user.guarnicao_id)
        return query

    @staticmethod
    def check_ownership(resource, user: Usuario):
        """Verifica se recurso pertence à guarnição do usuário."""
        if hasattr(resource, "guarnicao_id"):
            if resource.guarnicao_id != user.guarnicao_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado — recurso de outra guarnição"
                )
```

### Criptografia de Campos Sensíveis

```python
# app/core/crypto.py
import hashlib
from cryptography.fernet import Fernet
from app.config import settings

_fernet = Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    """Criptografa valor sensível (CPF, etc)."""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(encrypted_value: str) -> str:
    """Descriptografa valor."""
    return _fernet.decrypt(encrypted_value.encode()).decode()


def hash_for_search(value: str) -> str:
    """Gera hash SHA-256 para busca exata sem descriptografar."""
    normalized = value.strip().replace(".", "").replace("-", "")
    return hashlib.sha256(normalized.encode()).hexdigest()
```

### Audit Service

```python
# app/services/audit_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog
import json


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        usuario_id: int,
        acao: str,
        recurso: str,
        recurso_id: int = None,
        detalhes: dict = None,
        ip_address: str = None,
        user_agent: str = None,
    ):
        entry = AuditLog(
            usuario_id=usuario_id,
            acao=acao,
            recurso=recurso,
            recurso_id=recurso_id,
            detalhes=json.dumps(detalhes, ensure_ascii=False) if detalhes else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        await self.db.flush()
```

### Background Worker (arq)

```python
# app/worker.py
from arq import cron
from arq.connections import RedisSettings
from app.config import settings
from app.tasks.pdf_processor import process_pdf
from app.tasks.face_processor import process_face
from app.tasks.embedding_generator import generate_embeddings_batch


class WorkerSettings:
    functions = [process_pdf, process_face, generate_embeddings_batch]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300  # 5 min por job
```

```python
# app/tasks/pdf_processor.py
import fitz  # PyMuPDF
from app.database.session import AsyncSessionLocal
from app.services.embedding_service import EmbeddingService
from app.services.text_utils import chunk_text_semantico
from sqlalchemy import update
from app.models.ocorrencia import Ocorrencia


async def process_pdf(ctx, ocorrencia_id: int):
    """Background task: extrai texto do PDF, gera embedding, salva."""
    async with AsyncSessionLocal() as db:
        # Buscar ocorrência
        from sqlalchemy import select
        result = await db.execute(
            select(Ocorrencia).where(Ocorrencia.id == ocorrencia_id)
        )
        ocorrencia = result.scalar_one_or_none()
        if not ocorrencia or ocorrencia.processada:
            return

        # Baixar PDF do storage e extrair texto
        from app.services.storage_service import StorageService
        storage = StorageService()
        pdf_bytes = await storage.download(ocorrencia.arquivo_pdf_url)

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texto = ""
        for page in doc:
            texto += page.get_text()
        doc.close()

        # Gerar embedding do texto completo
        embedding_svc = EmbeddingService()
        embedding = embedding_svc.gerar_embedding(texto[:8000])

        # Atualizar no banco
        await db.execute(
            update(Ocorrencia)
            .where(Ocorrencia.id == ocorrencia_id)
            .values(
                texto_extraido=texto,
                embedding=embedding,
                processada=True,
            )
        )
        await db.commit()
```

### Geocoding Reverso

```python
# app/services/geocoding_service.py
import httpx
from app.config import settings


class GeocodingService:
    async def reverse(self, lat: float, lon: float) -> str | None:
        """Converte coordenadas em endereço texto."""
        if settings.GEOCODING_PROVIDER == "nominatim":
            return await self._nominatim_reverse(lat, lon)
        elif settings.GEOCODING_PROVIDER == "google":
            return await self._google_reverse(lat, lon)
        return None

    async def _nominatim_reverse(self, lat: float, lon: float) -> str | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": lat, "lon": lon,
                    "format": "json", "addressdetails": 1,
                },
                headers={"User-Agent": "ArgusAI/2.0"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("display_name")
        return None

    async def _google_reverse(self, lat: float, lon: float) -> str | None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    "latlng": f"{lat},{lon}",
                    "key": settings.GOOGLE_MAPS_API_KEY,
                    "language": "pt-BR",
                },
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    return results[0].get("formatted_address")
        return None
```

### Exemplo de Router completo (Abordagens)

```python
# app/api/v1/abordagens.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import get_db
from app.dependencies import get_current_user
from app.schemas.abordagem import AbordagemCreate, AbordagemRead, AbordagemDetail
from app.services.abordagem_service import AbordagemService
from app.services.audit_service import AuditService
from app.models.usuario import Usuario
from app.core.rate_limit import limiter

router = APIRouter(prefix="/abordagens", tags=["Abordagens"])


@router.post("/", response_model=AbordagemRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def criar_abordagem(
    request: Request,
    data: AbordagemCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    service = AbordagemService(db)
    abordagem = await service.criar(data, user_id=user.id, guarnicao_id=user.guarnicao_id)

    # Audit log
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="abordagem",
        recurso_id=abordagem.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )

    return abordagem


@router.get("/{abordagem_id}", response_model=AbordagemDetail)
async def detalhe_abordagem(
    abordagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    service = AbordagemService(db)
    abordagem = await service.buscar_por_id(abordagem_id, user)
    if not abordagem:
        raise HTTPException(status_code=404, detail="Abordagem não encontrada")
    return abordagem


@router.get("/", response_model=List[AbordagemRead])
async def listar_abordagens(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    service = AbordagemService(db)
    return await service.listar(skip=skip, limit=limit, user=user)


@router.get("/raio/", response_model=List[AbordagemRead])
async def abordagens_por_raio(
    lat: float,
    lon: float,
    raio_metros: int = 500,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Busca abordagens num raio geográfico (PostGIS)."""
    service = AbordagemService(db)
    return await service.buscar_por_raio(lat, lon, raio_metros, user)
```

### Abordagem Service com geoespacial e relacionamentos

```python
# app/services/abordagem_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from app.models.abordagem import Abordagem, AbordagemPessoa, AbordagemVeiculo
from app.schemas.abordagem import AbordagemCreate
from app.services.relacionamento_service import RelacionamentoService
from app.services.geocoding_service import GeocodingService
from app.core.permissions import TenantFilter
from app.models.usuario import Usuario


class AbordagemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def criar(
        self, data: AbordagemCreate, user_id: int, guarnicao_id: int
    ) -> Abordagem:
        # Geocodificação reversa automática se não veio endereço
        endereco = data.endereco_texto
        if not endereco and data.latitude and data.longitude:
            geo = GeocodingService()
            endereco = await geo.reverse(data.latitude, data.longitude)

        # Criar ponto PostGIS
        localizacao = None
        if data.latitude and data.longitude:
            localizacao = f"POINT({data.longitude} {data.latitude})"

        abordagem = Abordagem(
            data_hora=data.data_hora,
            latitude=data.latitude,
            longitude=data.longitude,
            localizacao=localizacao,
            endereco_texto=endereco,
            observacao=data.observacao,
            usuario_id=user_id,
            guarnicao_id=guarnicao_id,
            origem=data.origem or "online",
            client_id=data.client_id,
        )
        self.db.add(abordagem)
        await self.db.flush()

        # Vincular pessoas
        for pid in data.pessoa_ids:
            self.db.add(AbordagemPessoa(
                abordagem_id=abordagem.id, pessoa_id=pid))

        # Vincular veículos
        for vid in data.veiculo_ids:
            self.db.add(AbordagemVeiculo(
                abordagem_id=abordagem.id, veiculo_id=vid))

        await self.db.flush()

        # Materializar relacionamentos entre pessoas
        if len(data.pessoa_ids) > 1:
            rel_service = RelacionamentoService(self.db)
            await rel_service.registrar_vinculo(
                data.pessoa_ids, abordagem.id, abordagem.data_hora
            )

        return abordagem

    async def buscar_por_id(self, abordagem_id: int, user: Usuario) -> Abordagem | None:
        query = select(Abordagem).where(Abordagem.id == abordagem_id)
        query = TenantFilter.apply(query, Abordagem, user)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def listar(
        self, skip: int, limit: int, user: Usuario
    ) -> list[Abordagem]:
        query = (
            select(Abordagem)
            .where(Abordagem.ativo == True)
            .order_by(Abordagem.data_hora.desc())
            .offset(skip)
            .limit(limit)
        )
        query = TenantFilter.apply(query, Abordagem, user)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def buscar_por_raio(
        self, lat: float, lon: float, raio_metros: int, user: Usuario
    ) -> list[Abordagem]:
        """Busca abordagens dentro de um raio geográfico usando PostGIS."""
        query = (
            select(Abordagem)
            .where(
                Abordagem.ativo == True,
                func.ST_DWithin(
                    Abordagem.localizacao,
                    func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
                    raio_metros,
                )
            )
            .order_by(Abordagem.data_hora.desc())
            .limit(50)
        )
        query = TenantFilter.apply(query, Abordagem, user)
        result = await self.db.execute(query)
        return result.scalars().all()
```

### Relacionamento Service (materialização)

```python
# app/services/relacionamento_service.py
from itertools import combinations
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from app.models.relacionamento import RelacionamentoPessoa


class RelacionamentoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def registrar_vinculo(
        self,
        pessoa_ids: list[int],
        abordagem_id: int,
        data_hora: datetime,
    ):
        """Cria ou atualiza vínculos entre todas as combinações de pessoas."""
        for id_a, id_b in combinations(sorted(set(pessoa_ids)), 2):
            # UPSERT: insere ou incrementa frequência
            stmt = insert(RelacionamentoPessoa).values(
                pessoa_id_a=id_a,
                pessoa_id_b=id_b,
                frequencia=1,
                primeira_abordagem_id=abordagem_id,
                ultima_abordagem_id=abordagem_id,
                primeira_vez=data_hora,
                ultima_vez=data_hora,
            ).on_conflict_do_update(
                constraint="uq_relacionamento",
                set_={
                    "frequencia": RelacionamentoPessoa.frequencia + 1,
                    "ultima_abordagem_id": abordagem_id,
                    "ultima_vez": data_hora,
                }
            )
            await self.db.execute(stmt)

    async def buscar_vinculos(self, pessoa_id: int) -> list[dict]:
        """Retorna todas as pessoas vinculadas e a frequência."""
        query = select(RelacionamentoPessoa).where(
            (RelacionamentoPessoa.pessoa_id_a == pessoa_id) |
            (RelacionamentoPessoa.pessoa_id_b == pessoa_id)
        ).order_by(RelacionamentoPessoa.frequencia.desc())

        result = await self.db.execute(query)
        return result.scalars().all()
```

---

## 7. MÓDULO RAG

### Pipeline completo

```
PDF Upload → arq worker enfileira
→ PyMuPDF extrai texto
→ Chunking semântico (por seção do BO)
→ paraphrase-multilingual-MiniLM-L12-v2 gera embeddings
→ pgvector armazena

Query:
→ embedding da pergunta (com cache Redis)
→ busca cosine similarity top-k no pgvector
→ Contexto + dados da abordagem + legislação → prompt
→ LLM gera relatório
→ Log de qualidade (feedback do usuário)
```

### Embedding Service (com cache)

```python
# app/services/embedding_service.py
import hashlib
import json
from sentence_transformers import SentenceTransformer
from app.config import settings

try:
    import redis.asyncio as aioredis
    _redis = aioredis.from_url(settings.REDIS_URL)
except Exception:
    _redis = None


class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def gerar_embedding(self, texto: str) -> list[float]:
        """Gera embedding de um texto."""
        return self.model.encode(texto).tolist()

    def gerar_embeddings_batch(self, textos: list[str]) -> list[list[float]]:
        """Gera embeddings em batch (mais eficiente)."""
        return self.model.encode(textos).tolist()

    async def gerar_embedding_cached(self, texto: str) -> list[float]:
        """Gera embedding com cache Redis para queries repetidas."""
        if _redis is None:
            return self.gerar_embedding(texto)

        cache_key = f"emb:{hashlib.md5(texto.encode()).hexdigest()}"
        cached = await _redis.get(cache_key)
        if cached:
            return json.loads(cached)

        embedding = self.gerar_embedding(texto)
        await _redis.setex(cache_key, settings.EMBEDDING_CACHE_TTL, json.dumps(embedding))
        return embedding
```

### Chunking Semântico para BOs

```python
# app/services/text_utils.py
import re


def chunk_text_semantico(texto: str) -> list[dict]:
    """Chunking inteligente para Boletins de Ocorrência.
    Divide por seções estruturais do documento, preservando contexto."""

    secoes_bo = [
        r"(?i)(hist[óo]rico|relato|narrativa|descri[çc][ãa]o dos fatos)",
        r"(?i)(envolvidos?|autor|v[íi]tima|testemunha|conduzido)",
        r"(?i)(provid[êe]ncias|encaminhamento|destino)",
        r"(?i)(objetos?|apreens[ãa]o|material)",
        r"(?i)(local|endere[çc]o|cena do crime)",
        r"(?i)(conclus[ãa]o|desfecho|resultado)",
    ]

    chunks = []
    texto_limpo = texto.strip()

    # Tentar dividir por seções do BO
    secoes_encontradas = []
    for pattern in secoes_bo:
        for match in re.finditer(pattern, texto_limpo):
            secoes_encontradas.append(match.start())

    if len(secoes_encontradas) >= 2:
        # Dividir por seções encontradas
        secoes_encontradas.sort()
        secoes_encontradas.append(len(texto_limpo))

        for i in range(len(secoes_encontradas) - 1):
            inicio = secoes_encontradas[i]
            fim = secoes_encontradas[i + 1]
            trecho = texto_limpo[inicio:fim].strip()
            if len(trecho) > 50:
                chunks.append({
                    "texto": trecho,
                    "tipo": "secao_bo",
                    "posicao": i,
                })
    else:
        # Fallback: chunking por parágrafos com overlap
        chunks = chunk_text_paragrafos(texto_limpo)

    return chunks


def chunk_text_paragrafos(
    texto: str, max_tokens: int = 500, overlap: int = 50
) -> list[dict]:
    """Fallback: divide por parágrafos com overlap."""
    paragrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    chunks = []
    buffer = ""
    buffer_words = 0

    for paragrafo in paragrafos:
        words = len(paragrafo.split())
        if buffer_words + words > max_tokens and buffer:
            chunks.append({"texto": buffer.strip(), "tipo": "paragrafo"})
            # Overlap: manter últimas palavras
            overlap_text = " ".join(buffer.split()[-overlap:])
            buffer = overlap_text + " " + paragrafo
            buffer_words = len(buffer.split())
        else:
            buffer += "\n\n" + paragrafo if buffer else paragrafo
            buffer_words += words

    if buffer.strip():
        chunks.append({"texto": buffer.strip(), "tipo": "paragrafo"})

    return chunks
```

### RAG Service

```python
# app/services/rag_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService


class RAGService:
    def __init__(self, db: AsyncSession, embedding_service: EmbeddingService):
        self.db = db
        self.embedding_svc = embedding_service
        self.llm = LLMService()

    async def buscar_contexto(self, query: str, top_k: int = 5) -> list[dict]:
        """Busca ocorrências similares no pgvector."""
        query_embedding = await self.embedding_svc.gerar_embedding_cached(query)

        sql = text("""
            SELECT
                id, numero_ocorrencia, texto_extraido,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM ocorrencias
            WHERE embedding IS NOT NULL AND ativo = true
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)

        result = await self.db.execute(sql, {
            "embedding": str(query_embedding),
            "limit": top_k,
        })

        return [
            {
                "id": row.id,
                "numero": row.numero_ocorrencia,
                "texto": row.texto_extraido[:2000],
                "similaridade": round(row.similarity, 3),
            }
            for row in result.fetchall()
            if row.similarity > 0.3  # Threshold mínimo de relevância
        ]

    async def buscar_legislacao(self, query: str, top_k: int = 3) -> list[dict]:
        """Busca artigos de lei relevantes."""
        query_embedding = await self.embedding_svc.gerar_embedding_cached(query)

        sql = text("""
            SELECT
                lei, artigo, nome, texto,
                1 - (embedding <=> :embedding::vector) as similarity
            FROM legislacoes
            WHERE embedding IS NOT NULL AND ativo = true
            ORDER BY embedding <=> :embedding::vector
            LIMIT :limit
        """)

        result = await self.db.execute(sql, {
            "embedding": str(query_embedding),
            "limit": top_k,
        })

        return [
            {
                "lei": row.lei,
                "artigo": row.artigo,
                "nome": row.nome,
                "texto": row.texto[:1000],
                "similaridade": round(row.similarity, 3),
            }
            for row in result.fetchall()
        ]

    async def gerar_relatorio(
        self, abordagem_id: int, instrucao: str = ""
    ) -> dict:
        """Gera relatório baseado nos dados da abordagem + contexto RAG.
        Retorna texto + metadados de fontes usadas."""

        # 1. Carregar dados da abordagem
        abordagem_data = await self._carregar_abordagem(abordagem_id)

        # 2. Buscar contexto similar
        query = f"{abordagem_data.get('observacao', '')} {abordagem_data.get('passagens_texto', '')}"
        contexto_ocorrencias = await self.buscar_contexto(query)
        contexto_legislacao = await self.buscar_legislacao(query)

        # 3. Montar prompt
        prompt = self._montar_prompt(
            abordagem_data, contexto_ocorrencias, contexto_legislacao, instrucao
        )

        # 4. Gerar com LLM
        texto_gerado = await self.llm.gerar(prompt)

        return {
            "relatorio": texto_gerado,
            "fontes": {
                "ocorrencias_usadas": [c["numero"] for c in contexto_ocorrencias],
                "legislacao_usada": [
                    f"{c['lei']} art. {c['artigo']}" for c in contexto_legislacao
                ],
            },
            "metricas": {
                "ocorrencias_encontradas": len(contexto_ocorrencias),
                "melhor_similaridade": (
                    contexto_ocorrencias[0]["similaridade"]
                    if contexto_ocorrencias else 0
                ),
            }
        }

    def _montar_prompt(self, abordagem, ocorrencias, legislacao, instrucao) -> str:
        return f"""Você é um assistente que ajuda a redigir relatórios operacionais policiais.

REGRAS ABSOLUTAS:
- Use APENAS as informações fornecidas abaixo
- NÃO invente fatos, nomes, datas ou detalhes
- Se não há informação suficiente, diga explicitamente

## DADOS DA ABORDAGEM ATUAL
{self._formatar_abordagem(abordagem)}

## OCORRÊNCIAS SIMILARES ANTERIORES (para referência de estilo e contexto)
{self._formatar_contexto(ocorrencias)}

## LEGISLAÇÃO POTENCIALMENTE APLICÁVEL
{self._formatar_legislacao(legislacao)}

## INSTRUÇÃO
{instrucao or "Gere um relatório curto e objetivo da abordagem, em linguagem técnica policial."}

Responda em português, de forma técnica, objetiva e em terceira pessoa."""

    async def _carregar_abordagem(self, abordagem_id: int) -> dict:
        """Carrega todos os dados relevantes da abordagem."""
        # Implementação: query com joins para pessoas, veículos, passagens
        ...

    def _formatar_abordagem(self, data: dict) -> str: ...
    def _formatar_contexto(self, ocorrencias: list) -> str: ...
    def _formatar_legislacao(self, legislacao: list) -> str: ...
```

### LLM Service (abstração multi-provider)

```python
# app/services/llm_service.py
import httpx
from app.config import settings


class LLMService:
    async def gerar(self, prompt: str, max_tokens: int = 2000) -> str:
        if settings.LLM_PROVIDER == "anthropic":
            return await self._gerar_anthropic(prompt, max_tokens)
        elif settings.LLM_PROVIDER == "ollama":
            return await self._gerar_ollama(prompt)
        raise ValueError(f"Provider não suportado: {settings.LLM_PROVIDER}")

    async def _gerar_anthropic(self, prompt: str, max_tokens: int) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]

    async def _gerar_ollama(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]
```

---

## 8. VISÃO COMPUTACIONAL

### Face Service

```python
# app/services/face_service.py
import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image
import io


class FaceService:
    def __init__(self):
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))

    def extrair_embedding(self, image_bytes: bytes) -> list[float] | None:
        """Extrai embedding facial de uma imagem."""
        img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        faces = self.app.get(img)
        if not faces:
            return None
        face = max(faces, key=lambda f: f.det_score)
        return face.embedding.tolist()

    def comparar(self, emb1: list[float], emb2: list[float]) -> float:
        """Calcula similaridade cosseno entre dois embeddings faciais."""
        a, b = np.array(emb1), np.array(emb2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
```

### OCR de Placas

```python
# app/services/ocr_service.py
import re
from PIL import Image
import io

try:
    import easyocr
    _reader = easyocr.Reader(["pt", "en"], gpu=False)
except ImportError:
    _reader = None


class OCRService:
    # Padrões de placa brasileira
    PLACA_ANTIGA = re.compile(r"[A-Z]{3}\s?-?\s?\d{4}")
    PLACA_MERCOSUL = re.compile(r"[A-Z]{3}\s?\d[A-Z]\d{2}")

    def extrair_placa(self, image_bytes: bytes) -> str | None:
        """Extrai placa veicular de uma imagem usando OCR."""
        if _reader is None:
            return None

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = _reader.readtext(
            img,
            detail=0,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ",
        )

        for text in results:
            text = text.upper().strip()
            # Tentar match com padrão Mercosul
            match = self.PLACA_MERCOSUL.search(text)
            if match:
                return self._normalizar(match.group())
            # Tentar match com padrão antigo
            match = self.PLACA_ANTIGA.search(text)
            if match:
                return self._normalizar(match.group())

        return None

    def _normalizar(self, placa: str) -> str:
        return re.sub(r"[\s-]", "", placa).upper()
```

---

## 9. FRONTEND PWA

### manifest.json

```json
{
  "name": "Argus AI",
  "short_name": "Argus",
  "description": "Sistema de apoio operacional com IA",
  "start_url": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0f172a",
  "theme_color": "#1e293b",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### API Client com retry

```javascript
// frontend/js/api.js
const API_BASE = "/api/v1";

class ApiClient {
  constructor() {
    this.token = localStorage.getItem("argus_token");
  }

  async request(method, path, body = null, retries = 2) {
    const headers = { "Content-Type": "application/json" };
    if (this.token) headers["Authorization"] = `Bearer ${this.token}`;

    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const res = await fetch(`${API_BASE}${path}`, opts);

        if (res.status === 401) {
          localStorage.removeItem("argus_token");
          window.location.href = "/#login";
          return null;
        }
        if (res.status === 429) {
          // Rate limited — esperar e tentar de novo
          const retryAfter = res.headers.get("Retry-After") || 5;
          await new Promise(r => setTimeout(r, retryAfter * 1000));
          continue;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      } catch (err) {
        if (attempt === retries) throw err;
        await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
      }
    }
  }

  get(path) { return this.request("GET", path); }
  post(path, body) { return this.request("POST", path, body); }
  put(path, body) { return this.request("PUT", path, body); }
  delete(path) { return this.request("DELETE", path); }

  async uploadFile(path, file, extraData = {}) {
    const formData = new FormData();
    formData.append("file", file);
    Object.entries(extraData).forEach(([k, v]) => formData.append(k, String(v)));

    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${this.token}` },
      body: formData,
    });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  }
}

const api = new ApiClient();
```

### Componente de Voz (Web Speech API)

```javascript
// frontend/js/components/voice.js
class VoiceInput {
  constructor() {
    this.recognition = null;
    this.isListening = false;

    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      this.recognition = new SpeechRecognition();
      this.recognition.lang = "pt-BR";
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
    }
  }

  isSupported() {
    return this.recognition !== null;
  }

  start(onResult, onEnd) {
    if (!this.recognition) return;

    this.recognition.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      const isFinal = event.results[event.results.length - 1].isFinal;
      onResult(transcript, isFinal);
    };

    this.recognition.onend = () => {
      this.isListening = false;
      if (onEnd) onEnd();
    };

    this.recognition.start();
    this.isListening = true;
  }

  stop() {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    }
  }
}

const voice = new VoiceInput();
```

### Componente de Câmera (captura direta)

```javascript
// frontend/js/components/camera.js
class CameraCapture {
  constructor() {
    this.stream = null;
    this.video = null;
  }

  async open(videoElement) {
    this.video = videoElement;
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1280 } },
        audio: false,
      });
      this.video.srcObject = this.stream;
      await this.video.play();
    } catch (err) {
      // Fallback: file picker
      return this.fallbackCapture();
    }
  }

  capture() {
    if (!this.video) return null;
    const canvas = document.createElement("canvas");
    canvas.width = this.video.videoWidth;
    canvas.height = this.video.videoHeight;
    canvas.getContext("2d").drawImage(this.video, 0, 0);
    return new Promise((resolve) => {
      canvas.toBlob(resolve, "image/jpeg", 0.8);
    });
  }

  close() {
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
  }

  fallbackCapture() {
    return new Promise((resolve) => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "image/*";
      input.capture = "environment";
      input.onchange = (e) => resolve(e.target.files[0]);
      input.click();
    });
  }
}

const camera = new CameraCapture();
```

### Componente GPS com Geocoding Reverso

```javascript
// frontend/js/components/gps.js
class GPSService {
  getLocation() {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocalização não suportada"));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        async (pos) => {
          const coords = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          };
          // Tentar geocoding reverso
          try {
            const endereco = await this.reverseGeocode(coords.latitude, coords.longitude);
            coords.endereco_texto = endereco;
          } catch (e) {
            coords.endereco_texto = null;
          }
          resolve(coords);
        },
        (err) => reject(err),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
  }

  async reverseGeocode(lat, lon) {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json`,
      { headers: { "User-Agent": "ArgusAI/2.0" } }
    );
    if (res.ok) {
      const data = await res.json();
      return data.display_name;
    }
    return null;
  }
}

const gps = new GPSService();
```

---

## 10. MODO OFFLINE E SINCRONIZAÇÃO

### Estratégia

O sistema é **offline-first**: toda ação em campo pode ser realizada sem internet. Os dados são salvos localmente no IndexedDB e sincronizados automaticamente quando a conexão retorna.

### IndexedDB via Dexie.js

```javascript
// frontend/js/db.js
import Dexie from "https://cdn.jsdelivr.net/npm/dexie@4/dist/dexie.min.mjs";

const db = new Dexie("ArgusAI");

db.version(1).stores({
  // Fila de sincronização
  syncQueue: "++id, tipo, status, criadoEm",
  // Cache local de dados
  pessoas: "id, nome, cpf_hash, apelido",
  veiculos: "id, placa, modelo",
  passagens: "id, lei, artigo, nome_crime",
});

// Adicionar item à fila de sync
async function enqueueSync(tipo, dados) {
  await db.syncQueue.add({
    tipo,           // "abordagem", "foto", "pessoa"
    dados,          // payload completo
    status: "pending",
    criadoEm: new Date().toISOString(),
    tentativas: 0,
    clientId: crypto.randomUUID(),
  });
}

// Buscar itens pendentes
async function getPendingSync() {
  return db.syncQueue.where("status").equals("pending").toArray();
}

// Marcar como sincronizado
async function markSynced(id) {
  await db.syncQueue.update(id, { status: "synced" });
}

// Marcar como falha
async function markFailed(id, erro) {
  await db.syncQueue.update(id, {
    status: "failed",
    erro,
    tentativas: (await db.syncQueue.get(id)).tentativas + 1,
  });
}

export { db, enqueueSync, getPendingSync, markSynced, markFailed };
```

### Sincronização automática

```javascript
// frontend/js/sync.js
import { getPendingSync, markSynced, markFailed } from "./db.js";

class SyncManager {
  constructor() {
    this.isSyncing = false;
    this.onStatusChange = null;

    // Escutar quando conexão volta
    window.addEventListener("online", () => this.syncAll());

    // Tentar sync a cada 30 segundos
    setInterval(() => {
      if (navigator.onLine && !this.isSyncing) this.syncAll();
    }, 30000);
  }

  async syncAll() {
    if (this.isSyncing) return;
    this.isSyncing = true;
    this._notify("syncing");

    try {
      const pending = await getPendingSync();
      if (pending.length === 0) {
        this._notify("idle");
        return;
      }

      // Sync endpoint aceita batch
      const response = await api.post("/sync/batch", {
        items: pending.map((item) => ({
          tipo: item.tipo,
          dados: item.dados,
          client_id: item.clientId,
        })),
      });

      if (response && response.results) {
        for (const result of response.results) {
          const item = pending.find((p) => p.clientId === result.client_id);
          if (!item) continue;

          if (result.status === "ok") {
            await markSynced(item.id);
          } else {
            await markFailed(item.id, result.error);
          }
        }
      }

      this._notify("done", pending.length);
    } catch (err) {
      this._notify("error", err.message);
    } finally {
      this.isSyncing = false;
    }
  }

  getPendingCount() {
    return getPendingSync().then((items) => items.length);
  }

  _notify(status, detail) {
    if (this.onStatusChange) this.onStatusChange(status, detail);
  }
}

const syncManager = new SyncManager();
export { syncManager };
```

### Service Worker com Background Sync

```javascript
// frontend/sw.js
const CACHE_NAME = "argus-v1";
const STATIC_ASSETS = [
  "/",
  "/css/app.css",
  "/js/app.js",
  "/js/api.js",
  "/js/db.js",
  "/js/sync.js",
  "/js/components/camera.js",
  "/js/components/gps.js",
  "/js/components/voice.js",
  "/manifest.json",
];

// Install: cachear assets estáticos
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate: limpar caches antigos
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network first para API, cache first para assets
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith("/api/")) {
    // API: network first, com fallback offline
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          // Se offline e é GET, tentar cache
          if (event.request.method === "GET") {
            return caches.match(event.request);
          }
          // Se offline e é POST/PUT, retornar erro controlado
          return new Response(
            JSON.stringify({ error: "offline", queued: true }),
            { status: 503, headers: { "Content-Type": "application/json" } }
          );
        })
    );
  } else {
    // Assets: cache first
    event.respondWith(
      caches.match(event.request).then((r) => r || fetch(event.request))
    );
  }
});

// Background Sync (quando conexão volta)
self.addEventListener("sync", (event) => {
  if (event.tag === "argus-sync") {
    event.waitUntil(
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => client.postMessage({ type: "SYNC_NOW" }));
      })
    );
  }
});
```

### Sync Endpoint no Backend

```python
# app/api/v1/sync.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import get_db
from app.dependencies import get_current_user
from app.schemas.sync import SyncBatchRequest, SyncBatchResponse, SyncItemResult
from app.services.sync_service import SyncService
from app.models.usuario import Usuario

router = APIRouter(prefix="/sync", tags=["Sincronização"])


@router.post("/batch", response_model=SyncBatchResponse)
async def sync_batch(
    data: SyncBatchRequest,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Recebe batch de itens criados offline e processa.
    Usa client_id para deduplicação (idempotente)."""
    service = SyncService(db)
    results = await service.process_batch(data.items, user)
    return SyncBatchResponse(results=results)
```

---

## 11. AUTENTICAÇÃO E SEGURANÇA

### JWT com Refresh Token

```python
# app/core/security.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return pwd_context.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    return pwd_context.verify(senha, hash)


def criar_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def criar_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str, expected_type: str = "access") -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
```

### Dependency de autenticação

```python
# app/dependencies.py
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.core.security import decodificar_token
from app.models.usuario import Usuario

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    payload = decodificar_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )

    user_id = payload.get("sub")
    result = await db.execute(
        select(Usuario).where(Usuario.id == int(user_id), Usuario.ativo == True)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return user


def get_face_service(request: Request):
    return request.app.state.face_service


def get_embedding_service(request: Request):
    return request.app.state.embedding_service
```

---

## 12. LGPD E COMPLIANCE

### Política de dados

| Aspecto | Implementação |
|---|---|
| **Criptografia em trânsito** | HTTPS obrigatório (TLS 1.3) |
| **Criptografia em repouso** | Campos sensíveis (CPF) criptografados com Fernet |
| **Busca sem descriptografar** | Hash SHA-256 do CPF para busca exata |
| **Audit trail** | Toda ação logada em `audit_logs` (quem, quando, o quê, de onde) |
| **Soft delete** | Nenhum dado é deletado fisicamente — apenas desativado |
| **Retenção** | Dados mantidos por 5 anos (configurável), depois anonimizados |
| **Multi-tenancy** | Guarnição só acessa seus próprios dados |
| **Consentimento** | Tema delicado — consultar jurídico da corporação |
| **Minimização** | Coletar apenas dados estritamente necessários |
| **Logs imutáveis** | Tabela `audit_logs` é append-only, sem UPDATE ou DELETE |

### Script de anonimização periódica

```python
# scripts/anonymize_expired.py
"""Anonimiza dados expirados conforme política de retenção."""
from datetime import datetime, timedelta
from sqlalchemy import update, and_
from app.config import settings
from app.models.pessoa import Pessoa
from app.core.crypto import encrypt

RETENTION = timedelta(days=settings.DATA_RETENTION_DAYS)

async def anonymize():
    cutoff = datetime.utcnow() - RETENTION
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(Pessoa)
            .where(
                and_(
                    Pessoa.ativo == False,
                    Pessoa.desativado_em < cutoff,
                )
            )
            .values(
                nome="[ANONIMIZADO]",
                cpf_encrypted=None,
                cpf_hash=None,
                apelido=None,
                foto_principal_url=None,
                observacoes=None,
            )
        )
        await db.commit()
```

---

## 13. DASHBOARD ANALÍTICO

### Endpoints

```python
# app/api/v1/analytics.py
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.services.analytics_service import AnalyticsService
from app.models.usuario import Usuario

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/resumo")
async def resumo_geral(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Retorna métricas resumidas para o dashboard."""
    svc = AnalyticsService(db)
    return await svc.resumo(user.guarnicao_id, dias)


@router.get("/mapa-calor")
async def mapa_calor(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Retorna coordenadas para mapa de calor de abordagens."""
    svc = AnalyticsService(db)
    return await svc.heatmap(user.guarnicao_id, dias)


@router.get("/horarios-pico")
async def horarios_pico(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Distribuição de abordagens por hora do dia."""
    svc = AnalyticsService(db)
    return await svc.distribuicao_horaria(user.guarnicao_id, dias)


@router.get("/pessoas-recorrentes")
async def pessoas_recorrentes(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Top pessoas mais abordadas."""
    svc = AnalyticsService(db)
    return await svc.pessoas_mais_abordadas(user.guarnicao_id, limit)


@router.get("/rag-qualidade")
async def metricas_rag(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Métricas de qualidade do RAG (similaridade média, uso)."""
    svc = AnalyticsService(db)
    return await svc.metricas_rag(user.guarnicao_id)
```

### Analytics Service

```python
# app/services/analytics_service.py
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, select
from app.models.abordagem import Abordagem, AbordagemPessoa


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resumo(self, guarnicao_id: int, dias: int) -> dict:
        desde = datetime.utcnow() - timedelta(days=dias)

        # Total de abordagens no período
        total = await self.db.execute(
            select(func.count(Abordagem.id))
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.data_hora >= desde,
                Abordagem.ativo == True,
            )
        )
        total_abordagens = total.scalar()

        # Pessoas distintas abordadas
        pessoas = await self.db.execute(
            select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
            .join(Abordagem)
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.data_hora >= desde,
            )
        )
        total_pessoas = pessoas.scalar()

        return {
            "periodo_dias": dias,
            "total_abordagens": total_abordagens,
            "total_pessoas_distintas": total_pessoas,
            "media_abordagens_dia": round(total_abordagens / max(dias, 1), 1),
        }

    async def heatmap(self, guarnicao_id: int, dias: int) -> list[dict]:
        """Retorna pontos para mapa de calor."""
        desde = datetime.utcnow() - timedelta(days=dias)

        result = await self.db.execute(
            select(Abordagem.latitude, Abordagem.longitude)
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.data_hora >= desde,
                Abordagem.ativo == True,
                Abordagem.latitude.isnot(None),
            )
        )

        return [
            {"lat": row.latitude, "lon": row.longitude}
            for row in result.fetchall()
        ]

    async def distribuicao_horaria(self, guarnicao_id: int, dias: int) -> list[dict]:
        desde = datetime.utcnow() - timedelta(days=dias)

        result = await self.db.execute(text("""
            SELECT
                EXTRACT(HOUR FROM data_hora) as hora,
                COUNT(*) as total
            FROM abordagens
            WHERE guarnicao_id = :gid
                AND data_hora >= :desde
                AND ativo = true
            GROUP BY hora
            ORDER BY hora
        """), {"gid": guarnicao_id, "desde": desde})

        return [{"hora": int(row.hora), "total": row.total} for row in result.fetchall()]

    async def pessoas_mais_abordadas(self, guarnicao_id: int, limit: int) -> list[dict]:
        result = await self.db.execute(text("""
            SELECT
                p.id, p.nome, p.apelido,
                COUNT(ap.id) as total_abordagens,
                MAX(a.data_hora) as ultima_abordagem
            FROM pessoas p
            JOIN abordagem_pessoas ap ON ap.pessoa_id = p.id
            JOIN abordagens a ON a.id = ap.abordagem_id
            WHERE a.guarnicao_id = :gid AND a.ativo = true AND p.ativo = true
            GROUP BY p.id, p.nome, p.apelido
            ORDER BY total_abordagens DESC
            LIMIT :limit
        """), {"gid": guarnicao_id, "limit": limit})

        return [
            {
                "id": row.id,
                "nome": row.nome,
                "apelido": row.apelido,
                "total_abordagens": row.total_abordagens,
                "ultima_abordagem": row.ultima_abordagem.isoformat() if row.ultima_abordagem else None,
            }
            for row in result.fetchall()
        ]

    async def metricas_rag(self, guarnicao_id: int) -> dict:
        """Métricas de uso e qualidade do RAG."""
        # Contar ocorrências com embedding (processadas)
        from app.models.ocorrencia import Ocorrencia
        total = await self.db.execute(
            select(func.count(Ocorrencia.id))
            .where(Ocorrencia.guarnicao_id == guarnicao_id)
        )
        processadas = await self.db.execute(
            select(func.count(Ocorrencia.id))
            .where(
                Ocorrencia.guarnicao_id == guarnicao_id,
                Ocorrencia.processada == True,
            )
        )
        return {
            "total_ocorrencias": total.scalar(),
            "ocorrencias_indexadas": processadas.scalar(),
        }
```

---

## 14. TESTES

### conftest.py

```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import create_app
from app.models.base import Base
from app.database.session import get_db
from app.core.security import criar_access_token

TEST_DB_URL = "postgresql+asyncpg://test:test@localhost:5432/argus_test"

engine_test = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as session:
        yield session
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session):
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers():
    token = criar_access_token({"sub": "1"})
    return {"Authorization": f"Bearer {token}"}
```

### Exemplo de testes

```python
# tests/unit/test_crypto.py
from app.core.crypto import encrypt, decrypt, hash_for_search


def test_encrypt_decrypt():
    original = "12345678901"
    encrypted = encrypt(original)
    assert encrypted != original
    assert decrypt(encrypted) == original


def test_hash_for_search():
    cpf = "123.456.789-01"
    h1 = hash_for_search(cpf)
    h2 = hash_for_search("12345678901")
    assert h1 == h2  # Normalizado, mesmo hash


# tests/unit/test_relacionamento.py
import pytest
from app.services.relacionamento_service import RelacionamentoService


@pytest.mark.asyncio
async def test_registrar_vinculo_cria_relacionamento(db_session):
    service = RelacionamentoService(db_session)
    # ... criar pessoas e abordagem ...
    await service.registrar_vinculo([1, 2, 3], abordagem_id=1, data_hora=datetime.now())
    # Deve criar 3 vínculos: (1,2), (1,3), (2,3)


# tests/integration/test_api_abordagem.py
@pytest.mark.asyncio
async def test_criar_abordagem_api(client, auth_headers):
    response = await client.post("/api/v1/abordagens/", json={
        "data_hora": "2026-02-10T14:00:00-03:00",
        "latitude": -15.7942,
        "longitude": -47.8822,
        "observacao": "Abordagem de rotina na W3 Sul",
        "pessoa_ids": [],
        "veiculo_ids": [],
    }, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["endereco_texto"] is not None  # Geocoding reverso preencheu
```

### Rodar testes

```bash
pytest -v                           # Todos
pytest tests/unit -v                # Apenas unit
pytest tests/integration -v         # Apenas integração
pytest --cov=app --cov-report=html  # Com coverage
pytest -k "test_crypto" -v          # Filtrar por nome
```

---

## 15. DEPLOY E INFRAESTRUTURA

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### pyproject.toml

```toml
[project]
name = "argus-ai"
version = "2.0.0"
description = "Sistema de apoio operacional com IA"
requires-python = ">=3.11"
dependencies = [
    # Web
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.6",
    "slowapi>=0.1.9",
    # Database
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pgvector>=0.2.5",
    "geoalchemy2>=0.15.0",
    # Validation
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    # Auth
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "cryptography>=42.0.0",
    # HTTP
    "httpx>=0.27.0",
    # AI / RAG
    "sentence-transformers>=2.3.0",
    "pymupdf>=1.23.0",
    # Vision
    "insightface>=0.7.3",
    "onnxruntime>=1.16.0",
    "pillow>=10.0.0",
    "easyocr>=1.7.0",
    # Storage
    "boto3>=1.34.0",
    # Worker
    "arq>=0.26.0",
    # Cache
    "redis>=5.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.27.0",
    "ruff>=0.2.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "factory-boy>=3.3.0",
]

[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "N", "W", "UP", "S", "B"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.11"
plugins = ["pydantic.mypy"]
```

### GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: Argus AI CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: argus_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install system deps
        run: sudo apt-get install -y tesseract-ocr tesseract-ocr-por

      - name: Install Python deps
        run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check app/ tests/

      - name: Type check
        run: mypy app/ --ignore-missing-imports

      - name: Tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/argus_test
          REDIS_URL: redis://localhost:6379
          SECRET_KEY: test-secret-key-ci
          ENCRYPTION_KEY: ZmVybmV0LXRlc3Qta2V5LWZvci1jaS1vbmx5LTEyMzQ1
        run: pytest --cov=app -v
```

---

## 16. CONVENÇÕES E PADRÕES DE CÓDIGO

### Arquitetura em camadas

```
Router (API) → Service (Negócio) → Repository (Dados)
     ↓              ↓                    ↓
  Schemas       Models/Logic         SQLAlchemy
```

- **Router**: recebe request, valida, chama service, retorna response. NUNCA contém lógica
- **Service**: toda lógica de negócio. NUNCA importa FastAPI
- **Repository**: queries ao banco. NUNCA contém lógica de negócio
- **Core**: utilidades transversais (security, crypto, exceptions)
- **Tasks**: jobs assíncronos rodando no arq worker

### Idioma

- Código (variáveis, funções, classes): **inglês**
- Strings de domínio, mensagens ao usuário: **português**
- Docstrings: **português**
- Commits: **português**

### Commits

Formato: `tipo(escopo): descrição`

Tipos: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `security`

```
feat(abordagem): criar endpoint de busca por raio geoespacial
fix(rag): corrigir chunking semântico para BOs com tabelas
security(pessoa): criptografar CPF em repouso com Fernet
test(sync): adicionar testes de sincronização offline
```

### Branches

```
main        → produção
develop     → integração
feat/xxx    → features
fix/xxx     → correções
security/x  → correções de segurança
```

---

## 17. DECISÕES ARQUITETURAIS (ADR)

### ADR-001: Monolito Modular

**Decisão**: Monolito com separação lógica interna (routers → services → repositories).

**Contexto**: Equipe de 1 desenvolvedor, MVP com prazo curto. Microserviços adicionam complexidade operacional desnecessária (deploy, rede, debugging).

**Consequência**: Deploy simples, debugging fácil, refatoração para serviços separados possível no futuro via extração de services.

### ADR-002: pgvector em vez de FAISS

**Decisão**: Usar pgvector (extensão PostgreSQL) para armazenar e buscar embeddings.

**Contexto**: FAISS é mais rápido em datasets grandes (>1M vetores), mas requer gerenciar um índice separado em memória. pgvector vive dentro do PostgreSQL: um banco só para dados + vetores + geo, com transações ACID e backup unificado.

**Consequência**: Menos infra, queries SQL padrão, escala até ~500K vetores sem problemas. Se precisar de mais, migrar para FAISS ou Pinecone.

### ADR-003: PWA em vez de React Native

**Decisão**: PWA puro (HTML + JS + Alpine.js) em vez de app nativo ou React Native.

**Contexto**: O sistema precisa rodar em qualquer smartphone sem instalação via loja. PWA permite câmera, GPS, offline, e instalação como app. Evita complexidade de build nativo, conta de desenvolvedor nas stores, e review process.

**Consequência**: Limitações em acesso a hardware avançado (NFC, biometria nativa), mas cobre 100% dos requisitos operacionais do Argus AI.

### ADR-004: Embedding Multilíngue

**Decisão**: Usar `paraphrase-multilingual-MiniLM-L12-v2` em vez de `all-MiniLM-L6-v2`.

**Contexto**: Todo conteúdo do sistema é em português. O modelo `all-MiniLM-L6-v2` foi treinado primariamente em inglês e tem performance inferior para busca semântica em português. O modelo multilíngue tem a mesma dimensão (384) mas performance significativamente melhor para PT-BR.

**Consequência**: Mesma dimensão de embedding (sem impacto no banco), melhor qualidade de busca semântica, marginal aumento no tempo de inferência.

### ADR-005: Offline-First

**Decisão**: Sistema funciona offline com fila local (IndexedDB) e sincronização automática.

**Contexto**: Patrulhamento em Brasília tem áreas sem cobertura 4G. Perder uma abordagem porque não tinha sinal é inaceitável. Offline-first garante que o trabalho nunca é perdido.

**Consequência**: Complexidade adicional no frontend (IndexedDB, sync, conflitos), endpoint de sincronização idempotente no backend (client_id para deduplicação).

### ADR-006: Multi-tenancy por Guarnição

**Decisão**: Isolamento de dados por guarnição via campo `guarnicao_id` em todas as tabelas sensíveis.

**Contexto**: Dados de abordagens são operacionalmente sensíveis. Uma guarnição não deve ver dados de outra. A alternativa (banco separado por guarnição) é overkill para o MVP.

**Consequência**: Toda query passa pelo `TenantFilter` que injeta o filtro de guarnição. Simples e eficaz. Pode evoluir para Row Level Security (RLS) do PostgreSQL no futuro.

---

## 18. ROADMAP DE DESENVOLVIMENTO

### Fase 1 — Fundação (Semanas 1-2)

- [ ] Setup do projeto (pyproject.toml, docker-compose, .env)
- [ ] Configuração FastAPI + SQLAlchemy async + Alembic
- [ ] Models completos (todos os models com mixins)
- [ ] Extensões PostgreSQL (pgvector, PostGIS, pg_trgm)
- [ ] Autenticação JWT (registro + login + refresh token)
- [ ] Modelo de Guarnição + multi-tenancy
- [ ] Criptografia de campos sensíveis (CPF)
- [ ] Audit Log básico
- [ ] Health check endpoint
- [ ] Rate limiting

### Fase 2 — Core Operacional (Semanas 3-4)

- [ ] CRUD Pessoa (com busca fuzzy e CPF criptografado)
- [ ] CRUD Veículo (com busca por placa)
- [ ] CRUD Abordagem completo (com PostGIS)
- [ ] Vinculação pessoa ↔ abordagem
- [ ] Vinculação veículo ↔ abordagem
- [ ] Relacionamento materializado entre pessoas (UPSERT)
- [ ] Upload de fotos + storage S3
- [ ] CRUD Passagens
- [ ] Geocoding reverso automático
- [ ] Endpoint de busca por raio geográfico
- [ ] Endpoint de consulta unificada

### Fase 3 — RAG (Semanas 5-6)

- [ ] arq worker setup (Redis)
- [ ] Upload PDF de ocorrência → task assíncrona
- [ ] Extração de texto com PyMuPDF
- [ ] Chunking semântico (seções de BO)
- [ ] Embedding multilíngue (paraphrase-multilingual)
- [ ] Cache de embeddings de busca (Redis)
- [ ] Busca por similaridade no pgvector
- [ ] Integração LLM (Claude API + Ollama)
- [ ] Endpoint de geração de relatório
- [ ] Seed de legislação (Código Penal)
- [ ] Busca semântica em legislação
- [ ] Métricas de qualidade do RAG

### Fase 4 — Visão Computacional (Semana 7)

- [ ] Setup InsightFace
- [ ] Task assíncrona de embedding facial
- [ ] Busca por foto (similaridade facial via pgvector)
- [ ] OCR de placa veicular (EasyOCR)
- [ ] Endpoint de busca por rosto
- [ ] Endpoint de OCR de placa

### Fase 5 — Frontend PWA (Semanas 8-10)

- [ ] Estrutura PWA (manifest, service worker)
- [ ] Tela de login
- [ ] Tela de nova abordagem
  - [ ] GPS automático + geocoding reverso
  - [ ] Captura de foto (getUserMedia)
  - [ ] Entrada por voz (Web Speech API)
  - [ ] OCR de placa no frontend
  - [ ] Autocomplete de pessoas e veículos
- [ ] Tela de consulta unificada
- [ ] Tela de detalhe de pessoa (com vínculos)
- [ ] Tela de upload de ocorrência
- [ ] Tela de geração de relatório (RAG)
- [ ] Dashboard analítico
  - [ ] Mapa de calor de abordagens
  - [ ] Gráfico de horários de pico
  - [ ] Pessoas mais abordadas
- [ ] Modo offline completo
  - [ ] IndexedDB com Dexie.js
  - [ ] Fila de sincronização
  - [ ] Indicador de status offline
  - [ ] Background sync
- [ ] Testes de uso mobile em campo

### Fase 6 — Polimento e Deploy (Semanas 11-12)

- [ ] Testes completos (unit + integration + e2e)
- [ ] CI/CD com GitHub Actions
- [ ] Deploy backend em Render/Railway
- [ ] PostgreSQL gerenciado (Neon com pgvector + PostGIS)
- [ ] Redis gerenciado (Upstash)
- [ ] Storage em Cloudflare R2
- [ ] Monitoramento e alertas
- [ ] Documentação final (API, deploy, LGPD)
- [ ] ADRs finalizados
- [ ] README com GIF/vídeo demonstrativo
- [ ] Script de anonimização periódica

---

## 19. COMANDOS ÚTEIS

### Makefile

```makefile
.PHONY: dev test lint migrate seed worker

dev:
	docker compose up -d db redis minio
	uvicorn app.main:app --reload

worker:
	arq app.worker.WorkerSettings

test:
	pytest -v --cov=app

lint:
	ruff check app/ tests/
	mypy app/ --ignore-missing-imports

format:
	ruff format app/ tests/

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

seed:
	python scripts/seed_legislacao.py
	python scripts/seed_passagens.py

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f api worker

encrypt-key:
	python scripts/generate_encryption_key.py
```

---

## 20. REFERÊNCIA DE VARIÁVEIS DE AMBIENTE

```env
# .env.example

# ══════════════════════════════════
# APP
# ══════════════════════════════════
DEBUG=true

# ══════════════════════════════════
# DATABASE
# ══════════════════════════════════
DATABASE_URL=postgresql://argus:argus_dev@localhost:5432/argus_db

# ══════════════════════════════════
# REDIS
# ══════════════════════════════════
REDIS_URL=redis://localhost:6379

# ══════════════════════════════════
# AUTH
# ══════════════════════════════════
SECRET_KEY=gerar-chave-segura-com-openssl-rand-hex-32
ACCESS_TOKEN_EXPIRE_MINUTES=480
REFRESH_TOKEN_EXPIRE_DAYS=30

# ══════════════════════════════════
# ENCRYPTION (LGPD)
# ══════════════════════════════════
ENCRYPTION_KEY=gerar-com-scripts/generate_encryption_key.py

# ══════════════════════════════════
# STORAGE (MinIO local / Cloudflare R2 em prod)
# ══════════════════════════════════
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=argus

# ══════════════════════════════════
# LLM
# ══════════════════════════════════
LLM_PROVIDER=ollama
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b

# ══════════════════════════════════
# EMBEDDINGS
# ══════════════════════════════════
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSIONS=384
EMBEDDING_CACHE_TTL=3600

# ══════════════════════════════════
# FACE RECOGNITION
# ══════════════════════════════════
FACE_SIMILARITY_THRESHOLD=0.6

# ══════════════════════════════════
# GEOCODING
# ══════════════════════════════════
GEOCODING_PROVIDER=nominatim
GOOGLE_MAPS_API_KEY=

# ══════════════════════════════════
# RATE LIMITING
# ══════════════════════════════════
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_AUTH=10/minute
RATE_LIMIT_HEAVY=10/minute

# ══════════════════════════════════
# CORS
# ══════════════════════════════════
CORS_ORIGINS=["http://localhost:8000","http://localhost:3000"]

# ══════════════════════════════════
# LGPD
# ══════════════════════════════════
DATA_RETENTION_DAYS=1825
```

---

## 21. CLAUDE.md

Copie o bloco abaixo para o arquivo `CLAUDE.md` na raiz do projeto:

```markdown
# CLAUDE.md — Argus AI

## Projeto
Argus AI — Sistema de apoio operacional com IA para equipes de patrulhamento.
Memória operacional da guarnição: abordagens, ocorrências, RAG, reconhecimento facial, análise geoespacial.

## Stack
- Python 3.11+ / FastAPI / SQLAlchemy 2.0 async / Alembic
- PostgreSQL 16 + pgvector + PostGIS + pg_trgm
- Redis (cache + arq worker)
- SentenceTransformers (paraphrase-multilingual-MiniLM-L12-v2)
- InsightFace (reconhecimento facial) + EasyOCR (placas)
- PWA frontend (HTML + Alpine.js + Tailwind)
- Cloudflare R2 (storage)

## Estrutura
- `app/api/` — Routers FastAPI (camada HTTP, versionada em v1/)
- `app/services/` — Lógica de negócio (NUNCA importa FastAPI)
- `app/repositories/` — Acesso a dados (queries)
- `app/models/` — SQLAlchemy models (com mixins: Timestamp, SoftDelete, MultiTenant)
- `app/schemas/` — Pydantic schemas
- `app/core/` — Security, crypto, exceptions, middleware, rate_limit, permissions
- `app/tasks/` — Background tasks via arq worker
- `frontend/` — PWA offline-first
- `tests/` — pytest async (unit + integration + e2e)
- `scripts/` — Seed, atualização legislação, geração de chave

## Convenções
- Router NUNCA contém lógica — delega para Service
- Service NUNCA importa FastAPI
- Toda query sensível passa por TenantFilter (multi-tenancy por guarnição)
- Soft delete em tudo (SoftDeleteMixin) — dados nunca são removidos
- CPF criptografado (Fernet) + hash SHA-256 para busca
- Audit log em todas as ações (AuditService)
- Async em todo o backend (asyncpg + SQLAlchemy async)
- Tarefas pesadas (PDF, embedding, face) vão para o arq worker
- Ruff para lint, mypy para types
- Commits: tipo(escopo): descrição [pt-BR]
- Código em inglês, domínio/mensagens em português

## Comandos
- `make dev` — sobe ambiente local
- `make worker` — sobe arq worker
- `make test` — roda testes
- `make lint` — lint + type check
- `make migrate msg="descricao"` — nova migration
- `make seed` — popular legislação e passagens

## Banco
- pgvector: embeddings (384 dim texto, 512 dim face)
- PostGIS: queries geoespaciais (busca por raio, mapa de calor)
- pg_trgm: busca fuzzy em nomes
- Índices IVFFlat para busca vetorial
- Índice GiST para geography

## Regras de negócio
- Abordagem ≠ Ocorrência
- Relacionamento entre pessoas = materializado em tabela própria com UPSERT
- IA nunca inventa fatos — apenas organiza dados existentes
- Cadastro de abordagem < 40 segundos
- Offline-first: IndexedDB + sync automático
- LGPD: criptografia, audit, soft delete, retenção controlada

## Variáveis de ambiente
Veja .env.example
```

---

> **Este documento é a fonte de verdade do Argus AI.** Toda decisão arquitetural, padrão de código, fluxo de desenvolvimento e política de dados está documentado aqui. Use-o como referência constante durante o desenvolvimento com Claude Code.
