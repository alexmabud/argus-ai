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

## Documentação com Docstrings

Todos os arquivos Python devem ter docstrings em **Google Style em português**. Siga este padrão:

### Módulo (topo do arquivo)
```python
"""Descrição breve do módulo em uma linha.

Descrição mais detalhada explicando propósito, responsabilidades principais
e contexto no projeto. Pode incluir exemplos de uso se necessário.
"""
```

### Classe
```python
class MinhaClasse:
    """Descrição breve da classe.

    Descrição detalhada explicando responsabilidades, padrões de projeto
    aplicados (soft delete, multi-tenancy, async, etc), e comportamentos
    importantes.

    Attributes:
        campo1: Descrição do campo1.
        campo2: Descrição do campo2 (incluir tipo especial se houver).
    """
```

### Função/Método
```python
def minha_funcao(arg1: str, arg2: int) -> bool:
    """Descrição breve em uma linha.

    Descrição detalhada do que a função faz, seu propósito e comportamento.
    Pode incluir notas técnicas sobre async, side effects, etc.

    Args:
        arg1: Descrição do argumento 1.
        arg2: Descrição do argumento 2.

    Returns:
        Descrição do valor retornado.

    Raises:
        MeuErro: Quando X acontecer.
        OutroErro: Quando Y acontecer.
    """
```

### Tipos Especiais
Ao documentar campos/parâmetros com tipos especiais, inclua informação técnica:
- **Vector(384)**: "Embedding multilíngue para busca semântica (SentenceTransformers)"
- **Vector(512)**: "Embedding facial para reconhecimento InsightFace"
- **Geography(POINT, 4326)**: "Coordenada geoespacial para busca por raio (PostGIS)"
- **Fernet**: "Campo criptografado com AES-256 (LGPD)"

### Cobertura Obrigatória
✓ Todos os módulos (arquivo)
✓ Todas as classes
✓ Todos os métodos públicos e protegidos
✓ Todos os routers/endpoints
✓ Funções de teste
✓ Fixtures pytest
✓ Scripts

### Idioma
- **Docstrings**: sempre em português
- **Tipo hints**: em inglês (str, int, bool, etc)
- **Nomes de variáveis**: em inglês

## Referência detalhada
Para detalhes de implementação, models, código e arquitetura completa, consulte o arquivo `ARGUS_AI_SPEC.md` na raiz do projeto.

## Variáveis de ambiente
Veja .env.example
