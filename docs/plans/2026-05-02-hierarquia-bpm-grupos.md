# Hierarquia BPM > Grupo — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduzir a entidade `Bpm` como nível hierárquico acima das equipes (Guarnicao), com navegação em 2 níveis na página de Gerenciar Usuários.

**Architecture:** Nova tabela `bpm` com FK em `guarnicoes.bpm_id` substituindo o campo de texto `unidade`. Migration com data-migration inline preserva todos os grupos existentes. Frontend usa 2 fileiras de abas: BPMs no topo, equipes dentro do BPM ativo.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, Alpine.js, pytest-asyncio.

**Design doc:** `docs/plans/2026-05-02-hierarquia-bpm-grupos-design.md`

---

## Task 1: Model `Bpm` + atualizar `Guarnicao`

**Files:**
- Create: `app/models/bpm.py`
- Modify: `app/models/guarnicao.py`
- Modify: `app/models/__init__.py`
- Modify: `tests/unit/test_models_guarnicao.py`

### Step 1: Atualizar test_models_guarnicao.py (testes vão falhar)

Substituir o conteúdo de `tests/unit/test_models_guarnicao.py`:

```python
"""Testes do model Guarnicao — campo isolamento_abordagens e FK bpm_id."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_default_false(db_session: AsyncSession, bpm):
    """Nova guarnição tem isolamento_abordagens=False por padrão."""
    g = Guarnicao(nome="GU 02", bpm_id=bpm.id, codigo="3BPM-3CIA-GU02")
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_persiste_true(db_session: AsyncSession, bpm):
    """isolamento_abordagens=True persiste corretamente."""
    g = Guarnicao(
        nome="GU 03",
        bpm_id=bpm.id,
        codigo="3BPM-3CIA-GU03",
        isolamento_abordagens=True,
    )
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is True


@pytest.mark.asyncio
async def test_guarnicao_carrega_bpm(db_session: AsyncSession, bpm):
    """Guarnicao carrega o relacionamento bpm automaticamente."""
    g = Guarnicao(nome="GU 04", bpm_id=bpm.id, codigo="3BPM-3CIA-GU04")
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.bpm_id == bpm.id
```

### Step 2: Rodar para confirmar que falha

```
pytest tests/unit/test_models_guarnicao.py -v
```

Esperado: `ImportError: cannot import name 'Bpm' from 'app.models.bpm'`

### Step 3: Criar `app/models/bpm.py`

```python
"""Model de BPM (Batalhão de Polícia Militar) — nível hierárquico acima das equipes.

Define a entidade que agrupa equipes (guarnições) por batalhão.
Um BPM contém N equipes. Usuário pertence a uma equipe, que pertence a um BPM.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Bpm(Base, TimestampMixin, SoftDeleteMixin):
    """Batalhão de Polícia Militar — agrupador de equipes.

    Representa a unidade administrativa superior que agrupa equipes
    operacionais. Exemplo: "14º BPM", "PMDF".

    Attributes:
        id: Identificador único.
        nome: Nome do batalhão (ex: "14º BPM"). Único no sistema.
        guarnicoes: Equipes pertencentes a este BPM.
    """

    __tablename__ = "bpm"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), unique=True)

    guarnicoes = relationship(
        "Guarnicao",
        back_populates="bpm",
        lazy="noload",
    )
```

### Step 4: Atualizar `app/models/guarnicao.py`

Substituir o conteúdo completo:

```python
"""Modelo de Guarnição (Equipe) — unidade operacional do sistema.

Define a entidade central de multi-tenancy, representando uma equipe policial
que contém membros e dados operacionais isolados. Cada equipe pertence a um BPM.

NOTA SOBRE NOMENCLATURA: no banco de dados e código interno, a entidade
chama-se "guarnicao" / "guarnicoes". No frontend e para o usuário final,
é exibida como "Equipe". Não há renomeação — apenas labels diferentes na UI.
Manutenções futuras devem manter o nome "guarnicao" no código.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Guarnicao(Base, TimestampMixin, SoftDeleteMixin):
    """Unidade operacional (Equipe) que isola dados entre guarnições.

    Representa uma equipe policial que usa o sistema. Pertence a um BPM
    (Batalhão de Polícia Militar). O campo isolamento_abordagens controla
    se os membros da equipe veem apenas as abordagens próprias (True) ou
    todas as abordagens do sistema (False, padrão).

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome descritivo da equipe (ex: "3ª Cia - GU 01").
        bpm_id: FK para o BPM ao qual esta equipe pertence.
        codigo: Código único para identificação (ex: "14BPM-3CIA-GU01").
        isolamento_abordagens: Se True, membros veem apenas abordagens da
            própria equipe. Se False (padrão), veem todas as abordagens.
        bpm: Relacionamento com o BPM pai.
        membros: Relacionamento com usuários (oficiais) da equipe.
    """

    __tablename__ = "guarnicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    bpm_id: Mapped[int] = mapped_column(ForeignKey("bpm.id"), index=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    isolamento_abordagens: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    bpm = relationship(
        "Bpm",
        back_populates="guarnicoes",
        lazy="selectin",
    )

    membros = relationship(
        "Usuario",
        back_populates="guarnicao",
        foreign_keys="Usuario.guarnicao_id",
        lazy="selectin",
    )
```

### Step 5: Atualizar `app/models/__init__.py`

Adicionar a linha após `from app.models.base import Base  # noqa: F401`:

```python
from app.models.bpm import Bpm  # noqa: F401
```

### Step 6: Adicionar fixture `bpm` ao conftest.py

Em `tests/conftest.py`, adicionar após os imports existentes:

```python
from app.models.bpm import Bpm
```

E adicionar fixture após `setup_db`:

```python
@pytest.fixture
async def bpm(db_session: AsyncSession) -> Bpm:
    """Fixture que cria um BPM de teste.

    Args:
        db_session: Sessão do banco de testes.

    Returns:
        Bpm: Objeto BPM com nome "3o BPM".
    """
    b = Bpm(nome="3o BPM")
    db_session.add(b)
    await db_session.flush()
    return b
```

E atualizar a fixture `guarnicao` (substituir completamente):

```python
@pytest.fixture
async def guarnicao(db_session: AsyncSession, bpm: Bpm) -> Guarnicao:
    """Fixture que cria uma guarnição de teste.

    Args:
        db_session: Sessão do banco de testes.
        bpm: Fixture de BPM ao qual a guarnição pertence.

    Returns:
        Guarnicao: Objeto de guarnição com valores padrão (3a Cia - GU 01).
    """
    g = Guarnicao(
        nome="3a Cia - GU 01",
        bpm_id=bpm.id,
        codigo="3BPM-3CIA-GU01",
    )
    db_session.add(g)
    await db_session.flush()
    return g
```

### Step 7: Rodar testes do model

```
pytest tests/unit/test_models_guarnicao.py -v
```

Esperado: todos os 3 testes passando.

### Step 8: Commit

```bash
git add app/models/bpm.py app/models/guarnicao.py app/models/__init__.py tests/conftest.py tests/unit/test_models_guarnicao.py
git commit -m "feat(models): adicionar Bpm e substituir unidade por bpm_id em Guarnicao"
```

---

## Task 2: Schemas `BpmRead`/`BpmCreate` + atualizar `EquipeRead`/`EquipeCreate`

**Files:**
- Create: `app/schemas/bpm.py`
- Modify: `app/schemas/auth.py`
- Modify: `tests/unit/test_schemas_equipe.py`

### Step 1: Atualizar `tests/unit/test_schemas_equipe.py` (vai falhar)

