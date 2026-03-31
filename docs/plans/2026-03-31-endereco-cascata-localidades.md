# Endereço em Cascata com Tabela Localidades — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir os campos de texto livre (bairro, cidade, UF) no cadastro de endereço por dropdowns/autocomplete em cascata com tabela `localidades` hierárquica, eliminando duplicatas.

**Architecture:** Nova tabela `localidades` (estado → cidade → bairro via parent_id). `enderecos_pessoa` ganha FKs opcionais. Backend expõe endpoint de autocomplete e criação. Frontend (pessoa-detalhe.js) substitui inputs texto por select + autocomplete Alpine.js.

**Tech Stack:** SQLAlchemy 2.0 async, Alembic, FastAPI, Pydantic v2, Alpine.js, fetch API

---

## Task 1: Model `Localidade`

**Files:**
- Create: `app/models/localidade.py`
- Modify: `app/models/__init__.py`

**Step 1: Criar o model**

```python
# app/models/localidade.py
"""Modelo de Localidade — hierarquia de estados, cidades e bairros.

Armazena localidades de forma hierárquica (estado → cidade → bairro)
para uso em endereços com autocomplete e sem duplicatas.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Localidade(Base, TimestampMixin):
    """Localidade geográfica hierárquica (estado, cidade ou bairro).

    Armazena estados, cidades e bairros em uma única tabela hierárquica
    com parent_id apontando para o nível acima. Estados não têm pai.
    A busca usa o campo `nome` normalizado (sem acento, minúsculas).

    Attributes:
        id: Identificador único.
        nome: Nome normalizado para busca (sem acento, minúsculas).
        nome_exibicao: Nome original para exibição ao usuário.
        tipo: Nível hierárquico — 'estado', 'cidade' ou 'bairro'.
        sigla: Sigla UF de 2 letras (apenas para estados).
        parent_id: FK para o nível acima (null para estados).
        ativo: Se a localidade está disponível para uso.
        parent: Relacionamento com localidade pai.
        filhos: Localidades filhas (cidades de um estado, bairros de uma cidade).
    """

    __tablename__ = "localidades"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), index=True)
    nome_exibicao: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(10))  # 'estado' | 'cidade' | 'bairro'
    sigla: Mapped[str | None] = mapped_column(String(2), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("localidades.id"), nullable=True, index=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    parent: Mapped["Localidade | None"] = relationship(
        "Localidade", back_populates="filhos", remote_side="Localidade.id"
    )
    filhos: Mapped[list["Localidade"]] = relationship(
        "Localidade", back_populates="parent"
    )
```

**Step 2: Registrar no `__init__.py`**

Abrir `app/models/__init__.py` e adicionar:
```python
from app.models.localidade import Localidade
```
(seguindo o padrão de imports existentes no arquivo)

**Step 3: Commit**

```bash
git add app/models/localidade.py app/models/__init__.py
git commit -m "feat(localidade): model Localidade hierárquico"
```

---

## Task 2: Migration — tabela `localidades` + FKs em `enderecos_pessoa` + seed estados

**Files:**
- Create: `alembic/versions/<hash>_localidades_e_fks_endereco.py`

**Step 1: Gerar migration**

```bash
make migrate msg="localidades_e_fks_endereco"
```

Isso cria um arquivo em `alembic/versions/`. Abra-o e substitua o conteúdo de `upgrade()` e `downgrade()` pelo seguinte:

**Step 2: Editar o arquivo de migration gerado**