Substituir o conteúdo completo:

```python
"""Testes dos schemas de Equipe (Guarnicao) e BPM."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    EquipeCreate,
    EquipeRead,
    GuarnicaoRead,
    UsuarioAdminCreate,
    UsuarioAdminRead,
)
from app.schemas.bpm import BpmCreate, BpmRead


def test_bpm_create_valida_nome():
    """BpmCreate exige nome."""
    b = BpmCreate(nome="14º BPM")
    assert b.nome == "14º BPM"


def test_bpm_create_rejeita_nome_vazio():
    """BpmCreate rejeita nome vazio."""
    with pytest.raises(ValidationError):
        BpmCreate(nome="")


def test_bpm_read_campos():
    """BpmRead expõe id e nome."""
    b = BpmRead(id=1, nome="14º BPM")
    assert b.id == 1
    assert b.nome == "14º BPM"


def test_equipe_create_valida_campos():
    """EquipeCreate exige nome e bpm_id."""
    e = EquipeCreate(nome="3a Cia - GU 01", bpm_id=1)
    assert e.nome == "3a Cia - GU 01"
    assert e.bpm_id == 1


def test_equipe_create_rejeita_nome_vazio():
    """EquipeCreate rejeita nome vazio."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="", bpm_id=1)


def test_equipe_create_rejeita_bpm_id_ausente():
    """EquipeCreate rejeita bpm_id ausente."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="GU 01")


def test_equipe_read_inclui_bpm_e_isolamento():
    """EquipeRead expõe bpm (objeto) e isolamento_abordagens."""
    bpm_obj = BpmRead(id=1, nome="14º BPM")
    e = EquipeRead(
        id=1,
        nome="GU 01",
        bpm_id=1,
        bpm=bpm_obj,
        codigo="14BPM-GU01",
        isolamento_abordagens=True,
    )
    assert e.isolamento_abordagens is True
    assert e.bpm.nome == "14º BPM"


def test_usuario_admin_create_aceita_guarnicao_id_opcional():
    """UsuarioAdminCreate aceita guarnicao_id opcional (None = sem equipe)."""
    u1 = UsuarioAdminCreate(matricula="PM001")
    assert u1.guarnicao_id is None
    u2 = UsuarioAdminCreate(matricula="PM002", guarnicao_id=5)
    assert u2.guarnicao_id == 5


def test_usuario_admin_read_aceita_guarnicao_id_none():
    """UsuarioAdminRead permite guarnicao_id None (usuário sem equipe)."""
    u = UsuarioAdminRead(
        id=1,
        nome="Soldado",
        matricula="PM001",
        is_admin=False,
        ativo=True,
        tem_sessao=False,
        guarnicao_id=None,
    )
    assert u.guarnicao_id is None
```

### Step 2: Rodar para confirmar que falha

```
pytest tests/unit/test_schemas_equipe.py -v
```

Esperado: `ModuleNotFoundError: No module named 'app.schemas.bpm'`

### Step 3: Criar `app/schemas/bpm.py`

```python
"""Schemas Pydantic para BPM (Batalhão de Polícia Militar).

Define estruturas de requisição e resposta para listagem e criação de BPMs.
"""

from pydantic import BaseModel, Field


class BpmRead(BaseModel):
    """Dados de leitura de um BPM.

    Attributes:
        id: Identificador único do BPM.
        nome: Nome do batalhão (ex: "14º BPM").
    """

    id: int
    nome: str

    model_config = {"from_attributes": True}


class BpmCreate(BaseModel):
    """Dados para criação de novo BPM.

    Attributes:
        nome: Nome do batalhão (1-200 caracteres).
    """

    nome: str = Field(..., min_length=1, max_length=200)
```

### Step 4: Atualizar `app/schemas/auth.py` — GuarnicaoRead e EquipeCreate

Localizar a classe `GuarnicaoRead` e substituir:

```python
# ANTES:
class GuarnicaoRead(BaseModel):
    id: int
    nome: str
    unidade: str
    codigo: str
    isolamento_abordagens: bool = False

    model_config = {"from_attributes": True}
```

Por:

```python
# DEPOIS:
class GuarnicaoRead(BaseModel):
    """Dados públicos de uma guarnição (Equipe).

    Representação de leitura. A UI exibe como "Equipe" — internamente
    a entidade chama-se "guarnicao". Inclui o BPM pai e o campo
    isolamento_abordagens para controle de visibilidade de abordagens.

    Attributes:
        id: Identificador único da guarnição.
        nome: Nome da equipe (ex: "3ª Cia - GU 01").
        bpm_id: ID do BPM ao qual pertence.
        bpm: Dados do BPM pai.
        codigo: Código interno único.
        isolamento_abordagens: Se True, membros veem apenas as abordagens
            da própria equipe. Se False (padrão), veem todas.
    """

    id: int
    nome: str
    bpm_id: int
    bpm: "BpmRead"
    codigo: str
    isolamento_abordagens: bool = False

    model_config = {"from_attributes": True}
```

E adicionar o import de `BpmRead` no topo do arquivo `app/schemas/auth.py`:

```python
from app.schemas.bpm import BpmRead
```

Localizar a classe `EquipeCreate` e substituir:

```python
# ANTES:
class EquipeCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=200)
    unidade: str = Field(..., min_length=1, max_length=200)
```

Por:

```python
# DEPOIS:
class EquipeCreate(BaseModel):
    """Dados para criação de nova equipe (guarnição) pelo admin.

    O código é gerado automaticamente pelo serviço a partir do nome e BPM.

    Attributes:
        nome: Nome descritivo da equipe (1-200 caracteres).
        bpm_id: ID do BPM ao qual a equipe pertencerá.
    """

    nome: str = Field(..., min_length=1, max_length=200)
    bpm_id: int = Field(..., ge=1)
```

### Step 5: Rodar testes dos schemas

```
pytest tests/unit/test_schemas_equipe.py -v
```

Esperado: todos os testes passando.

### Step 6: Commit

```bash
git add app/schemas/bpm.py app/schemas/auth.py tests/unit/test_schemas_equipe.py
git commit -m "feat(schemas): BpmRead/BpmCreate + substituir unidade por bpm_id em EquipeCreate/EquipeRead"
```

---

## Task 3: Migration Alembic — criar `bpm`, migrar dados, remover `unidade`

**Files:**
- Create: `alembic/versions/<hash>_add_bpm_table_and_bpm_id_to_guarnicoes.py`

### Step 1: Gerar arquivo base da migration

```
make migrate msg="add_bpm_table_and_bpm_id_to_guarnicoes"
```

Isso cria `alembic/versions/<novo_hash>_add_bpm_table_and_bpm_id_to_guarnicoes.py`.

### Step 2: Substituir o conteúdo do arquivo gerado

Abrir o arquivo gerado e substituir as funções `upgrade()` e `downgrade()` pelo código abaixo (manter o cabeçalho gerado automaticamente — revision, down_revision, etc.):

```python
def upgrade() -> None:
    """Cria tabela bpm, migra dados de unidade para bpm_id, remove coluna unidade."""
    # 1. Criar tabela bpm
    op.create_table(
        "bpm",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("desativado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["desativado_por_id"], ["usuarios.id"], name="fk_bpm_desativado_por_id", use_alter=True),
        sa.Column("desativado_por_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )

    # 2. Inserir BPMs existentes (derivados dos valores únicos de guarnicoes.unidade)
    op.execute("""
        INSERT INTO bpm (nome, ativo, criado_em, atualizado_em)
        SELECT DISTINCT unidade, true, now(), now()
        FROM guarnicoes
        WHERE ativo = true AND unidade IS NOT NULL AND unidade != ''
    """)

    # 3. Adicionar bpm_id como nullable (para preencher antes de tornar NOT NULL)
    op.add_column("guarnicoes", sa.Column("bpm_id", sa.Integer(), nullable=True))

    # 4. Criar FK constraint
    op.create_foreign_key(
        "fk_guarnicoes_bpm_id",
        "guarnicoes", "bpm",
        ["bpm_id"], ["id"],
    )

    # 5. Mapear guarnicoes para seus BPMs pelo valor de unidade
    op.execute("""
        UPDATE guarnicoes g
        SET bpm_id = b.id
        FROM bpm b
        WHERE b.nome = g.unidade
    """)

    # 6. Criar index em bpm_id
    op.create_index("ix_guarnicoes_bpm_id", "guarnicoes", ["bpm_id"])

    # 7. Tornar bpm_id NOT NULL
    op.alter_column("guarnicoes", "bpm_id", nullable=False)

    # 8. Remover coluna unidade
    op.drop_column("guarnicoes", "unidade")


def downgrade() -> None:
    """Reverte: restaura coluna unidade, remove bpm_id, remove tabela bpm."""
    # Recriar coluna unidade como nullable primeiro
    op.add_column("guarnicoes", sa.Column("unidade", sa.String(200), nullable=True))

    # Restaurar valores de unidade a partir do bpm
    op.execute("""
        UPDATE guarnicoes g
        SET unidade = b.nome
        FROM bpm b
        WHERE b.id = g.bpm_id
    """)

    # Tornar unidade NOT NULL
    op.alter_column("guarnicoes", "unidade", nullable=False)

    # Remover bpm_id
    op.drop_index("ix_guarnicoes_bpm_id", table_name="guarnicoes")
    op.drop_constraint("fk_guarnicoes_bpm_id", "guarnicoes", type_="foreignkey")
    op.drop_column("guarnicoes", "bpm_id")

    # Remover tabela bpm
    op.drop_table("bpm")
```

> **Nota:** o `make migrate` auto-detecta o diff do modelo. Se gerar código extra (como `op.drop_column("guarnicoes", "unidade")` automático), **remova** o código auto-gerado e use apenas o código acima. O arquivo final deve ter SOMENTE `upgrade()` e `downgrade()` como definidos acima.

### Step 3: Commit

```bash
git add alembic/versions/
git commit -m "feat(migration): criar tabela bpm, migrar unidade para bpm_id, remover coluna unidade"
```

---

## Task 4: `BpmService` + testes unitários

**Files:**
- Create: `app/services/bpm_service.py`
- Create: `tests/unit/test_bpm_service.py`

### Step 1: Escrever testes em `tests/unit/test_bpm_service.py` (vai falhar)

```python
"""Testes de unidade do BpmService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError
from app.services.bpm_service import BpmService


@pytest.mark.asyncio
async def test_listar_bpms_retorna_todos_ativos(db_session: AsyncSession, bpm):
    """listar_bpms retorna todos os BPMs ativos."""
    service = BpmService(db_session)
    bpms = await service.listar_bpms()
    assert len(bpms) >= 1
    assert any(b.id == bpm.id for b in bpms)


@pytest.mark.asyncio
async def test_criar_bpm_sucesso(db_session: AsyncSession, usuario):
    """criar_bpm cria BPM com nome fornecido."""
    service = BpmService(db_session)
    b = await service.criar_bpm(nome="14º BPM", admin_id=usuario.id)
    assert b.id is not None
    assert b.nome == "14º BPM"
    assert b.ativo is True


@pytest.mark.asyncio
async def test_criar_bpm_nome_duplicado_falha(db_session: AsyncSession, bpm, usuario):
    """criar_bpm rejeita nome duplicado."""
    service = BpmService(db_session)
    with pytest.raises(ConflitoDadosError):
        await service.criar_bpm(nome=bpm.nome, admin_id=usuario.id)
```

### Step 2: Rodar para confirmar que falha

```
pytest tests/unit/test_bpm_service.py -v
```

Esperado: `ImportError: cannot import name 'BpmService' from 'app.services.bpm_service'`

### Step 3: Criar `app/services/bpm_service.py`

```python
"""Serviço de gestão de BPMs (Batalhões de Polícia Militar).

Implementa listagem e criação de BPMs. Sem dependências FastAPI.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError
from app.models.bpm import Bpm
from app.services.audit_service import AuditService


class BpmService:
    """Serviço de gestão de BPMs para uso do administrador.

    Cobre listagem e criação de BPMs. Registra mutações via AuditService.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        audit: Serviço de auditoria (LGPD).
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.audit = AuditService(db)

    async def listar_bpms(self) -> list[Bpm]:
        """Lista todos os BPMs ativos, ordenados por nome.

        Returns:
            Lista de Bpm com ativo=True.
        """
        result = await self.db.execute(
            select(Bpm)
            .where(Bpm.ativo == True)  # noqa: E712
            .order_by(Bpm.nome)
        )
        return list(result.scalars().all())

    async def criar_bpm(self, nome: str, admin_id: int) -> Bpm:
        """Cria novo BPM com o nome fornecido.

        Args:
            nome: Nome do BPM (ex: "14º BPM").
            admin_id: ID do admin que está criando (auditoria).

        Returns:
            BPM criado com ID atribuído.

        Raises:
            ConflitoDadosError: Se já existe BPM ativo com o mesmo nome.
        """
        existing = await self.db.execute(
            select(Bpm).where(
                Bpm.nome == nome,
                Bpm.ativo == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise ConflitoDadosError("Já existe um BPM com este nome")

        bpm = Bpm(nome=nome)
        self.db.add(bpm)
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="CREATE",
            recurso="bpm",
            recurso_id=bpm.id,
            detalhes={"nome": nome},
        )
        return bpm
```

### Step 4: Rodar testes

```
pytest tests/unit/test_bpm_service.py -v
```

Esperado: todos os 3 testes passando.

### Step 5: Commit

```bash
git add app/services/bpm_service.py tests/unit/test_bpm_service.py
git commit -m "feat(services): BpmService com listar e criar BPM"
```

---

## Task 5: Atualizar `EquipeService` (substituir `unidade` por `bpm_id`)

**Files:**
- Modify: `app/services/equipe_service.py`
- Modify: `tests/unit/test_equipe_service.py`

### Step 1: Atualizar `tests/unit/test_equipe_service.py` (vai falhar)

Substituir o conteúdo completo:

```python
"""Testes de unidade do EquipeService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.services.equipe_service import EquipeService


@pytest.mark.asyncio
async def test_listar_equipes_retorna_todas_ativas(db_session: AsyncSession, guarnicao):
    """listar_equipes retorna todas as equipes ativas."""
    service = EquipeService(db_session)
    equipes = await service.listar_equipes()
    assert len(equipes) >= 1
    assert any(e.id == guarnicao.id for e in equipes)


@pytest.mark.asyncio
async def test_criar_equipe_gera_codigo(db_session: AsyncSession, bpm, usuario):
    """criar_equipe gera código único automaticamente."""
    service = EquipeService(db_session)
    e = await service.criar_equipe(nome="3a Cia - GU 02", bpm_id=bpm.id, admin_id=usuario.id)
    assert e.id is not None
    assert e.codigo
    assert e.nome == "3a Cia - GU 02"
    assert e.bpm_id == bpm.id
    assert e.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_criar_equipe_nome_duplicado_falha(db_session: AsyncSession, guarnicao, bpm, usuario):
    """criar_equipe rejeita nome duplicado entre ativas."""
    service = EquipeService(db_session)
    with pytest.raises(ConflitoDadosError):
        await service.criar_equipe(
            nome=guarnicao.nome, bpm_id=bpm.id, admin_id=usuario.id
        )


@pytest.mark.asyncio
async def test_toggle_isolamento_alterna_valor(db_session: AsyncSession, guarnicao, usuario):
    """toggle_isolamento alterna o valor."""
    service = EquipeService(db_session)
    assert guarnicao.isolamento_abordagens is False
    e1 = await service.toggle_isolamento(guarnicao.id, valor=True, admin_id=usuario.id)
    assert e1.isolamento_abordagens is True
    e2 = await service.toggle_isolamento(guarnicao.id, valor=False, admin_id=usuario.id)
    assert e2.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_toggle_isolamento_inexistente_falha(db_session: AsyncSession, usuario):
    """toggle_isolamento em equipe inexistente lança NaoEncontradoError."""
    service = EquipeService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.toggle_isolamento(999_999, valor=True, admin_id=usuario.id)
```