```python
"""localidades e fks endereco

Revision ID: <gerado automaticamente>
Revises: <revisão anterior>
Create Date: <data gerada>
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "<gerado>"
down_revision = "<anterior>"
branch_labels = None
depends_on = None

ESTADOS = [
    ("acre", "Acre", "AC"),
    ("alagoas", "Alagoas", "AL"),
    ("amapa", "Amapá", "AP"),
    ("amazonas", "Amazonas", "AM"),
    ("bahia", "Bahia", "BA"),
    ("ceara", "Ceará", "CE"),
    ("distrito federal", "Distrito Federal", "DF"),
    ("espirito santo", "Espírito Santo", "ES"),
    ("goias", "Goiás", "GO"),
    ("maranhao", "Maranhão", "MA"),
    ("mato grosso", "Mato Grosso", "MT"),
    ("mato grosso do sul", "Mato Grosso do Sul", "MS"),
    ("minas gerais", "Minas Gerais", "MG"),
    ("para", "Pará", "PA"),
    ("paraiba", "Paraíba", "PB"),
    ("parana", "Paraná", "PR"),
    ("pernambuco", "Pernambuco", "PE"),
    ("piaui", "Piauí", "PI"),
    ("rio de janeiro", "Rio de Janeiro", "RJ"),
    ("rio grande do norte", "Rio Grande do Norte", "RN"),
    ("rio grande do sul", "Rio Grande do Sul", "RS"),
    ("rondonia", "Rondônia", "RO"),
    ("roraima", "Roraima", "RR"),
    ("santa catarina", "Santa Catarina", "SC"),
    ("sao paulo", "São Paulo", "SP"),
    ("sergipe", "Sergipe", "SE"),
    ("tocantins", "Tocantins", "TO"),
]


def upgrade() -> None:
    # Tabela localidades
    op.create_table(
        "localidades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("nome_exibicao", sa.String(200), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("sigla", sa.String(2), nullable=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("localidades.id"), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_localidades_nome", "localidades", ["nome"])
    op.create_index("ix_localidades_parent_id", "localidades", ["parent_id"])

    # FKs em enderecos_pessoa
    op.add_column("enderecos_pessoa", sa.Column("estado_id", sa.Integer(), nullable=True))
    op.add_column("enderecos_pessoa", sa.Column("cidade_id", sa.Integer(), nullable=True))
    op.add_column("enderecos_pessoa", sa.Column("bairro_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_enderecos_estado", "enderecos_pessoa", "localidades", ["estado_id"], ["id"])
    op.create_foreign_key("fk_enderecos_cidade", "enderecos_pessoa", "localidades", ["cidade_id"], ["id"])
    op.create_foreign_key("fk_enderecos_bairro", "enderecos_pessoa", "localidades", ["bairro_id"], ["id"])

    # Seed dos 27 estados
    localidades_table = sa.table(
        "localidades",
        sa.column("nome", sa.String),
        sa.column("nome_exibicao", sa.String),
        sa.column("tipo", sa.String),
        sa.column("sigla", sa.String),
        sa.column("parent_id", sa.Integer),
        sa.column("ativo", sa.Boolean),
    )
    op.bulk_insert(
        localidades_table,
        [
            {"nome": nome, "nome_exibicao": exibicao, "tipo": "estado", "sigla": sigla, "parent_id": None, "ativo": True}
            for nome, exibicao, sigla in ESTADOS
        ],
    )


def downgrade() -> None:
    op.drop_constraint("fk_enderecos_bairro", "enderecos_pessoa", type_="foreignkey")
    op.drop_constraint("fk_enderecos_cidade", "enderecos_pessoa", type_="foreignkey")
    op.drop_constraint("fk_enderecos_estado", "enderecos_pessoa", type_="foreignkey")
    op.drop_column("enderecos_pessoa", "bairro_id")
    op.drop_column("enderecos_pessoa", "cidade_id")
    op.drop_column("enderecos_pessoa", "estado_id")
    op.drop_index("ix_localidades_parent_id", "localidades")
    op.drop_index("ix_localidades_nome", "localidades")
    op.drop_table("localidades")
```

**Step 3: Rodar a migration**

```bash
make migrate msg="localidades_e_fks_endereco"
# depois de editar o arquivo gerado:
docker compose exec api alembic upgrade head
```

Ou localmente: `alembic upgrade head`

**Step 4: Verificar**

```bash
docker compose exec db psql -U argus -d argus -c "SELECT count(*) FROM localidades WHERE tipo='estado';"
```
Esperado: `27`

**Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat(migration): tabela localidades + FKs em enderecos_pessoa + seed 27 estados"
```

---

## Task 3: Atualizar model `EnderecoPessoa`

**Files:**
- Modify: `app/models/endereco.py`

**Step 1: Adicionar FKs ao model**

Adicionar os campos após `estado`:

```python
estado_id: Mapped[int | None] = mapped_column(
    ForeignKey("localidades.id"), nullable=True, index=True
)
cidade_id: Mapped[int | None] = mapped_column(
    ForeignKey("localidades.id"), nullable=True, index=True
)
bairro_id: Mapped[int | None] = mapped_column(
    ForeignKey("localidades.id"), nullable=True, index=True
)
```

Atualizar também a docstring da classe para incluir:
```
estado_id: FK para localidades (estado). Substitui o campo texto estado.
cidade_id: FK para localidades (cidade). Substitui o campo texto cidade.
bairro_id: FK para localidades (bairro). Substitui o campo texto bairro.
```

**Step 2: Commit**

```bash
git add app/models/endereco.py
git commit -m "feat(endereco): adicionar estado_id, cidade_id, bairro_id no model"
```

---

## Task 4: Schemas de Localidade

**Files:**
- Create: `app/schemas/localidade.py`

**Step 1: Criar schemas**

```python
# app/schemas/localidade.py
"""Schemas Pydantic para criação e leitura de Localidade.

Define estruturas de requisição e resposta para o endpoint
de autocomplete e criação de localidades (estado, cidade, bairro).
"""

from pydantic import BaseModel, Field, field_validator


class LocalidadeCreate(BaseModel):
    """Requisição de criação de nova localidade.

    Attributes:
        nome: Nome da localidade como digitado pelo usuário.
        tipo: Nível hierárquico — 'cidade' ou 'bairro' (estado não é criado via API).
        parent_id: ID da localidade pai (estado para cidade, cidade para bairro).
    """

    nome: str = Field(..., min_length=2, max_length=200)
    tipo: str = Field(..., pattern="^(cidade|bairro)$")
    parent_id: int


class LocalidadeRead(BaseModel):
    """Dados de leitura de uma localidade.

    Attributes:
        id: Identificador único.
        nome_exibicao: Nome original para exibição.
        tipo: Nível hierárquico.
        sigla: Sigla UF (apenas para estados).
        parent_id: ID da localidade pai.
    """

    id: int
    nome_exibicao: str
    tipo: str
    sigla: str | None = None
    parent_id: int | None = None

    model_config = {"from_attributes": True}