### Step 2: Rodar para confirmar que falha

```
pytest tests/unit/test_equipe_service.py -v
```

Esperado: `TypeError: criar_equipe() got an unexpected keyword argument 'bpm_id'`

### Step 3: Atualizar `app/services/equipe_service.py`

Substituir o conteúdo completo:

```python
"""Serviço de gestão de equipes (guarnições) pelo administrador.

Implementa criação de novas equipes com código gerado automaticamente,
listagem e alternância do toggle de isolamento de abordagens.
Sem dependências FastAPI.

NOTA: "Equipe" na UI = "Guarnicao" no código/banco.
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.services.audit_service import AuditService


def _gerar_codigo(nome: str, bpm_nome: str) -> str:
    """Gera código alfanumérico a partir de nome e BPM.

    Remove caracteres não alfanuméricos, normaliza para upper-case e trunca
    em 50 chars. Ex: ("3ª Cia - GU 01", "14º BPM") -> "14BPM-3CIAGU01".

    Args:
        nome: Nome da equipe.
        bpm_nome: Nome do BPM pai.

    Returns:
        Código alfanumérico em upper-case (máx 50 chars).
    """

    def _slug(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", s).upper()

    base = f"{_slug(bpm_nome)}-{_slug(nome)}"
    return base[:50] or "EQUIPE"


class EquipeService:
    """Serviço de gestão de equipes (guarnições) para uso do administrador.

    Cobre criação com código automático, listagem e toggle de isolamento
    de abordagens por equipe. Registra todas as mutações via AuditService.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        audit: Serviço de auditoria (LGPD).
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.audit = AuditService(db)

    async def listar_equipes(self) -> list[Guarnicao]:
        """Lista todas as equipes ativas, ordenadas por nome.

        Returns:
            Lista de Guarnicao com ativo=True.
        """
        result = await self.db.execute(
            select(Guarnicao)
            .where(Guarnicao.ativo == True)  # noqa: E712
            .order_by(Guarnicao.nome)
        )
        return list(result.scalars().all())

    async def criar_equipe(self, nome: str, bpm_id: int, admin_id: int) -> Guarnicao:
        """Cria nova equipe com código gerado automaticamente.

        Busca o BPM pelo ID para gerar o código. Se o código gerado colidir
        com um existente, adiciona sufixo numérico (-2, -3, ...) até encontrar
        um código único.

        Args:
            nome: Nome descritivo da equipe.
            bpm_id: ID do BPM ao qual a equipe pertencerá.
            admin_id: ID do admin que está criando (auditoria).

        Returns:
            Equipe criada com ID atribuído.

        Raises:
            ConflitoDadosError: Se já existe equipe ativa com o mesmo nome.
            NaoEncontradoError: Se o BPM não existe ou está inativo.
        """
        bpm_result = await self.db.execute(
            select(Bpm).where(Bpm.id == bpm_id, Bpm.ativo == True)  # noqa: E712
        )
        bpm = bpm_result.scalar_one_or_none()
        if not bpm:
            raise NaoEncontradoError("BPM não encontrado")

        existing = await self.db.execute(
            select(Guarnicao).where(
                Guarnicao.nome == nome,
                Guarnicao.ativo == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise ConflitoDadosError("Já existe uma equipe ativa com este nome")

        codigo_base = _gerar_codigo(nome, bpm.nome)
        codigo = codigo_base
        i = 2
        while True:
            exists = await self.db.execute(select(Guarnicao.id).where(Guarnicao.codigo == codigo))
            if exists.scalar_one_or_none() is None:
                break
            codigo = f"{codigo_base[:48]}-{i}"
            i += 1

        equipe = Guarnicao(nome=nome, bpm_id=bpm_id, codigo=codigo)
        self.db.add(equipe)
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="CREATE",
            recurso="guarnicao",
            recurso_id=equipe.id,
            detalhes={"nome": nome, "bpm_id": bpm_id},
        )
        return equipe

    async def toggle_isolamento(self, guarnicao_id: int, valor: bool, admin_id: int) -> Guarnicao:
        """Define o valor de isolamento_abordagens da equipe.

        Args:
            guarnicao_id: ID da equipe.
            valor: True ativa o isolamento, False desativa.
            admin_id: ID do admin (auditoria).

        Returns:
            Equipe atualizada com o novo valor.

        Raises:
            NaoEncontradoError: Se a equipe não existe ou está inativa.
        """
        result = await self.db.execute(
            select(Guarnicao).where(
                Guarnicao.id == guarnicao_id,
                Guarnicao.ativo == True,  # noqa: E712
            )
        )
        equipe = result.scalar_one_or_none()
        if not equipe:
            raise NaoEncontradoError("Equipe não encontrada")

        equipe.isolamento_abordagens = valor
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="guarnicao",
            recurso_id=equipe.id,
            detalhes={"acao": "toggle_isolamento", "valor": valor},
        )
        return equipe
```

### Step 4: Rodar testes

```
pytest tests/unit/test_equipe_service.py -v
```

Esperado: todos os 5 testes passando.

### Step 5: Commit

```bash
git add app/services/equipe_service.py tests/unit/test_equipe_service.py
git commit -m "feat(services): EquipeService usa bpm_id em vez de unidade"
```

---

## Task 6: API endpoints — BPM + atualizar endpoints de equipe

**Files:**
- Modify: `app/api/v1/admin.py`
- Modify: `tests/integration/test_api_equipes.py`
- Create: `tests/integration/test_api_bpms.py`

### Step 1: Escrever `tests/integration/test_api_bpms.py` (vai falhar)

```python
"""Testes do router /admin/bpms — listar e criar BPMs."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.usuario import Usuario


@pytest.fixture
async def admin_bpm(db_session, guarnicao):
    """Admin para testes de BPM."""
    u = Usuario(
        nome="Admin BPM",
        matricula="ADMBPM001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        session_id="admin-bpm-session",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_bpm_headers(admin_bpm):
    """Headers de autenticação do admin de BPMs."""
    token = criar_access_token(
        {
            "sub": str(admin_bpm.id),
            "guarnicao_id": admin_bpm.guarnicao_id,
            "sid": admin_bpm.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_listar_bpms_retorna_lista(client: AsyncClient, admin_bpm_headers, bpm):
    """GET /admin/bpms retorna lista com BPMs ativos."""
    response = await client.get("/api/v1/admin/bpms", headers=admin_bpm_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(b["id"] == bpm.id for b in data)


@pytest.mark.asyncio
async def test_criar_bpm_201(client: AsyncClient, admin_bpm_headers):
    """POST /admin/bpms cria novo BPM e retorna 201."""
    response = await client.post(
        "/api/v1/admin/bpms",
        json={"nome": "14º BPM"},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "14º BPM"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_criar_bpm_sem_admin_403(client: AsyncClient, auth_headers):
    """Usuário comum recebe 403 ao tentar criar BPM."""
    response = await client.post(
        "/api/v1/admin/bpms",
        json={"nome": "Novo BPM"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_criar_bpm_nome_duplicado_409(client: AsyncClient, admin_bpm_headers, bpm):
    """POST /admin/bpms rejeita nome duplicado com 409."""
    response = await client.post(
        "/api/v1/admin/bpms",
        json={"nome": bpm.nome},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 409
```

### Step 2: Atualizar `tests/integration/test_api_equipes.py`

Substituir o conteúdo completo:

```python
"""Testes do router /admin/equipes — listar, criar, toggle isolamento."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.usuario import Usuario


@pytest.fixture
async def admin_eq(db_session, guarnicao):
    """Admin com sessão ativa para testes de equipes."""
    u = Usuario(
        nome="Admin Equipes",
        matricula="ADMEQ001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        session_id="admin-eq-session",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_eq_headers(admin_eq):
    """Headers de autenticação do admin de equipes."""
    token = criar_access_token(
        {
            "sub": str(admin_eq.id),
            "guarnicao_id": admin_eq.guarnicao_id,
            "sid": admin_eq.session_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_listar_equipes_retorna_lista(client: AsyncClient, admin_eq_headers, guarnicao):
    """GET /admin/equipes retorna todas as equipes ativas com bpm aninhado."""
    response = await client.get("/api/v1/admin/equipes", headers=admin_eq_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(e["id"] == guarnicao.id for e in data)
    assert "isolamento_abordagens" in data[0]
    assert "bpm" in data[0]
    assert "bpm_id" in data[0]


@pytest.mark.asyncio
async def test_criar_equipe_201(client: AsyncClient, admin_eq_headers, bpm):
    """POST /admin/equipes cria nova equipe e retorna 201."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": "GU 50", "bpm_id": bpm.id},
        headers=admin_eq_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "GU 50"
    assert data["bpm_id"] == bpm.id
    assert data["bpm"]["nome"] == bpm.nome
    assert data["codigo"]
    assert data["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_criar_equipe_nome_duplicado_409(client: AsyncClient, admin_eq_headers, guarnicao):
    """POST /admin/equipes rejeita nome duplicado com 409."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": guarnicao.nome, "bpm_id": guarnicao.bpm_id},
        headers=admin_eq_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_criar_equipe_sem_admin_403(client: AsyncClient, auth_headers, bpm):
    """Usuário comum recebe 403 ao tentar criar equipe."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": "X", "bpm_id": bpm.id},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_toggle_isolamento_alterna(client: AsyncClient, admin_eq_headers, guarnicao):
    """PATCH /admin/equipes/{id}/toggle-isolamento alterna o valor."""
    r1 = await client.patch(
        f"/api/v1/admin/equipes/{guarnicao.id}/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_eq_headers,
    )
    assert r1.status_code == 200
    assert r1.json()["isolamento_abordagens"] is True

    r2 = await client.patch(
        f"/api/v1/admin/equipes/{guarnicao.id}/toggle-isolamento",
        json={"isolamento_abordagens": False},
        headers=admin_eq_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_toggle_isolamento_inexistente_404(client: AsyncClient, admin_eq_headers):
    """PATCH em equipe inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/admin/equipes/999999/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_eq_headers,
    )
    assert response.status_code == 404
```

### Step 3: Rodar testes para confirmar que falham

```
pytest tests/integration/test_api_bpms.py tests/integration/test_api_equipes.py -v
```

Esperado: falhas por `AttributeError` no router (ainda usa `unidade`) e rotas de BPM inexistentes.

### Step 4: Atualizar `app/api/v1/admin.py`

**4a. Adicionar imports no topo:**

Após as importações existentes, adicionar:

```python
from app.schemas.bpm import BpmCreate, BpmRead
from app.services.bpm_service import BpmService
```

**4b. Adicionar endpoints de BPM** (antes do endpoint `listar_equipes`):

```python
@router.get("/bpms", response_model=list[BpmRead])
@limiter.limit("30/minute")
async def listar_bpms(
    request: Request,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[BpmRead]:
    """Lista todos os BPMs ativos.

    Args:
        request: Requisição HTTP.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Lista de BpmRead ordenada por nome.

    Status Code:
        200: Lista retornada com sucesso.
        403: Não é administrador.
    """
    service = BpmService(db)
    bpms = await service.listar_bpms()
    return [BpmRead.model_validate(b) for b in bpms]


@router.post("/bpms", response_model=BpmRead, status_code=201)
@limiter.limit("10/minute")
async def criar_bpm(
    request: Request,
    data: BpmCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BpmRead:
    """Cria novo BPM.

    Args:
        request: Requisição HTTP.
        data: Nome do BPM.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        BpmRead com ID atribuído.

    Raises:
        HTTPException: 409 se nome já existe.

    Status Code:
        201: BPM criado com sucesso.
        403: Não é administrador.
        409: Nome de BPM já cadastrado.
    """
    service = BpmService(db)
    try:
        bpm = await service.criar_bpm(nome=data.nome, admin_id=admin.id)
    except ConflitoDadosError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    await db.commit()
    return BpmRead.model_validate(bpm)
```

**4c. Atualizar endpoint `criar_equipe`** — substituir a chamada ao service:

```python
# ANTES (linha ~330):
equipe = await service.criar_equipe(nome=data.nome, unidade=data.unidade, admin_id=admin.id)

# DEPOIS:
equipe = await service.criar_equipe(nome=data.nome, bpm_id=data.bpm_id, admin_id=admin.id)
```

### Step 5: Rodar testes

```
pytest tests/integration/test_api_bpms.py tests/integration/test_api_equipes.py -v
```

Esperado: todos os testes passando.

### Step 6: Rodar suite completa para checar regressões

```
pytest tests/ -v --timeout=60
```

Verificar se há falhas em outros arquivos de teste que ainda referenciam `unidade`. Se houver, corrigir antes de commitar (substituir `guarnicao.unidade` por `guarnicao.bpm.nome` e `unidade=` por `bpm_id=`).

### Step 7: Commit

```bash
git add app/api/v1/admin.py tests/integration/test_api_bpms.py tests/integration/test_api_equipes.py
git commit -m "feat(api): endpoints GET/POST /admin/bpms + atualizar /admin/equipes para bpm_id"
```

---

## Task 7: Frontend — navegação em 2 níveis

**Files:**
- Modify: `frontend/js/pages/admin-usuarios.js`

### Step 1: Planejar as mudanças de estado

Estado atual:
```javascript
abaAtiva: "sem-equipe",  // controla qual conteúdo exibir
novaEquipe: { nome: "", unidade: "" },
```

Novo estado:
```javascript
bpms: [],               // lista de BPMs carregados
bpmAtivo: null,         // ID do BPM selecionado no nível 1 (null = nenhum)
equipeAtiva: null,      // ID da equipe selecionada no nível 2 (null = nenhuma)
abaAtiva: "sem-equipe", // "sem-equipe" | number(bpm_id) | "novo-bpm"
novaEquipe: { nome: "" }, // bpm_id vem de abaAtiva quando for número
novoBpm: { nome: "" },
criandoBpm: false,
```

### Step 2: Substituir o conteúdo completo de `frontend/js/pages/admin-usuarios.js`