```

**Step 2: Commit**

```bash
git add app/schemas/localidade.py
git commit -m "feat(localidade): schemas LocalidadeCreate e LocalidadeRead"
```

---

## Task 5: Repository `LocalidadeRepository`

**Files:**
- Create: `app/repositories/localidade_repo.py`

**Step 1: Escrever o teste (TDD)**

```python
# tests/unit/test_localidade_repo.py
"""Testes unitários do LocalidadeRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.localidade import Localidade
from app.repositories.localidade_repo import LocalidadeRepository


@pytest.mark.asyncio
async def test_listar_estados(db_session: AsyncSession):
    """Deve retornar todos os estados ativos ordenados por nome_exibicao."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    assert len(estados) == 27
    assert all(e.tipo == "estado" for e in estados)
    nomes = [e.nome_exibicao for e in estados]
    assert nomes == sorted(nomes)


@pytest.mark.asyncio
async def test_autocomplete_cidade(db_session: AsyncSession):
    """Deve retornar cidades do estado filtradas pelo texto."""
    repo = LocalidadeRepository(db_session)
    # pegar id do estado SP
    estados = await repo.listar_estados()
    sp = next(e for e in estados if e.sigla == "SP")

    # criar cidade teste
    cidade = Localidade(
        nome="sao paulo",
        nome_exibicao="São Paulo",
        tipo="cidade",
        parent_id=sp.id,
    )
    db_session.add(cidade)
    await db_session.flush()

    resultados = await repo.autocomplete(tipo="cidade", parent_id=sp.id, q="sao")
    assert any(r.id == cidade.id for r in resultados)


@pytest.mark.asyncio
async def test_autocomplete_retorna_max_10(db_session: AsyncSession):
    """Deve retornar no máximo 10 resultados."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    sp = next(e for e in estados if e.sigla == "SP")

    for i in range(15):
        db_session.add(Localidade(
            nome=f"cidade {i:02d}",
            nome_exibicao=f"Cidade {i:02d}",
            tipo="cidade",
            parent_id=sp.id,
        ))
    await db_session.flush()

    resultados = await repo.autocomplete(tipo="cidade", parent_id=sp.id, q="cidade")
    assert len(resultados) <= 10


@pytest.mark.asyncio
async def test_buscar_por_nome_e_parent(db_session: AsyncSession):
    """Deve encontrar localidade exata pelo nome normalizado e parent_id."""
    repo = LocalidadeRepository(db_session)
    estados = await repo.listar_estados()
    rj = next(e for e in estados if e.sigla == "RJ")

    cidade = Localidade(
        nome="rio de janeiro",
        nome_exibicao="Rio de Janeiro",
        tipo="cidade",
        parent_id=rj.id,
    )
    db_session.add(cidade)
    await db_session.flush()

    encontrada = await repo.buscar_por_nome_e_parent("rio de janeiro", "cidade", rj.id)
    assert encontrada is not None
    assert encontrada.id == cidade.id
```

**Step 2: Rodar para confirmar que falha**

```bash
pytest tests/unit/test_localidade_repo.py -v
```
Esperado: `ImportError` ou `ModuleNotFoundError`

**Step 3: Implementar o repository**

```python
# app/repositories/localidade_repo.py
"""Repository de Localidade — queries de autocomplete e busca hierárquica.

Provê acesso aos dados de localidades (estados, cidades, bairros)
com suporte a autocomplete por texto e busca por nome normalizado.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.localidade import Localidade