```javascript
/**
 * Página de gestão de usuários e equipes — exclusivo para administradores.
 *
 * Navegação em 2 níveis: BPMs no topo (nível 1), equipes dentro do BPM
 * ativo (nível 2). A aba "Sem Equipe" (global) lista usuários sem guarnicao_id.
 *
 * Nota: no backend a entidade chama-se "guarnicao". Na UI exibe-se "Equipe".
 */

function renderAdminUsuarios() {
  return `
    <div style="padding: 1rem;" x-data="adminUsuariosPage()" x-init="init()">
      <!-- Cabeçalho -->
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
        <div>
          <h2 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 1.125rem; text-transform: uppercase; letter-spacing: 0.05em;">GERENCIAR USUÁRIOS</h2>
          <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-top: 0.125rem;">Equipes e acesso</p>
          <p x-show="!carregando" style="font-family: var(--font-data); font-size: 12px; color: var(--color-text-dim); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 4px; white-space: nowrap;">
            Policiais Cadastrados:
            <span x-text="usuarios.length.toLocaleString('pt-BR')"
                  style="color: var(--color-success); font-size: 14px; font-weight: 700; text-shadow: 0 0 8px rgba(0,255,136,0.7), 0 0 20px rgba(0,255,136,0.35);"></span>
          </p>
        </div>
        <button @click="abrirCriarUsuario()" class="btn btn-primary" style="font-size: 0.8125rem; padding: 0.375rem 0.75rem;">
          + Novo usuário
        </button>
      </div>

      <!-- Nível 1: abas por BPM -->
      <div x-show="!carregando" style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-bottom: 0.25rem; border-bottom: 1px solid var(--color-border);">
        <button
          @click="abaAtiva = 'sem-equipe'; bpmAtivo = null; equipeAtiva = null"
          :style="abaAtiva === 'sem-equipe' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          Sem Equipe (<span x-text="usuariosSemEquipe.length"></span>)
        </button>
        <template x-for="b in bpms" :key="b.id">
          <button
            @click="selecionarBpm(b.id)"
            :style="bpmAtivo === b.id ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
            style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
            x-text="b.nome"
          ></button>
        </template>
        <button
          @click="abaAtiva = 'novo-bpm'; bpmAtivo = null; equipeAtiva = null"
          :style="abaAtiva === 'novo-bpm' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          + Novo BPM
        </button>
      </div>

      <!-- Nível 2: abas de equipes dentro do BPM ativo -->
      <template x-if="bpmAtivo !== null">
        <div x-show="!carregando" style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-bottom: 1rem; border-bottom: 1px solid rgba(58,80,104,0.4); padding-left: 0.5rem;">
          <template x-for="e in equipesDoBpm(bpmAtivo)" :key="e.id">
            <button
              @click="equipeAtiva = e.id"
              :style="equipeAtiva === e.id ? 'border-bottom: 2px solid var(--color-secondary); color: var(--color-secondary);' : 'color: var(--color-text-dim);'"
              style="padding: 0.375rem 0.625rem; font-family: var(--font-data); font-size: 0.75rem; background: transparent; border: 0; cursor: pointer;"
              x-text="e.nome + ' (' + usuariosDaEquipe(e.id).length + ')'"
            ></button>
          </template>
          <button
            @click="equipeAtiva = 'nova-equipe'"
            :style="equipeAtiva === 'nova-equipe' ? 'border-bottom: 2px solid var(--color-secondary); color: var(--color-secondary);' : 'color: var(--color-text-dim);'"
            style="padding: 0.375rem 0.625rem; font-family: var(--font-data); font-size: 0.75rem; background: transparent; border: 0; cursor: pointer;"
          >
            + Nova Equipe
          </button>
        </div>
      </template>

      <!-- Loading -->
      <div x-show="carregando" style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.875rem; text-align: center; padding: 2rem 0;">Carregando...</div>

      <!-- Conteúdo -->
      <div x-show="!carregando">

        <!-- Aba: Sem Equipe -->
        <template x-if="abaAtiva === 'sem-equipe'">
          <div>
            <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-bottom: 0.75rem;">
              Usuários ainda não atribuídos a uma equipe.
            </p>
            <template x-if="usuariosSemEquipe.length === 0">
              <p style="color: var(--color-text-muted); padding: 1rem; text-align: center;">Nenhum usuário sem equipe.</p>
            </template>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <template x-for="u in usuariosSemEquipe" :key="u.id">
                <div class="glass-card" style="padding: 1rem;" x-data="{ destinoId: '' }">
                  ${cardUsuario('u')}
                  <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; align-items: center;">
                    <select x-model="destinoId" style="flex: 1; padding: 0.375rem 0.5rem; font-size: 0.75rem; font-family: var(--font-data); background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text);">
                      <option value="">Selecionar equipe...</option>
                      <template x-for="e in equipes" :key="e.id">
                        <option :value="e.id" x-text="e.bpm.nome + ' — ' + e.nome"></option>
                      </template>
                    </select>
                    <button @click="moverUsuario(u.id, destinoId ? parseInt(destinoId) : null); destinoId = ''" :disabled="!destinoId" class="btn btn-primary" style="font-size: 0.75rem; padding: 0.375rem 0.75rem;">
                      Atribuir
                    </button>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>

        <!-- Aba: Novo BPM -->
        <template x-if="abaAtiva === 'novo-bpm'">
          <div class="glass-card" style="padding: 1.5rem; max-width: 28rem;">
            <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Novo BPM</h3>
            <div style="margin-bottom: 1rem;">
              <label class="login-field-label">Nome</label>
              <input type="text" x-model="novoBpm.nome" placeholder="Ex: 14º BPM" />
            </div>
            <button @click="criarBpm()" :disabled="criandoBpm || !novoBpm.nome" class="btn btn-primary" style="width: 100%;">
              <span x-show="!criandoBpm">Criar BPM</span>
              <span x-show="criandoBpm">Criando...</span>
            </button>
          </div>
        </template>

        <!-- BPM selecionado: conteúdo de equipe -->
        <template x-if="bpmAtivo !== null">
          <div>

            <!-- Sem equipe selecionada ainda (BPM sem equipes) -->
            <template x-if="equipesDoBpm(bpmAtivo).length === 0 && equipeAtiva !== 'nova-equipe'">
              <p style="color: var(--color-text-muted); padding: 1rem; text-align: center; font-family: var(--font-data); font-size: 0.875rem;">
                Nenhuma equipe neste BPM. Clique em "+ Nova Equipe" para criar.
              </p>
            </template>

            <!-- Nova Equipe dentro do BPM -->
            <template x-if="equipeAtiva === 'nova-equipe'">
              <div class="glass-card" style="padding: 1.5rem; max-width: 28rem;">
                <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Nova equipe</h3>
                <div style="margin-bottom: 1rem;">
                  <label class="login-field-label">Nome</label>
                  <input type="text" x-model="novaEquipe.nome" placeholder="Ex: 3ª Cia - GU 01" />
                </div>
                <button @click="criarEquipe()" :disabled="criandoEquipe || !novaEquipe.nome" class="btn btn-primary" style="width: 100%;">
                  <span x-show="!criandoEquipe">Criar equipe</span>
                  <span x-show="criandoEquipe">Criando...</span>
                </button>
              </div>
            </template>

            <!-- Equipe específica selecionada -->
            <template x-if="typeof equipeAtiva === 'number' && equipeAtivaObj">
              <div>
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-bottom: 0.75rem;">
                  <div>
                    <p style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 0.9375rem;" x-text="equipeAtivaObj.nome"></p>
                    <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;" x-text="equipeAtivaObj.bpm.nome"></p>
                  </div>
                  <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                    <span style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;">Ver apenas abordagens da equipe</span>
                    <input
                      type="checkbox"
                      :checked="equipeAtivaObj.isolamento_abordagens"
                      @change="alternarIsolamento(equipeAtivaObj.id, $event.target.checked)"
                    />
                  </label>
                </div>
                <template x-if="usuariosDaEquipe(equipeAtiva).length === 0">
                  <p style="color: var(--color-text-muted); padding: 1rem; text-align: center;">Nenhum usuário nesta equipe.</p>
                </template>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                  <template x-for="u in usuariosDaEquipe(equipeAtiva)" :key="u.id">
                    <div class="glass-card" style="padding: 1rem;" x-data="{ destinoId: '', modalMover: false }">
                      ${cardUsuario('u')}
                      <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                        <button @click="pausarUsuario(u)"
                                x-show="u.tem_sessao"
                                style="flex: 1; font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.5rem; border-radius: 4px; background: rgba(255,165,0,0.15); color: #FFA500; border: 1px solid rgba(255,165,0,0.3); cursor: pointer;">
                          Pausar acesso
                        </button>
                        <button @click="gerarSenha(u)" class="btn btn-secondary" style="flex: 1; font-size: 0.75rem; padding: 0.375rem 0.5rem;">
                          Gerar nova senha
                        </button>
                        <button @click="modalMover = true" class="btn btn-secondary" style="font-size: 0.75rem; padding: 0.375rem 0.75rem;">
                          Mover
                        </button>
                        <button @click="excluirUsuario(u)"
                                style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.75rem; border-radius: 4px; background: rgba(255,107,0,0.15); color: var(--color-danger); border: 1px solid rgba(255,107,0,0.3); cursor: pointer;">
                          Excluir
                        </button>
                      </div>
                      <!-- Modal: Mover de equipe -->
                      <div x-show="modalMover"
                           @click.self="modalMover = false; destinoId = ''"
                           style="position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 1000;">
                        <div class="glass-card" style="padding: 1.5rem; min-width: 22rem; max-width: 90vw;">
                          <h4 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Mover policial</h4>
                          <select x-model="destinoId" style="width: 100%; padding: 0.5rem; font-size: 0.875rem; background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text); border-radius: 4px; margin-bottom: 1rem;">
                            <option value="">Selecionar equipe destino...</option>
                            <option value="null">Sem equipe</option>
                            <template x-for="e in equipes.filter(eq => eq.id !== u.guarnicao_id)" :key="e.id">
                              <option :value="e.id" x-text="e.bpm.nome + ' — ' + e.nome"></option>
                            </template>
                          </select>
                          <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                            <button @click="modalMover = false; destinoId = ''" class="btn btn-secondary" style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                              Cancelar
                            </button>
                            <button @click="moverUsuario(u.id, destinoId === 'null' ? null : (destinoId ? parseInt(destinoId) : undefined)); destinoId = ''; modalMover = false"
                                    :disabled="!destinoId"
                                    class="btn btn-primary" style="font-size: 0.875rem; padding: 0.5rem 1rem;">
                              Mover
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>
                </div>
              </div>
            </template>

          </div>
        </template>

      </div>

      <!-- Modal: Criar usuário -->
      <div x-cloak
           :style="mostrarFormCriacao ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.8);align-items:center;justify-content:center;z-index:50;padding:1rem;' : 'display:none;'">
        <div class="glass-card" style="padding: 1.5rem; max-width: 24rem; width: 100%; border: 1px solid var(--color-border);">
          <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Novo usuário</h3>
          <div style="margin-bottom: 0.75rem;">
            <label class="login-field-label">Matrícula</label>
            <input type="text" x-model="novaMatricula" placeholder="Ex: PM001" />
          </div>
          <div style="margin-bottom: 1rem;">
            <label class="login-field-label">Equipe</label>
            <select x-model="novaEquipeId" style="width: 100%; padding: 0.5rem; background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text);">
              <option value="">Sem equipe</option>
              <template x-for="e in equipes" :key="e.id">
                <option :value="e.id" x-text="e.bpm.nome + ' — ' + e.nome"></option>
              </template>
            </select>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button @click="cancelarCriacao()" class="btn btn-secondary" style="flex: 1;">Cancelar</button>
            <button @click="criarUsuario()" :disabled="criando" class="btn btn-primary" style="flex: 1;">
              <span x-show="!criando">Criar</span>
              <span x-show="criando">Criando...</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Modal: senha gerada -->
      <div x-cloak
           :style="senhaGerada ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.8);align-items:center;justify-content:center;z-index:50;padding:1rem;' : 'display:none;'">
        <div class="glass-card" style="padding: 1.5rem; max-width: 24rem; width: 100%; border: 1px solid #FFA500;">
          <h3 style="color: #FFA500; font-family: var(--font-display); font-weight: 600; margin-bottom: 0.5rem;">Senha gerada — anote agora</h3>
          <p style="color: var(--color-text-muted); font-family: var(--font-body); font-size: 0.875rem; margin-bottom: 1rem;">Esta senha será exibida apenas uma vez.</p>
          <div style="background: var(--color-bg); border-radius: 4px; padding: 1rem; text-align: center; margin-bottom: 1rem; border: 1px solid var(--color-border);">
            <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; margin-bottom: 0.25rem;" x-text="'Matrícula: ' + (senhaGerada?.matricula || '')"></p>
            <p style="color: var(--color-text); font-family: var(--font-data); font-size: 1.5rem; font-weight: 700; letter-spacing: 0.1em;" x-text="senhaGerada?.senha"></p>
          </div>
          <button @click="senhaGerada = null" class="btn btn-secondary" style="width: 100%;">Entendi, já anotei</button>
        </div>
      </div>
    </div>
  `;
}

/** Helper que retorna o trecho de cabeçalho do card de usuário (avatar + info). */
function cardUsuario(varName) {
  return `
    <div style="display: flex; align-items: center; gap: 0.75rem;">
      <div style="width: 44px; height: 44px; border-radius: 4px; background: var(--color-surface-hover); border: 1px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-primary); font-size: 1rem; font-family: var(--font-display); font-weight: 700; overflow: hidden; flex-shrink: 0;">
        <template x-if="${varName}.foto_url">
          <img :src="${varName}.foto_url" style="width: 100%; height: 100%; object-fit: cover;" />
        </template>
        <template x-if="!${varName}.foto_url">
          <span x-text="(${varName}.nome_guerra || ${varName}.nome || '?')[0].toUpperCase()"></span>
        </template>
      </div>
      <div style="flex: 1; min-width: 0;">
        <p style="color: var(--color-primary); font-family: var(--font-display); font-weight: 700; font-size: 0.9375rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
           x-text="(POSTO_ABREV[${varName}.posto_graduacao] || ${varName}.posto_graduacao || 'Sem grad.') + (${varName}.nome_guerra ? ' ' + ${varName}.nome_guerra : '')"></p>
        <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
           x-text="(${varName}.nome !== ${varName}.matricula ? ${varName}.nome + ' · ' : '') + ${varName}.matricula"></p>
      </div>
      <span :style="${varName}.tem_sessao ? 'background: rgba(0,255,136,0.15); color: var(--color-success);' : 'background: rgba(58,80,104,0.3); color: var(--color-text-dim);'"
            style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.125rem 0.5rem; border-radius: 4px; flex-shrink: 0;"
            x-text="${varName}.tem_sessao ? 'Ativo' : 'Sem sessão'"></span>
    </div>
  `;
}

function adminUsuariosPage() {
  return {
    usuarios: [],
    equipes: [],
    bpms: [],
    bpmAtivo: null,
    equipeAtiva: null,
    abaAtiva: "sem-equipe",
    carregando: true,
    mostrarFormCriacao: false,
    novaMatricula: "",
    novaEquipeId: "",
    criando: false,
    novaEquipe: { nome: "" },
    criandoEquipe: false,
    novoBpm: { nome: "" },
    criandoBpm: false,
    excluindo: false,
    senhaGerada: null,

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.carregando = true;
      try {
        const [usuarios, equipes, bpms] = await Promise.all([
          api.get("/admin/usuarios"),
          api.get("/admin/equipes"),
          api.get("/admin/bpms"),
        ]);
        const ordemRank = [
          "Soldado", "Cabo", "3º Sargento", "2º Sargento", "1º Sargento", "Subtenente",
          "Aspirante", "2º Tenente", "1º Tenente", "Capitão", "Major", "Tenente-Coronel", "Coronel",
        ];
        this.usuarios = usuarios.sort((a, b) => {
          const ra = ordemRank.indexOf(a.posto_graduacao ?? "");
          const rb = ordemRank.indexOf(b.posto_graduacao ?? "");
          if (rb !== ra) return rb - ra;
          return (parseInt(a.matricula) || 0) - (parseInt(b.matricula) || 0);
        });
        this.equipes = equipes;
        this.bpms = bpms;
        // Revalidar estado após reload
        if (this.bpmAtivo !== null && !this.bpms.some(b => b.id === this.bpmAtivo)) {
          this.bpmAtivo = null;
          this.equipeAtiva = null;
          this.abaAtiva = "sem-equipe";
        }
        if (typeof this.equipeAtiva === "number" && !this.equipes.some(e => e.id === this.equipeAtiva)) {
          this.equipeAtiva = null;
        }
      } catch {
        showToast("Erro ao carregar dados", "error");
      } finally {
        this.carregando = false;
      }
    },

    selecionarBpm(bpmId) {
      this.bpmAtivo = bpmId;
      this.abaAtiva = bpmId;
      // Auto-selecionar primeira equipe do BPM, se existir
      const primeiraEquipe = this.equipes.find(e => e.bpm_id === bpmId);
      this.equipeAtiva = primeiraEquipe ? primeiraEquipe.id : null;
    },

    equipesDoBpm(bpmId) {
      return this.equipes.filter(e => e.bpm_id === bpmId);
    },

    get usuariosSemEquipe() {
      return this.usuarios.filter(u => u.guarnicao_id === null || u.guarnicao_id === undefined);
    },

    usuariosDaEquipe(equipeId) {
      return this.usuarios.filter(u => u.guarnicao_id === equipeId);
    },

    get equipeAtivaObj() {
      if (typeof this.equipeAtiva !== "number") return null;
      return this.equipes.find(e => e.id === this.equipeAtiva) || null;
    },

    abrirCriarUsuario() {
      this.novaMatricula = "";
      this.novaEquipeId = typeof this.equipeAtiva === "number" ? String(this.equipeAtiva) : "";
      this.mostrarFormCriacao = true;
    },

    cancelarCriacao() {
      this.mostrarFormCriacao = false;
      this.novaMatricula = "";
      this.novaEquipeId = "";
    },

    async criarUsuario() {
      if (!this.novaMatricula.trim()) return;
      this.criando = true;
      try {
        const payload = { matricula: this.novaMatricula.trim() };
        if (this.novaEquipeId) payload.guarnicao_id = parseInt(this.novaEquipeId);
        const result = await api.post("/admin/usuarios", payload);
        this.senhaGerada = result;
        this.cancelarCriacao();
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao criar usuário", "error");
      } finally {
        this.criando = false;
      }
    },

    async pausarUsuario(u) {
      try {
        await api.patch(`/admin/usuarios/${u.id}/pausar`);
        showToast(`Acesso de ${u.matricula} pausado`, "success");
        await this.carregar();
      } catch {
        showToast("Erro ao pausar usuário", "error");
      }
    },

    async gerarSenha(u) {
      try {
        const result = await api.post(`/admin/usuarios/${u.id}/gerar-senha`);
        this.senhaGerada = result;
        await this.carregar();
      } catch {
        showToast("Erro ao gerar senha", "error");
      }
    },

    async excluirUsuario(u) {
      if (this.excluindo) return;
      if (!confirm(`Excluir o usuário ${u.matricula}? Esta ação não pode ser desfeita.`)) return;
      this.excluindo = true;
      try {
        await api.delete(`/admin/usuarios/${u.id}`);
        showToast("Usuário excluído", "success");
        await this.carregar();
      } catch {
        showToast("Erro ao excluir usuário", "error");
      } finally {
        this.excluindo = false;
      }
    },

    async moverUsuario(usuarioId, destinoId) {
      if (destinoId === undefined) return;
      try {
        await api.patch(`/admin/usuarios/${usuarioId}/equipe`, { guarnicao_id: destinoId });
        showToast("Usuário movido", "success");
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao mover usuário", "error");
      }
    },

    async criarEquipe() {
      if (!this.novaEquipe.nome.trim() || this.bpmAtivo === null) return;
      this.criandoEquipe = true;
      try {
        const equipe = await api.post("/admin/equipes", {
          nome: this.novaEquipe.nome.trim(),
          bpm_id: this.bpmAtivo,
        });
        this.novaEquipe = { nome: "" };
        await this.carregar();
        this.equipeAtiva = equipe.id;
      } catch (e) {
        showToast(e.message || "Erro ao criar equipe", "error");
      } finally {
        this.criandoEquipe = false;
      }
    },

    async criarBpm() {
      if (!this.novoBpm.nome.trim()) return;
      this.criandoBpm = true;
      try {
        const bpm = await api.post("/admin/bpms", { nome: this.novoBpm.nome.trim() });
        this.novoBpm = { nome: "" };
        await this.carregar();
        this.selecionarBpm(bpm.id);
      } catch (e) {
        showToast(e.message || "Erro ao criar BPM", "error");
      } finally {
        this.criandoBpm = false;
      }
    },

    async alternarIsolamento(equipeId, valor) {
      try {
        await api.patch(`/admin/equipes/${equipeId}/toggle-isolamento`, {
          isolamento_abordagens: valor,
        });
        showToast(valor ? "Isolamento ativado" : "Isolamento desativado", "success");
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao atualizar equipe", "error");
        await this.carregar();
      }
    },
  };
}
```

### Step 3: Rodar suite completa de testes

```
pytest tests/ -v --timeout=60
```

Esperado: todos os testes passando.

### Step 4: Commit

```bash
git add frontend/js/pages/admin-usuarios.js
git commit -m "feat(frontend): navegação em 2 níveis BPM > Equipe em gerenciar usuários"
```

---

## Checklist Final

Após todas as tasks, verificar:

- [ ] `pytest tests/ -v` — nenhuma falha
- [ ] `make lint` — sem erros de ruff/mypy
- [ ] Migration testada: `alembic upgrade head` no ambiente local (via `docker compose up`)
- [ ] Página de Gerenciar Usuários abre sem erros no console do browser
- [ ] BPM "14º BPM" e "PMDF" aparecem como abas no topo após migration
- [ ] Criar novo BPM via "+ Novo BPM" funciona
- [ ] Criar equipe dentro de um BPM funciona
- [ ] Mover usuário entre equipes funciona (dropdown exibe "BPM — Equipe")
- [ ] "Sem Equipe" ainda mostra usuários sem guarnicao_id