class LocalidadeRepository:
    """Repository para operações de leitura e criação de localidades.

    Attributes:
        db: Sessão assíncrona do banco de dados.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Inicializa o repository com a sessão do banco.

        Args:
            db: Sessão assíncrona SQLAlchemy.
        """
        self.db = db

    async def listar_estados(self) -> list[Localidade]:
        """Retorna todos os estados ativos ordenados por nome de exibição.

        Returns:
            Lista de Localidade com tipo='estado', ordenada por nome_exibicao.
        """
        result = await self.db.execute(
            select(Localidade)
            .where(Localidade.tipo == "estado", Localidade.ativo == True)
            .order_by(Localidade.nome_exibicao)
        )
        return list(result.scalars().all())

    async def autocomplete(
        self,
        tipo: str,
        parent_id: int,
        q: str,
        limit: int = 10,
    ) -> list[Localidade]:
        """Retorna localidades filtradas por texto (autocomplete).

        Busca pelo campo `nome` normalizado com ILIKE para ignorar case.
        Filtra por tipo e parent_id para garantir hierarquia correta.

        Args:
            tipo: Tipo da localidade ('cidade' ou 'bairro').
            parent_id: ID da localidade pai (estado para cidades, cidade para bairros).
            q: Texto de busca (mínimo 2 chars recomendado).
            limit: Número máximo de resultados (padrão: 10).

        Returns:
            Lista de até `limit` localidades que correspondem ao texto.
        """
        result = await self.db.execute(
            select(Localidade)
            .where(
                Localidade.tipo == tipo,
                Localidade.parent_id == parent_id,
                Localidade.ativo == True,
                Localidade.nome.ilike(f"%{q}%"),
            )
            .order_by(Localidade.nome_exibicao)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def buscar_por_nome_e_parent(
        self,
        nome_normalizado: str,
        tipo: str,
        parent_id: int,
    ) -> Localidade | None:
        """Busca localidade exata por nome normalizado e parent (evita duplicatas).

        Args:
            nome_normalizado: Nome já normalizado (sem acento, minúsculas).
            tipo: Tipo da localidade ('cidade' ou 'bairro').
            parent_id: ID da localidade pai.

        Returns:
            Localidade encontrada ou None.
        """
        result = await self.db.execute(
            select(Localidade).where(
                Localidade.nome == nome_normalizado,
                Localidade.tipo == tipo,
                Localidade.parent_id == parent_id,
                Localidade.ativo == True,
            )
        )
        return result.scalar_one_or_none()

    async def get(self, localidade_id: int) -> Localidade | None:
        """Busca localidade por ID.

        Args:
            localidade_id: ID da localidade.

        Returns:
            Localidade encontrada ou None.
        """
        result = await self.db.execute(
            select(Localidade).where(
                Localidade.id == localidade_id,
                Localidade.ativo == True,
            )
        )
        return result.scalar_one_or_none()
```

**Step 4: Rodar testes**

```bash
pytest tests/unit/test_localidade_repo.py -v
```
Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/repositories/localidade_repo.py tests/unit/test_localidade_repo.py
git commit -m "feat(localidade): repository com autocomplete e busca por nome"
```

---

## Task 6: Service `LocalidadeService`

**Files:**
- Create: `app/services/localidade_service.py`

**Step 1: Escrever o teste**

```python
# tests/unit/test_localidade_service.py
"""Testes unitários do LocalidadeService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.localidade_service import LocalidadeService
from app.schemas.localidade import LocalidadeCreate
from app.core.exceptions import ConflitoDadosError


@pytest.mark.asyncio
async def test_criar_cidade_nova():
    """Deve criar cidade quando não existe duplicata."""
    db = AsyncMock()
    service = LocalidadeService(db)
    service.repo = AsyncMock()
    service.repo.buscar_por_nome_e_parent = AsyncMock(return_value=None)
    service.repo.get = AsyncMock(return_value=MagicMock(tipo="estado"))

    data = LocalidadeCreate(nome="Campinas", tipo="cidade", parent_id=1)
    result = await service.criar(data)

    db.add.assert_called_once()
    db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_criar_cidade_duplicata_levanta_erro():
    """Deve levantar ConflitoDadosError quando cidade já existe."""
    db = AsyncMock()
    service = LocalidadeService(db)
    service.repo = AsyncMock()
    service.repo.buscar_por_nome_e_parent = AsyncMock(return_value=MagicMock())
    service.repo.get = AsyncMock(return_value=MagicMock(tipo="estado"))

    data = LocalidadeCreate(nome="Campinas", tipo="cidade", parent_id=1)
    with pytest.raises(ConflitoDadosError):
        await service.criar(data)


@pytest.mark.asyncio
async def test_criar_cidade_sem_pai_estado_levanta_erro():
    """Deve levantar erro quando pai de cidade não é um estado."""
    db = AsyncMock()
    service = LocalidadeService(db)
    service.repo = AsyncMock()
    service.repo.buscar_por_nome_e_parent = AsyncMock(return_value=None)
    service.repo.get = AsyncMock(return_value=MagicMock(tipo="bairro"))  # pai inválido

    data = LocalidadeCreate(nome="Campinas", tipo="cidade", parent_id=99)
    with pytest.raises(Exception):
        await service.criar(data)
```

**Step 2: Rodar para confirmar falha**

```bash
pytest tests/unit/test_localidade_service.py -v
```
Esperado: `ImportError`

**Step 3: Implementar o service**

```python
# app/services/localidade_service.py
"""Service de Localidade — criação e busca com validação hierárquica.

Encapsula regras de negócio para localidades: impede duplicatas,
valida hierarquia (cidade precisa de estado pai, bairro precisa de cidade pai)
e normaliza nomes para busca.
"""

import unicodedata

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError
from app.models.localidade import Localidade
from app.repositories.localidade_repo import LocalidadeRepository
from app.schemas.localidade import LocalidadeCreate


def _normalizar(nome: str) -> str:
    """Normaliza texto para busca: remove acentos e converte para minúsculas.

    Args:
        nome: Texto original.

    Returns:
        Texto sem acentos em minúsculas.
    """
    return "".join(
        c for c in unicodedata.normalize("NFD", nome.strip().lower())
        if unicodedata.category(c) != "Mn"
    )


class LocalidadeService:
    """Service de Localidade com validação de hierarquia e deduplicação.

    Attributes:
        db: Sessão assíncrona do banco de dados.
        repo: Repository de localidades.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Inicializa o service com a sessão do banco.

        Args:
            db: Sessão assíncrona SQLAlchemy.
        """
        self.db = db
        self.repo = LocalidadeRepository(db)

    async def listar_estados(self) -> list[Localidade]:
        """Retorna todos os 27 estados ordenados por nome.

        Returns:
            Lista de estados.
        """
        return await self.repo.listar_estados()

    async def autocomplete(
        self,
        tipo: str,
        parent_id: int,
        q: str,
    ) -> list[Localidade]:
        """Autocomplete de cidades ou bairros filtrados por texto.

        Args:
            tipo: 'cidade' ou 'bairro'.
            parent_id: ID do estado (para cidades) ou cidade (para bairros).
            q: Texto digitado pelo usuário.

        Returns:
            Lista de até 10 localidades correspondentes.
        """
        return await self.repo.autocomplete(tipo=tipo, parent_id=parent_id, q=_normalizar(q))

    async def criar(self, data: LocalidadeCreate) -> Localidade:
        """Cria nova cidade ou bairro após validar hierarquia e duplicata.

        Normaliza o nome para busca. Valida que o parent_id corresponde
        ao tipo correto (cidade precisa de pai estado, bairro de pai cidade).
        Impede duplicatas pelo nome normalizado + parent_id + tipo.

        Args:
            data: Dados da nova localidade (nome, tipo, parent_id).

        Returns:
            Localidade criada.

        Raises:
            HTTPException 404: Quando parent_id não existe.
            HTTPException 400: Quando hierarquia é inválida.
            ConflitoDadosError: Quando já existe localidade com mesmo nome e pai.
        """
        nome_normalizado = _normalizar(data.nome)

        # Validar pai
        pai = await self.repo.get(data.parent_id)
        if not pai:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Localidade pai não encontrada.",
            )

        # Validar hierarquia
        if data.tipo == "cidade" and pai.tipo != "estado":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uma cidade deve ter um estado como pai.",
            )
        if data.tipo == "bairro" and pai.tipo != "cidade":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Um bairro deve ter uma cidade como pai.",
            )

        # Verificar duplicata
        existente = await self.repo.buscar_por_nome_e_parent(
            nome_normalizado, data.tipo, data.parent_id
        )
        if existente:
            raise ConflitoDadosError(
                f"{data.tipo.capitalize()} '{data.nome}' já cadastrada neste local."
            )

        localidade = Localidade(
            nome=nome_normalizado,
            nome_exibicao=data.nome.strip(),
            tipo=data.tipo,
            parent_id=data.parent_id,
        )
        self.db.add(localidade)
        await self.db.flush()
        return localidade
```

**Step 4: Rodar testes**

```bash
pytest tests/unit/test_localidade_service.py -v
```
Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/services/localidade_service.py tests/unit/test_localidade_service.py
git commit -m "feat(localidade): service com validação de hierarquia e deduplicação"
```

---

## Task 7: Router `/api/v1/localidades`

**Files:**
- Create: `app/api/v1/localidades.py`
- Modify: `app/api/v1/router.py`

**Step 1: Criar o router**

```python
# app/api/v1/localidades.py
"""Router de Localidades — autocomplete e criação de cidades/bairros.

Expõe endpoints para listar estados, buscar cidades/bairros por texto
(autocomplete) e cadastrar novas localidades sem duplicatas.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.usuario import Usuario
from app.schemas.localidade import LocalidadeCreate, LocalidadeRead
from app.services.localidade_service import LocalidadeService

router = APIRouter(prefix="/localidades", tags=["Localidades"])


@router.get("", response_model=list[LocalidadeRead])
async def listar_localidades(
    tipo: str = Query(..., pattern="^(estado|cidade|bairro)$"),
    parent_id: int | None = Query(None),
    q: str | None = Query(None, min_length=2),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[LocalidadeRead]:
    """Lista estados ou faz autocomplete de cidades/bairros.

    Para tipo='estado': retorna todos os 27 estados (ignora parent_id e q).
    Para tipo='cidade' ou 'bairro': retorna até 10 resultados filtrados por q.

    Args:
        tipo: Nível hierárquico — 'estado', 'cidade' ou 'bairro'.
        parent_id: ID da localidade pai (obrigatório para cidade e bairro).
        q: Texto de busca (obrigatório para cidade e bairro, mínimo 2 chars).
        db: Sessão do banco de dados.
        _: Usuário autenticado (apenas para proteger o endpoint).

    Returns:
        Lista de localidades correspondentes.

    Raises:
        HTTPException 400: Quando parent_id ou q ausentes para cidade/bairro.
    """
    from fastapi import HTTPException, status

    service = LocalidadeService(db)

    if tipo == "estado":
        return await service.listar_estados()

    if parent_id is None or q is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parent_id e q são obrigatórios para cidade e bairro.",
        )

    return await service.autocomplete(tipo=tipo, parent_id=parent_id, q=q)


@router.post("", response_model=LocalidadeRead, status_code=201)
async def criar_localidade(
    data: LocalidadeCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> LocalidadeRead:
    """Cadastra nova cidade ou bairro.

    Valida hierarquia e impede duplicatas. Normaliza o nome para busca.
    Estados não podem ser criados via API (são fixos no seed).

    Args:
        data: Dados da nova localidade (nome, tipo, parent_id).
        db: Sessão do banco de dados.
        _: Usuário autenticado.

    Returns:
        Localidade criada com id e nome_exibicao.

    Raises:
        HTTPException 404: Parent não encontrado.
        HTTPException 400: Hierarquia inválida.
        ConflitoDadosError 409: Duplicata detectada.
    """
    service = LocalidadeService(db)
    localidade = await service.criar(data)
    await db.commit()
    await db.refresh(localidade)
    return LocalidadeRead.model_validate(localidade)
```

**Step 2: Registrar no router.py**

Em `app/api/v1/router.py`, adicionar:
```python
from app.api.v1.localidades import router as localidades_router
# ...
api_router.include_router(localidades_router)
```

**Step 3: Teste de integração**

```python
# tests/integration/test_api_localidades.py
"""Testes de integração para o endpoint /api/v1/localidades."""

import pytest
from httpx import AsyncClient


class TestListarEstados:
    """Testes para GET /localidades?tipo=estado."""

    async def test_retorna_27_estados(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar os 27 estados brasileiros."""
        response = await client.get(
            "/api/v1/localidades?tipo=estado",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 27
        assert all(e["tipo"] == "estado" for e in data)

    async def test_sem_autenticacao_retorna_401(self, client: AsyncClient):
        """Deve retornar 401 sem token."""
        response = await client.get("/api/v1/localidades?tipo=estado")
        assert response.status_code == 401


class TestCriarLocalidade:
    """Testes para POST /localidades."""

    async def test_criar_cidade(self, client: AsyncClient, auth_headers: dict):
        """Deve criar cidade vinculada a um estado."""
        # Pegar id de SP
        estados = (await client.get(
            "/api/v1/localidades?tipo=estado", headers=auth_headers
        )).json()
        sp = next(e for e in estados if e["sigla"] == "SP")

        response = await client.post(
            "/api/v1/localidades",
            json={"nome": "Campinas", "tipo": "cidade", "parent_id": sp["id"]},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["nome_exibicao"] == "Campinas"

    async def test_criar_duplicata_retorna_409(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar 409 ao criar cidade duplicada."""
        estados = (await client.get(
            "/api/v1/localidades?tipo=estado", headers=auth_headers
        )).json()
        sp = next(e for e in estados if e["sigla"] == "SP")

        payload = {"nome": "São Paulo", "tipo": "cidade", "parent_id": sp["id"]}
        await client.post("/api/v1/localidades", json=payload, headers=auth_headers)
        response = await client.post("/api/v1/localidades", json=payload, headers=auth_headers)
        assert response.status_code == 409
```

**Step 4: Rodar testes**

```bash
pytest tests/integration/test_api_localidades.py -v
```
Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/api/v1/localidades.py app/api/v1/router.py tests/integration/test_api_localidades.py
git commit -m "feat(localidade): router GET/POST /api/v1/localidades"
```

---

## Task 8: Atualizar schemas de Endereço

**Files:**
- Modify: `app/schemas/pessoa.py`

**Step 1: Adicionar campos de ID nos schemas**

Em `EnderecoCreate` (linha ~90), adicionar após `estado`:
```python
estado_id: int | None = None
cidade_id: int | None = None
bairro_id: int | None = None
```

Atualizar a docstring para incluir:
```
estado_id: ID da localidade estado (opcional, preferido sobre campo texto).
cidade_id: ID da localidade cidade (opcional, preferido sobre campo texto).
bairro_id: ID da localidade bairro (opcional, preferido sobre campo texto).
```

Em `EnderecoUpdate` (linha ~114), adicionar os mesmos campos.

Em `EnderecoRead` (linha ~140), adicionar:
```python
estado_id: int | None = None
cidade_id: int | None = None
bairro_id: int | None = None
```

**Step 2: Commit**

```bash
git add app/schemas/pessoa.py
git commit -m "feat(endereco): adicionar estado_id, cidade_id, bairro_id nos schemas"
```

---

## Task 9: Atualizar `PessoaService` para salvar IDs

**Files:**
- Modify: `app/services/pessoa_service.py`

**Step 1: Localizar `adicionar_endereco` e `atualizar_endereco`**

Em `adicionar_endereco`, adicionar os campos ao construir `EnderecoPessoa`:
```python
endereco = EnderecoPessoa(
    pessoa_id=pessoa_id,
    endereco=data.endereco,
    bairro=data.bairro,
    cidade=data.cidade,
    estado=data.estado,
    estado_id=data.estado_id,
    cidade_id=data.cidade_id,
    bairro_id=data.bairro_id,
    localizacao=localizacao,
    data_inicio=data.data_inicio,
    data_fim=data.data_fim,
)
```

Em `atualizar_endereco`, no bloco de atualização de campos (onde usa `setattr` ou atribuição direta), adicionar:
```python
if data.estado_id is not None:
    endereco_obj.estado_id = data.estado_id
if data.cidade_id is not None:
    endereco_obj.cidade_id = data.cidade_id
if data.bairro_id is not None:
    endereco_obj.bairro_id = data.bairro_id
```

**Step 2: Rodar testes existentes**

```bash
pytest tests/unit/test_pessoa_service.py tests/integration/test_api_pessoas.py -v
```
Esperado: todos passando (nenhuma regressão — campos novos são nullable).

**Step 3: Commit**

```bash
git add app/services/pessoa_service.py
git commit -m "feat(endereco): salvar estado_id, cidade_id, bairro_id no service"
```

---

## Task 10: Frontend — substituir form de endereço em pessoa-detalhe.js

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

Esta é a task mais extensa. Dividida em 3 sub-steps: estado Alpine, HTML do form, e métodos.

### Step 1: Adicionar estado Alpine.js

Localizar (linha ~822):
```javascript
editEnderecoForm: { id: null, endereco: '', bairro: '', cidade: '', estado: '' },
```

Substituir por:
```javascript
editEnderecoForm: { id: null, endereco: '', data_inicio: null, data_fim: null },
enderecoEstadoId: null,
enderecoEstadoNome: '',
enderecoCidadeId: null,
enderecoCidadeTexto: '',
enderecoBairroId: null,
enderecoBairroTexto: '',
enderecoEstados: [],
enderecoCidadeSugestoes: [],
enderecoBairroSugestoes: [],
enderecoCidadeCadastrarNovo: false,
enderecoBairroCadastrarNovo: false,
```

### Step 2: Substituir HTML do form (linhas ~267-286)

Substituir o bloco de Bairro + Cidade + UF pelo seguinte HTML:

```html
<!-- Estado -->
<div>
  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Estado (UF)</label>
  <select x-model="enderecoEstadoId"
          @change="enderecoCidadeId=null; enderecoCidadeTexto=''; enderecoBairroId=null; enderecoBairroTexto=''; enderecoCidadeSugestoes=[]; enderecoBairroSugestoes=[];"
          style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;">
    <option value="">Selecione o estado...</option>
    <template x-for="est in enderecoEstados" :key="est.id">
      <option :value="est.id" x-text="est.sigla + ' — ' + est.nome_exibicao"></option>
    </template>
  </select>
</div>

<!-- Cidade -->
<div style="position: relative;">
  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Cidade</label>
  <input type="text"
         x-model="enderecoCidadeTexto"
         :disabled="!enderecoEstadoId"
         @input.debounce.400ms="buscarCidades()"
         @blur.debounce.200ms="enderecoCidadeSugestoes = []"
         placeholder="Digite para buscar..."
         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
  <!-- Sugestões cidade -->
  <div x-show="enderecoCidadeSugestoes.length > 0 || enderecoCidadeCadastrarNovo"
       style="position: absolute; z-index: 100; width: 100%; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-top: 2px; max-height: 200px; overflow-y: auto;">
    <template x-for="cidade in enderecoCidadeSugestoes" :key="cidade.id">
      <div @mousedown.prevent="selecionarCidade(cidade)"
           style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-text);"
           onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
        <span x-text="cidade.nome_exibicao"></span>
      </div>
    </template>
    <div x-show="enderecoCidadeCadastrarNovo"
         @mousedown.prevent="cadastrarNovaCidade()"
         style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-primary); border-top: 1px solid var(--color-border);"
         onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
      + Cadastrar "<span x-text="enderecoCidadeTexto"></span>" como nova cidade
    </div>
  </div>
</div>

<!-- Bairro -->
<div style="position: relative;">
  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Bairro</label>
  <input type="text"
         x-model="enderecoBairroTexto"
         :disabled="!enderecoCidadeId"
         @input.debounce.400ms="buscarBairros()"
         @blur.debounce.200ms="enderecoBairroSugestoes = []"
         placeholder="Digite para buscar..."
         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
  <!-- Sugestões bairro -->
  <div x-show="enderecoBairroSugestoes.length > 0 || enderecoBairroCadastrarNovo"
       style="position: absolute; z-index: 100; width: 100%; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-top: 2px; max-height: 200px; overflow-y: auto;">
    <template x-for="bairro in enderecoBairroSugestoes" :key="bairro.id">
      <div @mousedown.prevent="selecionarBairro(bairro)"
           style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-text);"
           onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
        <span x-text="bairro.nome_exibicao"></span>
      </div>
    </template>
    <div x-show="enderecoBairroCadastrarNovo"
         @mousedown.prevent="cadastrarNovoBairro()"
         style="padding: 0.5rem 0.75rem; cursor: pointer; font-size: 0.875rem; color: var(--color-primary); border-top: 1px solid var(--color-border);"
         onmouseover="this.style.background='var(--color-surface-hover)'" onmouseout="this.style.background=''">
      + Cadastrar "<span x-text="enderecoBairroTexto"></span>" como novo bairro
    </div>
  </div>
</div>
```

### Step 3: Adicionar métodos Alpine.js

Localizar o método `abrirModalNovoEndereco()` (linha ~1171) e, antes dele, adicionar os novos métodos:

```javascript
async carregarEstados() {
  if (this.enderecoEstados.length > 0) return; // cache simples
  try {
    this.enderecoEstados = await api.get('/localidades?tipo=estado');
  } catch (e) {
    console.error('Erro ao carregar estados', e);
  }
},

async buscarCidades() {
  const q = this.enderecoCidadeTexto.trim();
  if (!this.enderecoEstadoId || q.length < 2) {
    this.enderecoCidadeSugestoes = [];
    this.enderecoCidadeCadastrarNovo = false;
    return;
  }
  try {
    const resultado = await api.get(
      `/localidades?tipo=cidade&parent_id=${this.enderecoEstadoId}&q=${encodeURIComponent(q)}`
    );
    this.enderecoCidadeSugestoes = resultado;
    this.enderecoCidadeCadastrarNovo = resultado.length === 0;
  } catch (e) {
    console.error('Erro ao buscar cidades', e);
  }
},

async buscarBairros() {
  const q = this.enderecoBairroTexto.trim();
  if (!this.enderecoCidadeId || q.length < 2) {
    this.enderecoBairroSugestoes = [];
    this.enderecoBairroCadastrarNovo = false;
    return;
  }
  try {
    const resultado = await api.get(
      `/localidades?tipo=bairro&parent_id=${this.enderecoCidadeId}&q=${encodeURIComponent(q)}`
    );
    this.enderecoBairroSugestoes = resultado;
    this.enderecoBairroCadastrarNovo = resultado.length === 0;
  } catch (e) {
    console.error('Erro ao buscar bairros', e);
  }
},

selecionarCidade(cidade) {
  this.enderecoCidadeId = cidade.id;
  this.enderecoCidadeTexto = cidade.nome_exibicao;
  this.enderecoCidadeSugestoes = [];
  this.enderecoCidadeCadastrarNovo = false;
  // Limpar bairro ao trocar cidade
  this.enderecoBairroId = null;
  this.enderecoBairroTexto = '';
},

selecionarBairro(bairro) {
  this.enderecoBairroId = bairro.id;
  this.enderecoBairroTexto = bairro.nome_exibicao;
  this.enderecoBairroSugestoes = [];
  this.enderecoBairroCadastrarNovo = false;
},

async cadastrarNovaCidade() {
  const nome = this.enderecoCidadeTexto.trim();
  if (!nome || !this.enderecoEstadoId) return;
  try {
    const nova = await api.post('/localidades', {
      nome,
      tipo: 'cidade',
      parent_id: parseInt(this.enderecoEstadoId),
    });
    this.selecionarCidade(nova);
  } catch (e) {
    showToast('Erro ao cadastrar cidade', 'error');
  }
},

async cadastrarNovoBairro() {
  const nome = this.enderecoBairroTexto.trim();
  if (!nome || !this.enderecoCidadeId) return;
  try {
    const novo = await api.post('/localidades', {
      nome,
      tipo: 'bairro',
      parent_id: this.enderecoCidadeId,
    });
    this.selecionarBairro(novo);
  } catch (e) {
    showToast('Erro ao cadastrar bairro', 'error');
  }
},
```

### Step 4: Atualizar `abrirModalNovoEndereco()` e `abrirModalEditarEndereco()`

`abrirModalNovoEndereco` (linha ~1171):
```javascript
abrirModalNovoEndereco() {
  this.modoEndereco = 'criar';
  this.editEnderecoForm = { id: null, endereco: '' };
  this.enderecoEstadoId = null;
  this.enderecoCidadeId = null;
  this.enderecoCidadeTexto = '';
  this.enderecoBairroId = null;
  this.enderecoBairroTexto = '';
  this.carregarEstados();
  this.modalEditarEndereco = true;
},
```

`abrirModalEditarEndereco(end)` (linha ~1160) — preencher campos ao editar:
```javascript
abrirModalEditarEndereco(end) {
  this.modoEndereco = 'editar';
  this.editEnderecoForm = {
    id: end.id,
    endereco: end.endereco || '',
  };
  this.enderecoEstadoId = end.estado_id || null;
  this.enderecoCidadeId = end.cidade_id || null;
  this.enderecoCidadeTexto = end.cidade || '';
  this.enderecoBairroId = end.bairro_id || null;
  this.enderecoBairroTexto = end.bairro || '';
  this.carregarEstados();
  this.modalEditarEndereco = true;
},
```

### Step 5: Atualizar `salvarEditEndereco()` para enviar IDs

Localizar (linha ~1181) onde monta o `body`. Substituir por:
```javascript
const body = {
  endereco: f.endereco.trim(),
  estado_id: this.enderecoEstadoId ? parseInt(this.enderecoEstadoId) : null,
  cidade_id: this.enderecoCidadeId || null,
  bairro_id: this.enderecoBairroId || null,
};
```

### Step 6: Commit

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): endereço em cascata com autocomplete de cidade e bairro"
```

---

## Task 11: Testes finais e lint

**Step 1: Rodar todos os testes**

```bash
make test
```
Esperado: todos passando, sem regressões.

**Step 2: Rodar lint**

```bash
make lint
```
Corrigir quaisquer erros apontados pelo ruff ou mypy.

**Step 3: Commit de correções se houver**

```bash
git add -p
git commit -m "fix(localidade): corrigir warnings de lint"
```

---

## Resumo das tasks

| # | Task | Arquivos principais |
|---|------|---------------------|
| 1 | Model Localidade | `app/models/localidade.py` |
| 2 | Migration + seed estados | `alembic/versions/` |
| 3 | Atualizar EnderecoPessoa | `app/models/endereco.py` |
| 4 | Schemas Localidade | `app/schemas/localidade.py` |
| 5 | Repository LocalidadeRepository | `app/repositories/localidade_repo.py` |
| 6 | Service LocalidadeService | `app/services/localidade_service.py` |
| 7 | Router /api/v1/localidades | `app/api/v1/localidades.py`, `router.py` |
| 8 | Atualizar schemas EnderecoCreate/Update/Read | `app/schemas/pessoa.py` |
| 9 | Atualizar PessoaService | `app/services/pessoa_service.py` |
| 10 | Frontend autocomplete | `frontend/js/pages/pessoa-detalhe.js` |
| 11 | Testes finais + lint | — |
