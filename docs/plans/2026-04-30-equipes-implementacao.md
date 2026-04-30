# Gestão de Equipes — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Permitir que o admin organize policiais por equipe (guarnição real), com abas na página de gerenciar usuários, toggle por equipe que controla se a equipe vê apenas suas abordagens ou todas, e fluxo orgânico de migração via aba "Sem Equipe".

**Architecture:** Manter `guarnicao` no banco/código (UI mostra "Equipe"). Adicionar coluna `isolamento_abordagens` em `guarnicoes`. Novos endpoints em `/admin/equipes`. Frontend reescreve `admin-usuarios.js` com abas Alpine.js. Pessoas abordadas continuam visíveis para todos.

**Tech Stack:** SQLAlchemy 2.0 async, FastAPI, Alembic, Pydantic v2, Alpine.js, Tailwind, pytest async (httpx AsyncClient).

**Design source:** `docs/plans/2026-04-30-equipes-design.md`

---

## Convenções deste plano

- **Linguagem do projeto:** docstrings em pt-BR (Google Style), código em inglês, mensagens de domínio em pt-BR.
- **TDD obrigatório:** todo código novo é precedido por teste que falha primeiro.
- **Commits frequentes:** uma feature lógica = um commit. Mensagens em pt-BR no formato `tipo(escopo): descrição`.
- **Soft delete + audit:** todas as mutações registram via `AuditService`.
- **Sem FastAPI em service:** routers chamam services, services não importam de `fastapi.*`.
- **Async em todo backend.**
- **Lint:** `make lint` deve passar antes de commit (ruff + mypy).

---

## Task 1: Migration — adicionar `isolamento_abordagens` em `guarnicoes`

**Files:**
- Create: `alembic/versions/<auto>_add_isolamento_abordagens.py`

**Step 1: Verificar `down_revision`**

Run: `cd c:/projetos/argus_ai && ls alembic/versions/ | sort | tail -3`
Anote a última revisão (ex: `f7…`).

```bash
cd c:/projetos/argus_ai && alembic current 2>/dev/null || true
```

Se incerto, abra a última migration e copie seu `revision` para usar como `down_revision`.

**Step 2: Gerar a migration**

```bash
cd c:/projetos/argus_ai && make migrate msg="add isolamento_abordagens em guarnicoes"
```

Isso cria um arquivo em `alembic/versions/`. Abra-o e substitua `upgrade()` e `downgrade()` para serem determinísticas (não confiar no autogen):

```python
def upgrade() -> None:
    """Adiciona coluna isolamento_abordagens em guarnicoes (default False)."""
    op.add_column(
        "guarnicoes",
        sa.Column(
            "isolamento_abordagens",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Remove a coluna isolamento_abordagens."""
    op.drop_column("guarnicoes", "isolamento_abordagens")
```

**Step 3: Aplicar a migration localmente**

```bash
cd c:/projetos/argus_ai && docker compose exec api alembic upgrade head
```

Expected: log `Running upgrade ... -> ...` e nenhum erro.

**Step 4: Verificar o schema**

```bash
cd c:/projetos/argus_ai && docker compose exec db psql -U argus -d argus -c '\d guarnicoes'
```

Expected: lista colunas incluindo `isolamento_abordagens | boolean | not null default false`.

**Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat(db): adicionar coluna isolamento_abordagens em guarnicoes

A coluna controla, por equipe, se seus membros veem apenas as abordagens
da própria equipe (true) ou todas as abordagens do sistema (false).
Default false preserva o comportamento atual."
```

---

## Task 2: Atualizar model `Guarnicao` com novo campo + docstring de equivalência "Equipe"

**Files:**
- Modify: `app/models/guarnicao.py`
- Modify: `app/models/usuario.py` (apenas docstring, esclarecer "Equipe = Guarnicao")

**Step 1: Escrever teste de model**

Create: `tests/unit/test_models_guarnicao.py`

```python
"""Testes do model Guarnicao."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guarnicao import Guarnicao


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_default_false(db_session: AsyncSession):
    """Nova guarnição tem isolamento_abordagens=False por padrão."""
    g = Guarnicao(nome="GU 02", unidade="3o BPM", codigo="3BPM-3CIA-GU02")
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_guarnicao_isolamento_abordagens_persiste_true(db_session: AsyncSession):
    """isolamento_abordagens=True persiste corretamente."""
    g = Guarnicao(
        nome="GU 03",
        unidade="3o BPM",
        codigo="3BPM-3CIA-GU03",
        isolamento_abordagens=True,
    )
    db_session.add(g)
    await db_session.flush()
    await db_session.refresh(g)
    assert g.isolamento_abordagens is True
```

**Step 2: Rodar teste e verificar que falha**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_models_guarnicao.py -v
```

Expected: `FAIL` (atributo `isolamento_abordagens` não existe no model).

**Step 3: Adicionar campo ao model + atualizar docstring**

Edit `app/models/guarnicao.py`:

```python
"""Modelo de Guarnição (Equipe) — unidade operacional do sistema.

NOTA SOBRE NOMENCLATURA: no banco de dados e código interno, a entidade
chama-se "guarnicao". No frontend e para o usuário final, é exibida
como "Equipe". Não há renomeação — apenas labels diferentes na UI.
Manutenções futuras devem manter `guarnicao` no código.
"""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Guarnicao(Base, TimestampMixin, SoftDeleteMixin):
    """Unidade operacional (Equipe) que isola dados entre guarnições.

    Representa uma equipe policial que usa o sistema. Dados operacionais
    são associados via guarnicao_id. O campo isolamento_abordagens controla
    se os membros da equipe veem apenas as abordagens próprias (True) ou
    todas as abordagens do sistema (False, padrão).

    Pessoas abordadas são sempre visíveis para todos, independentemente
    do isolamento (decisão de design).

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome descritivo (ex: "3ª Cia - GU 01").
        unidade: Unidade administrativa superior (ex: "3º BPM").
        codigo: Código único para identificação (ex: "3BPM-3CIA-GU01").
        isolamento_abordagens: Se True, membros veem apenas abordagens da
            própria equipe. Se False (padrão), veem todas as abordagens.
        membros: Relacionamento com usuários (oficiais) da equipe.
    """

    __tablename__ = "guarnicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    unidade: Mapped[str] = mapped_column(String(200))
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    isolamento_abordagens: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    membros = relationship(
        "Usuario",
        back_populates="guarnicao",
        foreign_keys="Usuario.guarnicao_id",
        lazy="selectin",
    )
```

**Step 4: Atualizar docstring de `Usuario` para esclarecer**

Edit `app/models/usuario.py`, ajustando a linha que descreve `guarnicao_id`:

```python
        guarnicao_id: ID da Equipe (guarnição) à qual o usuário pertence.
            FK para guarnicoes.id, nullable. Usuários sem equipe aparecem
            na aba "Sem Equipe" do admin.
```

**Step 5: Rodar testes e verificar passagem**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_models_guarnicao.py -v
```

Expected: `2 passed`.

**Step 6: Commit**

```bash
git add app/models/guarnicao.py app/models/usuario.py tests/unit/test_models_guarnicao.py
git commit -m "feat(model): campo isolamento_abordagens em Guarnicao

Documenta a equivalência Guarnicao = Equipe nas docstrings para
manutenção futura. UI exibe 'Equipe', código mantém 'guarnicao'."
```

---

## Task 3: Schemas Pydantic — `EquipeRead`, `EquipeCreate`, `EquipeUpdate` + ajustes

**Files:**
- Modify: `app/schemas/auth.py`

**Step 1: Escrever teste**

Create: `tests/unit/test_schemas_equipe.py`

```python
"""Testes dos schemas de Equipe (Guarnicao)."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    EquipeCreate,
    EquipeRead,
    UsuarioAdminCreate,
    UsuarioAdminRead,
)


def test_equipe_create_valida_campos():
    """EquipeCreate exige nome e unidade."""
    e = EquipeCreate(nome="3a Cia - GU 01", unidade="3o BPM")
    assert e.nome == "3a Cia - GU 01"
    assert e.unidade == "3o BPM"


def test_equipe_create_rejeita_nome_vazio():
    """EquipeCreate rejeita nome vazio."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="", unidade="3o BPM")


def test_equipe_create_rejeita_unidade_vazia():
    """EquipeCreate rejeita unidade vazia."""
    with pytest.raises(ValidationError):
        EquipeCreate(nome="GU 01", unidade="")


def test_equipe_read_inclui_isolamento():
    """EquipeRead expõe campo isolamento_abordagens."""
    e = EquipeRead(
        id=1,
        nome="GU 01",
        unidade="3o BPM",
        codigo="3BPM-GU01",
        isolamento_abordagens=True,
    )
    assert e.isolamento_abordagens is True


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

**Step 2: Rodar teste**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_schemas_equipe.py -v
```

Expected: `FAIL` em `EquipeCreate`, `EquipeRead` não existem.

**Step 3: Implementar schemas**

Edit `app/schemas/auth.py`:

1. Substituir `GuarnicaoRead` por uma versão que inclui `isolamento_abordagens` e adicionar alias `EquipeRead`:

```python
class GuarnicaoRead(BaseModel):
    """Dados públicos de uma guarnição (Equipe).

    Representação de leitura. UI exibe como "Equipe" — internamente
    a entidade chama-se "guarnicao".

    Attributes:
        id: Identificador único.
        nome: Nome da equipe (ex: "3ª Cia - GU 01").
        unidade: Unidade superior (ex: "3º BPM").
        codigo: Código interno único.
        isolamento_abordagens: Se True, membros veem apenas as abordagens
            da própria equipe. Se False, veem todas.
    """

    id: int
    nome: str
    unidade: str
    codigo: str
    isolamento_abordagens: bool = False

    model_config = {"from_attributes": True}


# Alias semântico para uso futuro/UI ("Equipe" = Guarnicao).
EquipeRead = GuarnicaoRead


class EquipeCreate(BaseModel):
    """Dados para criação de uma nova equipe (guarnição) pelo admin.

    O código é gerado automaticamente pelo serviço a partir do nome.

    Attributes:
        nome: Nome descritivo da equipe (1-200 caracteres).
        unidade: Unidade superior (1-200 caracteres).
    """

    nome: str = Field(..., min_length=1, max_length=200)
    unidade: str = Field(..., min_length=1, max_length=200)


class EquipeIsolamentoUpdate(BaseModel):
    """Dados para alternar isolamento de abordagens de uma equipe.

    Attributes:
        isolamento_abordagens: True ativa isolamento, False desativa.
    """

    isolamento_abordagens: bool


class UsuarioMoverEquipe(BaseModel):
    """Dados para mover usuário entre equipes (ou remover de equipe).

    Attributes:
        guarnicao_id: ID da equipe de destino. None remove o usuário
            da equipe atual (vai para "Sem Equipe").
    """

    guarnicao_id: int | None = None
```

2. Atualizar `UsuarioAdminCreate` para aceitar `guarnicao_id`:

```python
class UsuarioAdminCreate(BaseModel):
    """Dados para criação de usuário pelo admin.

    O admin informa matrícula e (opcionalmente) a equipe.

    Attributes:
        matricula: Matrícula do agente (1-50 caracteres, único).
        guarnicao_id: ID da equipe (opcional). None = "Sem Equipe".
    """

    matricula: str = Field(..., min_length=1, max_length=50)
    guarnicao_id: int | None = Field(None, ge=1)
```

3. Tornar `guarnicao_id` opcional em `UsuarioAdminRead`:

```python
class UsuarioAdminRead(BaseModel):
    """Dados de usuário para listagem no painel admin.

    Attributes:
        ...
        guarnicao_id: ID da equipe. None se "Sem Equipe".
    """

    id: int
    nome: str
    matricula: str
    posto_graduacao: str | None = None
    nome_guerra: str | None = None
    foto_url: str | None = None
    is_admin: bool
    ativo: bool
    tem_sessao: bool
    guarnicao_id: int | None = None  # ← era int, agora opcional

    _normalize_foto = field_validator("foto_url", mode="before")(normalize_storage_url)

    model_config = {"from_attributes": True}
```

**Step 4: Rodar testes**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_schemas_equipe.py -v
```

Expected: `6 passed`.

**Step 5: Garantir que testes existentes ainda passam**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_api_admin.py -v
```

Expected: `all passed` (não deve ter quebrado o teste existente).

**Step 6: Commit**

```bash
git add app/schemas/auth.py tests/unit/test_schemas_equipe.py
git commit -m "feat(schemas): adicionar EquipeCreate, EquipeRead e ajustes

- EquipeRead inclui isolamento_abordagens
- UsuarioAdminCreate aceita guarnicao_id opcional
- UsuarioAdminRead permite guarnicao_id=None (usuários sem equipe)"
```

---

## Task 4: Service `EquipeService` — criar, listar, toggle isolamento

**Files:**
- Create: `app/services/equipe_service.py`
- Create: `tests/unit/test_equipe_service.py`

**Step 1: Escrever testes**

Create `tests/unit/test_equipe_service.py`:

```python
"""Testes de unidade do EquipeService."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.services.equipe_service import EquipeService


@pytest.mark.asyncio
async def test_listar_equipes_retorna_todas_ativas(db_session: AsyncSession, guarnicao):
    """listar_equipes retorna todas as equipes ativas."""
    service = EquipeService(db_session)
    equipes = await service.listar_equipes()
    assert len(equipes) >= 1
    assert any(e.id == guarnicao.id for e in equipes)


@pytest.mark.asyncio
async def test_criar_equipe_gera_codigo(db_session: AsyncSession):
    """criar_equipe gera código único automaticamente."""
    service = EquipeService(db_session)
    e = await service.criar_equipe(nome="3a Cia - GU 02", unidade="3o BPM", admin_id=1)
    assert e.id is not None
    assert e.codigo  # gerado automaticamente
    assert e.nome == "3a Cia - GU 02"
    assert e.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_criar_equipe_nome_duplicado_falha(db_session: AsyncSession, guarnicao):
    """criar_equipe rejeita nome duplicado entre ativas."""
    service = EquipeService(db_session)
    with pytest.raises(ConflitoDadosError):
        await service.criar_equipe(nome=guarnicao.nome, unidade=guarnicao.unidade, admin_id=1)


@pytest.mark.asyncio
async def test_toggle_isolamento_alterna_valor(db_session: AsyncSession, guarnicao):
    """toggle_isolamento alterna o valor."""
    service = EquipeService(db_session)
    assert guarnicao.isolamento_abordagens is False
    e1 = await service.toggle_isolamento(guarnicao.id, valor=True, admin_id=1)
    assert e1.isolamento_abordagens is True
    e2 = await service.toggle_isolamento(guarnicao.id, valor=False, admin_id=1)
    assert e2.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_toggle_isolamento_inexistente_falha(db_session: AsyncSession):
    """toggle_isolamento em equipe inexistente lança NaoEncontradoError."""
    service = EquipeService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.toggle_isolamento(999_999, valor=True, admin_id=1)
```

**Step 2: Rodar e ver falhar**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_equipe_service.py -v
```

Expected: `FAIL` (módulo `equipe_service` não existe).

**Step 3: Implementar o service**

Create `app/services/equipe_service.py`:

```python
"""Serviço de gestão de equipes (guarnições) pelo administrador.

Implementa criação de novas equipes, listagem e alternância do toggle
de isolamento de abordagens. Sem dependências FastAPI.
"""

import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.services.audit_service import AuditService


def _gerar_codigo(nome: str, unidade: str) -> str:
    """Gera código a partir de nome + unidade.

    Remove caracteres não alfanuméricos, normaliza para upper-case e trunca.
    Ex: ("3ª Cia - GU 01", "3º BPM") -> "3BPM-3CIAGU01".

    Args:
        nome: Nome da equipe.
        unidade: Unidade superior.

    Returns:
        Código alfanumérico em upper-case (max 50 chars).
    """
    def _slug(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "", s).upper()

    base = f"{_slug(unidade)}-{_slug(nome)}"
    return base[:50] or "EQUIPE"


class EquipeService:
    """Serviço de gestão de equipes (guarnições) para uso do administrador.

    Cobre criação, listagem e toggle de isolamento de abordagens.
    Registra todas as mutações via AuditService (LGPD).

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        audit: Serviço de auditoria.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço.

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

    async def criar_equipe(self, nome: str, unidade: str, admin_id: int) -> Guarnicao:
        """Cria nova equipe com código gerado automaticamente.

        Args:
            nome: Nome descritivo da equipe.
            unidade: Unidade superior (ex: "3º BPM").
            admin_id: ID do admin que está criando (auditoria).

        Returns:
            Equipe criada com ID atribuído.

        Raises:
            ConflitoDadosError: Se nome ou código já existem entre ativas.
        """
        existing = await self.db.execute(
            select(Guarnicao).where(
                Guarnicao.nome == nome, Guarnicao.ativo == True  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise ConflitoDadosError("Já existe uma equipe ativa com este nome")

        codigo_base = _gerar_codigo(nome, unidade)
        codigo = codigo_base
        # Resolução de colisão: sufixar -2, -3, ... se já existir.
        i = 2
        while True:
            exists = await self.db.execute(
                select(Guarnicao.id).where(Guarnicao.codigo == codigo)
            )
            if exists.scalar_one_or_none() is None:
                break
            codigo = f"{codigo_base[:48]}-{i}"
            i += 1

        equipe = Guarnicao(nome=nome, unidade=unidade, codigo=codigo)
        self.db.add(equipe)
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="CREATE",
            recurso="guarnicao",
            recurso_id=equipe.id,
            detalhes={"nome": nome, "unidade": unidade},
        )
        return equipe

    async def toggle_isolamento(
        self, guarnicao_id: int, valor: bool, admin_id: int
    ) -> Guarnicao:
        """Define o valor de isolamento_abordagens da equipe.

        Args:
            guarnicao_id: ID da equipe.
            valor: True ativa o isolamento, False desativa.
            admin_id: ID do admin (auditoria).

        Returns:
            Equipe atualizada.

        Raises:
            NaoEncontradoError: Se a equipe não existe ou está inativa.
        """
        result = await self.db.execute(
            select(Guarnicao).where(
                Guarnicao.id == guarnicao_id, Guarnicao.ativo == True  # noqa: E712
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

**Step 4: Rodar testes**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_equipe_service.py -v
```

Expected: `5 passed`.

**Step 5: Commit**

```bash
git add app/services/equipe_service.py tests/unit/test_equipe_service.py
git commit -m "feat(services): EquipeService com listar, criar e toggle de isolamento"
```

---

## Task 5: Estender `UsuarioAdminService` — `listar_todos` e `mover_equipe`; ajustar `criar_usuario`

**Files:**
- Modify: `app/services/usuario_admin_service.py`
- Modify: `tests/integration/test_api_admin.py` (adiciona, não substitui)
- Create: `tests/unit/test_usuario_admin_service.py` (se não existir)

**Step 1: Escrever testes**

Create `tests/unit/test_usuario_admin_service.py`:

```python
"""Testes de unidade do UsuarioAdminService — novas funcionalidades."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario
from app.services.usuario_admin_service import UsuarioAdminService


@pytest.fixture
async def outra_equipe(db_session: AsyncSession) -> Guarnicao:
    """Cria uma segunda equipe para testes de movimentação."""
    g = Guarnicao(nome="GU 99", unidade="9o BPM", codigo="9BPM-GU99")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.mark.asyncio
async def test_listar_todos_retorna_todos_usuarios_ativos(
    db_session: AsyncSession, usuario, guarnicao
):
    """listar_todos retorna todos os usuários ativos do sistema."""
    service = UsuarioAdminService(db_session)
    todos = await service.listar_todos()
    assert any(u.id == usuario.id for u in todos)


@pytest.mark.asyncio
async def test_listar_todos_inclui_sem_equipe(db_session: AsyncSession):
    """listar_todos inclui usuários com guarnicao_id=None."""
    from app.core.security import hash_senha

    sem_equipe = Usuario(
        nome="Sem Equipe",
        matricula="ZZ001",
        senha_hash=hash_senha("xxxx"),
        guarnicao_id=None,
    )
    db_session.add(sem_equipe)
    await db_session.flush()

    service = UsuarioAdminService(db_session)
    todos = await service.listar_todos()
    assert any(u.id == sem_equipe.id and u.guarnicao_id is None for u in todos)


@pytest.mark.asyncio
async def test_mover_equipe_atualiza_guarnicao_id(
    db_session: AsyncSession, usuario, outra_equipe
):
    """mover_equipe atualiza guarnicao_id do usuário."""
    service = UsuarioAdminService(db_session)
    u = await service.mover_equipe(
        usuario_id=usuario.id, guarnicao_id_destino=outra_equipe.id, admin_id=1
    )
    assert u.guarnicao_id == outra_equipe.id


@pytest.mark.asyncio
async def test_mover_equipe_para_none_remove_equipe(
    db_session: AsyncSession, usuario
):
    """mover_equipe com destino=None remove o usuário da equipe."""
    service = UsuarioAdminService(db_session)
    u = await service.mover_equipe(
        usuario_id=usuario.id, guarnicao_id_destino=None, admin_id=1
    )
    assert u.guarnicao_id is None


@pytest.mark.asyncio
async def test_mover_equipe_usuario_inexistente_falha(db_session: AsyncSession):
    """mover_equipe em usuário inexistente lança NaoEncontradoError."""
    service = UsuarioAdminService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.mover_equipe(
            usuario_id=999_999, guarnicao_id_destino=None, admin_id=1
        )


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_id_explicito(
    db_session: AsyncSession, outra_equipe
):
    """criar_usuario respeita guarnicao_id passado pelo caller."""
    service = UsuarioAdminService(db_session)
    usuario, _ = await service.criar_usuario(
        matricula="PMNOVO", admin_id=1, guarnicao_id=outra_equipe.id
    )
    assert usuario.guarnicao_id == outra_equipe.id


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_id_none_fica_sem_equipe(
    db_session: AsyncSession,
):
    """criar_usuario com guarnicao_id=None cria usuário sem equipe."""
    service = UsuarioAdminService(db_session)
    usuario, _ = await service.criar_usuario(
        matricula="PMSE01", admin_id=1, guarnicao_id=None
    )
    assert usuario.guarnicao_id is None
```

**Step 2: Rodar e ver falhar**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_usuario_admin_service.py -v
```

Expected: vários `FAIL` — `listar_todos`, `mover_equipe` não existem; comportamento de `criar_usuario` com None ainda cria equipe Geral.

**Step 3: Implementar mudanças**

Edit `app/services/usuario_admin_service.py`:

1. Adicionar `listar_todos()`:

```python
    async def listar_todos(self) -> list[Usuario]:
        """Lista todos os usuários ativos do sistema (todas as equipes + sem equipe).

        Usado pelo admin para gerenciar usuários globalmente. O frontend
        agrupa por guarnicao_id (incluindo None = "Sem Equipe").

        Returns:
            Lista de Usuario com ativo=True, ordenada por nome.
        """
        result = await self.db.execute(
            select(Usuario)
            .where(Usuario.ativo == True)  # noqa: E712
            .order_by(Usuario.nome)
        )
        return list(result.scalars().all())
```

2. Adicionar `mover_equipe()`:

```python
    async def mover_equipe(
        self,
        usuario_id: int,
        guarnicao_id_destino: int | None,
        admin_id: int,
    ) -> Usuario:
        """Move o usuário para outra equipe (ou remove de equipe).

        Args:
            usuario_id: ID do usuário a mover.
            guarnicao_id_destino: ID da equipe de destino. None = remove de equipe.
            admin_id: ID do admin (auditoria).

        Returns:
            Usuario atualizado.

        Raises:
            NaoEncontradoError: Se o usuário não existe ou está inativo.
        """
        usuario = await self.repo.get(usuario_id)
        if not usuario or not usuario.ativo:
            raise NaoEncontradoError("Usuário não encontrado")

        guarnicao_id_origem = usuario.guarnicao_id
        usuario.guarnicao_id = guarnicao_id_destino
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={
                "acao": "mover_equipe",
                "origem": guarnicao_id_origem,
                "destino": guarnicao_id_destino,
            },
        )
        return usuario
```

3. Ajustar `criar_usuario` para **não** criar equipe Geral quando `guarnicao_id is None` — agora None significa "sem equipe":

Remover este bloco:

```python
        # Garantir guarnição: busca ou cria a padrão se não informada
        if not guarnicao_id:
            from app.models.guarnicao import Guarnicao

            result = await self.db.execute(
                select(Guarnicao).where(Guarnicao.ativo == True).limit(1)  # noqa: E712
            )
            guarnicao = result.scalar_one_or_none()
            if not guarnicao:
                guarnicao = Guarnicao(nome="Geral", unidade="Geral", codigo="GERAL-001")
                self.db.add(guarnicao)
                await self.db.flush()
            guarnicao_id = guarnicao.id
```

E atualizar a docstring de `criar_usuario`:

```python
        Args:
            matricula: Matrícula do novo agente (deve ser única).
            admin_id: ID do admin que está criando (para auditoria).
            guarnicao_id: ID da equipe do novo usuário. None = "Sem Equipe"
                (admin atribuirá depois pela aba "Sem Equipe").
```

**Step 4: Rodar testes novos**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/unit/test_usuario_admin_service.py -v
```

Expected: `7 passed`.

**Step 5: Rodar testes existentes (proteger contra regressão)**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_api_admin.py -v
```

Expected: ainda passam. Se algum quebra (provavelmente `test_listar_usuarios_admin` se assumir filtro por guarnição), atualizar — admin agora vê todos. Não mudar o teste sem causa real: leia o teste e ajuste apenas se passou a depender de comportamento que mudamos.

**Step 6: Commit**

```bash
git add app/services/usuario_admin_service.py tests/unit/test_usuario_admin_service.py
git commit -m "feat(services): listar_todos, mover_equipe; criar_usuario aceita None

Admin passa a enxergar todos os usuários (todas equipes + sem equipe).
Remove fallback que criava 'Geral' automaticamente — None agora
significa explicitamente 'Sem Equipe' (resolvido via UI)."
```

---

## Task 6: Endpoints `/admin/equipes` (listar, criar, toggle)

**Files:**
- Modify: `app/api/v1/admin.py`
- Create: `tests/integration/test_api_equipes.py`

**Step 1: Escrever testes de integração**

Create `tests/integration/test_api_equipes.py`:

```python
"""Testes do router /admin/equipes."""

import pytest
from httpx import AsyncClient

from app.core.security import criar_access_token, hash_senha
from app.models.usuario import Usuario


@pytest.fixture
async def admin_usuario(db_session, guarnicao):
    """Admin com sessão ativa."""
    u = Usuario(
        nome="Admin",
        matricula="ADMIN001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        session_id="admin-session-id",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_headers(admin_usuario):
    """Headers de autenticação do admin."""
    token = criar_access_token({
        "sub": str(admin_usuario.id),
        "guarnicao_id": admin_usuario.guarnicao_id,
        "sid": admin_usuario.session_id,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_listar_equipes_retorna_lista(
    client: AsyncClient, admin_headers, guarnicao
):
    """GET /admin/equipes retorna todas as equipes ativas."""
    response = await client.get("/api/v1/admin/equipes", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(e["id"] == guarnicao.id for e in data)
    # Cada equipe expõe isolamento_abordagens
    assert "isolamento_abordagens" in data[0]


@pytest.mark.asyncio
async def test_criar_equipe_201(client: AsyncClient, admin_headers):
    """POST /admin/equipes cria nova equipe."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": "GU 50", "unidade": "5o BPM"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "GU 50"
    assert data["unidade"] == "5o BPM"
    assert data["codigo"]
    assert data["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_criar_equipe_nome_duplicado_409(
    client: AsyncClient, admin_headers, guarnicao
):
    """POST /admin/equipes rejeita nome duplicado."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": guarnicao.nome, "unidade": guarnicao.unidade},
        headers=admin_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_criar_equipe_sem_admin_403(client: AsyncClient, auth_headers):
    """Usuário comum recebe 403 ao criar equipe."""
    response = await client.post(
        "/api/v1/admin/equipes",
        json={"nome": "X", "unidade": "Y"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_toggle_isolamento_alterna(
    client: AsyncClient, admin_headers, guarnicao
):
    """PATCH /admin/equipes/{id}/toggle-isolamento alterna o valor."""
    r1 = await client.patch(
        f"/api/v1/admin/equipes/{guarnicao.id}/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_headers,
    )
    assert r1.status_code == 200
    assert r1.json()["isolamento_abordagens"] is True

    r2 = await client.patch(
        f"/api/v1/admin/equipes/{guarnicao.id}/toggle-isolamento",
        json={"isolamento_abordagens": False},
        headers=admin_headers,
    )
    assert r2.status_code == 200
    assert r2.json()["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_toggle_isolamento_inexistente_404(client: AsyncClient, admin_headers):
    """PATCH em equipe inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/admin/equipes/999999/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_headers,
    )
    assert response.status_code == 404
```

**Step 2: Rodar e ver falhar**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_api_equipes.py -v
```

Expected: `404` em todos (rotas não existem ainda).

**Step 3: Implementar endpoints**

Edit `app/api/v1/admin.py`. Adicionar após os imports e antes dos endpoints existentes:

```python
from app.schemas.auth import (
    EquipeCreate,
    EquipeIsolamentoUpdate,
    EquipeRead,
    SenhaGeradaResponse,
    UsuarioAdminCreate,
    UsuarioAdminRead,
    UsuarioMoverEquipe,
)
from app.services.equipe_service import EquipeService
```

Adicionar os 3 endpoints de equipe ao final do arquivo:

```python
@router.get("/equipes", response_model=list[EquipeRead])
@limiter.limit("30/minute")
async def listar_equipes(
    request: Request,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[EquipeRead]:
    """Lista todas as equipes ativas para gestão pelo admin.

    Args:
        admin: Administrador autenticado.
        db: Sessão do banco.

    Returns:
        Lista de EquipeRead ordenada por nome.

    Status Code:
        200: Lista retornada.
        403: Não é administrador.
    """
    service = EquipeService(db)
    equipes = await service.listar_equipes()
    return [EquipeRead.model_validate(e) for e in equipes]


@router.post("/equipes", response_model=EquipeRead, status_code=201)
@limiter.limit("10/minute")
async def criar_equipe(
    request: Request,
    data: EquipeCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> EquipeRead:
    """Cria nova equipe (guarnição) com código gerado automaticamente.

    Args:
        data: Nome e unidade da equipe.
        admin: Administrador autenticado.
        db: Sessão do banco.

    Returns:
        EquipeRead criada com ID e código.

    Raises:
        HTTPException 409: Se nome já existe.
    """
    service = EquipeService(db)
    try:
        equipe = await service.criar_equipe(
            nome=data.nome, unidade=data.unidade, admin_id=admin.id
        )
    except ConflitoDadosError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    audit = AuditService(db)
    await audit.log(
        usuario_id=admin.id,
        acao="CREATE",
        recurso="guarnicao",
        recurso_id=equipe.id,
        detalhes={"nome": data.nome},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return EquipeRead.model_validate(equipe)


@router.patch("/equipes/{guarnicao_id}/toggle-isolamento", response_model=EquipeRead)
@limiter.limit("10/minute")
async def toggle_isolamento_equipe(
    request: Request,
    guarnicao_id: int,
    data: EquipeIsolamentoUpdate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> EquipeRead:
    """Liga/desliga isolamento de abordagens para a equipe.

    Args:
        guarnicao_id: ID da equipe.
        data: Novo valor do toggle.
        admin: Administrador autenticado.
        db: Sessão do banco.

    Returns:
        EquipeRead com o novo valor.

    Raises:
        HTTPException 404: Se a equipe não existe.
    """
    service = EquipeService(db)
    try:
        equipe = await service.toggle_isolamento(
            guarnicao_id=guarnicao_id,
            valor=data.isolamento_abordagens,
            admin_id=admin.id,
        )
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
    return EquipeRead.model_validate(equipe)
```

**Step 4: Rodar testes**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_api_equipes.py -v
```

Expected: `6 passed`.

**Step 5: Commit**

```bash
git add app/api/v1/admin.py tests/integration/test_api_equipes.py
git commit -m "feat(api): endpoints /admin/equipes (listar, criar, toggle isolamento)"
```

---

## Task 7: Atualizar `GET /admin/usuarios` para retornar todos + endpoint mover equipe

**Files:**
- Modify: `app/api/v1/admin.py`
- Modify: `tests/integration/test_api_admin.py`

**Step 1: Escrever testes**

Adicione ao final de `tests/integration/test_api_admin.py`:

```python
@pytest.mark.asyncio
async def test_listar_usuarios_inclui_sem_equipe(
    client: AsyncClient, admin_headers, db_session
):
    """GET /admin/usuarios inclui usuários sem equipe (guarnicao_id=None)."""
    from app.core.security import hash_senha
    from app.models.usuario import Usuario

    sem_equipe = Usuario(
        nome="Sem Equipe",
        matricula="ZZ001",
        senha_hash=hash_senha("xxxx"),
        guarnicao_id=None,
    )
    db_session.add(sem_equipe)
    await db_session.flush()

    response = await client.get("/api/v1/admin/usuarios", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(u["id"] == sem_equipe.id and u["guarnicao_id"] is None for u in data)


@pytest.mark.asyncio
async def test_mover_usuario_equipe_atualiza(
    client: AsyncClient, admin_headers, usuario, db_session
):
    """PATCH /admin/usuarios/{id}/equipe move o usuário para outra equipe."""
    from app.models.guarnicao import Guarnicao

    nova = Guarnicao(nome="GU 77", unidade="7o BPM", codigo="7BPM-GU77")
    db_session.add(nova)
    await db_session.flush()

    response = await client.patch(
        f"/api/v1/admin/usuarios/{usuario.id}/equipe",
        json={"guarnicao_id": nova.id},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guarnicao_id"] == nova.id


@pytest.mark.asyncio
async def test_mover_usuario_para_none(client: AsyncClient, admin_headers, usuario):
    """PATCH /admin/usuarios/{id}/equipe com guarnicao_id=None remove de equipe."""
    response = await client.patch(
        f"/api/v1/admin/usuarios/{usuario.id}/equipe",
        json={"guarnicao_id": None},
        headers=admin_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["guarnicao_id"] is None


@pytest.mark.asyncio
async def test_mover_usuario_inexistente_404(client: AsyncClient, admin_headers):
    """PATCH em usuário inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/admin/usuarios/999999/equipe",
        json={"guarnicao_id": None},
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_criar_usuario_com_guarnicao_explicita(
    client: AsyncClient, admin_headers, db_session
):
    """POST /admin/usuarios respeita guarnicao_id no payload."""
    from app.models.guarnicao import Guarnicao

    nova = Guarnicao(nome="GU 88", unidade="8o BPM", codigo="8BPM-GU88")
    db_session.add(nova)
    await db_session.flush()

    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "PMNEW01", "guarnicao_id": nova.id},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["matricula"] == "PMNEW01"
    # Verificar diretamente no banco
    from sqlalchemy import select
    from app.models.usuario import Usuario
    res = await db_session.execute(select(Usuario).where(Usuario.id == body["usuario_id"]))
    u = res.scalar_one()
    assert u.guarnicao_id == nova.id


@pytest.mark.asyncio
async def test_criar_usuario_sem_equipe(client: AsyncClient, admin_headers, db_session):
    """POST /admin/usuarios com guarnicao_id=None cria usuário sem equipe."""
    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "PMSEM01", "guarnicao_id": None},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    from sqlalchemy import select
    from app.models.usuario import Usuario
    res = await db_session.execute(select(Usuario).where(Usuario.id == body["usuario_id"]))
    u = res.scalar_one()
    assert u.guarnicao_id is None
```

**Step 2: Rodar testes — devem falhar**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_api_admin.py -v
```

Expected: novos testes `FAIL`.

**Step 3: Atualizar `listar_usuarios` para usar `listar_todos()`**

Edit `app/api/v1/admin.py`:

Localizar a função `listar_usuarios` e trocar:

```python
    usuarios = await service.listar_usuarios(admin.guarnicao_id)
```

por:

```python
    usuarios = await service.listar_todos()
```

E atualizar a docstring para refletir "todos os usuários do sistema".

**Step 4: Atualizar `criar_usuario` para receber `guarnicao_id` do payload**

Localizar a função `criar_usuario` e trocar:

```python
        usuario, senha = await service.criar_usuario(
            matricula=data.matricula,
            admin_id=admin.id,
            guarnicao_id=admin.guarnicao_id,
        )
```

por:

```python
        usuario, senha = await service.criar_usuario(
            matricula=data.matricula,
            admin_id=admin.id,
            guarnicao_id=data.guarnicao_id,
        )
```

**Step 5: Adicionar endpoint mover-equipe**

Adicionar ao final do arquivo:

```python
@router.patch("/usuarios/{usuario_id}/equipe", response_model=UsuarioAdminRead)
@limiter.limit("10/minute")
async def mover_usuario_equipe(
    request: Request,
    usuario_id: int,
    data: UsuarioMoverEquipe,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UsuarioAdminRead:
    """Move o usuário para outra equipe ou remove de equipe (guarnicao_id=None).

    Args:
        usuario_id: ID do usuário.
        data: Equipe de destino (guarnicao_id) ou None.
        admin: Administrador autenticado.
        db: Sessão do banco.

    Returns:
        UsuarioAdminRead atualizado.

    Raises:
        HTTPException 404: Se o usuário não existe.
    """
    service = UsuarioAdminService(db)
    try:
        usuario = await service.mover_equipe(
            usuario_id=usuario_id,
            guarnicao_id_destino=data.guarnicao_id,
            admin_id=admin.id,
        )
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
    return UsuarioAdminRead(
        id=usuario.id,
        nome=usuario.nome,
        matricula=usuario.matricula,
        posto_graduacao=usuario.posto_graduacao,
        nome_guerra=usuario.nome_guerra,
        foto_url=usuario.foto_url,
        is_admin=usuario.is_admin,
        ativo=usuario.ativo,
        tem_sessao=usuario.session_id is not None,
        guarnicao_id=usuario.guarnicao_id,
    )
```

**Step 6: Rodar todos os testes admin**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_api_admin.py tests/integration/test_api_equipes.py -v
```

Expected: todos `PASS`.

**Step 7: Commit**

```bash
git add app/api/v1/admin.py tests/integration/test_api_admin.py
git commit -m "feat(api): admin vê todos os usuários e pode mover entre equipes

- GET /admin/usuarios: agora retorna todos (incluindo sem equipe)
- POST /admin/usuarios: aceita guarnicao_id (None = sem equipe)
- PATCH /admin/usuarios/{id}/equipe: move usuário entre equipes"
```

---

## Task 8: `AbordagemService` — aplicar toggle de isolamento nas listagens

**Files:**
- Modify: `app/services/abordagem_service.py`
- Modify: `app/repositories/abordagem_repo.py` (adicionar variantes sem filtro de guarnicao)
- Modify: `app/api/v1/abordagens.py`
- Create: `tests/integration/test_abordagens_toggle.py`

**Background:**
Quando `usuario.guarnicao.isolamento_abordagens == True`, listagens filtram por `guarnicao_id`. Quando `False`, retornam todas. Pessoas, veículos, ocorrências **não** são afetados — apenas Abordagem.

**Step 1: Escrever testes**

Create `tests/integration/test_abordagens_toggle.py`:

```python
"""Testes do toggle de isolamento de abordagens por equipe."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, hash_senha
from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


@pytest.fixture
async def equipe_b(db_session: AsyncSession) -> Guarnicao:
    """Segunda equipe de teste."""
    g = Guarnicao(nome="GU B", unidade="2o BPM", codigo="2BPM-GUB")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_b(db_session: AsyncSession, equipe_b: Guarnicao) -> Usuario:
    """Usuário ativo na equipe B."""
    u = Usuario(
        nome="Agente B",
        matricula="BBB001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=equipe_b.id,
        session_id="session-b",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def headers_b(usuario_b: Usuario) -> dict:
    """Headers do usuário B."""
    token = criar_access_token({
        "sub": str(usuario_b.id),
        "guarnicao_id": usuario_b.guarnicao_id,
        "sid": usuario_b.session_id,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def abordagem_b(
    db_session: AsyncSession, equipe_b: Guarnicao, usuario_b: Usuario
) -> Abordagem:
    """Abordagem registrada pela equipe B."""
    a = Abordagem(
        guarnicao_id=equipe_b.id,
        usuario_id=usuario_b.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av B 100",
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.mark.asyncio
async def test_isolamento_off_usuario_a_ve_abordagem_de_b(
    client: AsyncClient,
    auth_headers,
    abordagem,  # da guarnicao A (fixture default)
    abordagem_b,  # da guarnicao B
    guarnicao,
):
    """Quando isolamento=False, usuário da equipe A vê abordagens de B também."""
    # Garantir que A tem isolamento OFF (padrão)
    assert guarnicao.isolamento_abordagens is False
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_b.id in ids


@pytest.mark.asyncio
async def test_isolamento_on_usuario_a_nao_ve_abordagem_de_b(
    client: AsyncClient,
    auth_headers,
    db_session,
    guarnicao,
    abordagem,
    abordagem_b,
):
    """Quando isolamento=True, usuário da equipe A vê apenas abordagens de A."""
    guarnicao.isolamento_abordagens = True
    await db_session.flush()
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_b.id not in ids


@pytest.mark.asyncio
async def test_detalhe_abordagem_de_outra_equipe_isolamento_off(
    client: AsyncClient, auth_headers, abordagem_b
):
    """Com isolamento OFF, usuário de A consegue abrir detalhe de abordagem de B."""
    response = await client.get(
        f"/api/v1/abordagens/{abordagem_b.id}", headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_detalhe_abordagem_de_outra_equipe_isolamento_on_404(
    client: AsyncClient, auth_headers, db_session, guarnicao, abordagem_b
):
    """Com isolamento ON, detalhe de abordagem de B retorna 404 para usuário de A."""
    guarnicao.isolamento_abordagens = True
    await db_session.flush()
    response = await client.get(
        f"/api/v1/abordagens/{abordagem_b.id}", headers=auth_headers
    )
    assert response.status_code == 404
```

**Step 2: Rodar testes — falhar**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_abordagens_toggle.py -v
```

Expected: testes de "isolamento OFF, vê de outras" falham (sistema atualmente sempre filtra).

**Step 3: Adicionar variantes globais ao `AbordagemRepository`**

Edit `app/repositories/abordagem_repo.py`. Adicionar 4 métodos globais (não filtrados por guarnicao_id) — espelham os existentes:

```python
    async def get_detail_global(self, id: int) -> Abordagem | None:
        """Busca abordagem por ID em todo o sistema (sem filtro de guarnição).

        Usado quando o usuário pertence a equipe sem isolamento_abordagens.

        Args:
            id: ID da abordagem.

        Returns:
            Abordagem com relacionamentos ou None.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(Abordagem.id == id, Abordagem.ativo == True)  # noqa: E712
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_global(self, skip: int = 0, limit: int = 20) -> Sequence[Abordagem]:
        """Lista todas as abordagens do sistema sem filtro de guarnição."""
        query = (
            select(Abordagem)
            .where(Abordagem.ativo == True)  # noqa: E712
            .order_by(Abordagem.data_hora.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_by_data_global(self, data: date) -> Sequence[Abordagem]:
        """Lista abordagens do sistema (todas equipes) em uma data."""
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(
                Abordagem.ativo == True,  # noqa: E712
                cast(Abordagem.data_hora, Date) == data,
            )
            .order_by(Abordagem.data_hora.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_texto_global(self, q: str, limit: int = 100) -> Sequence[Abordagem]:
        """Busca abordagens por texto em todo o sistema (todas equipes)."""
        # Replicar a lógica de `search_by_texto` removendo o filtro por guarnicao_id.
        # Manter os mesmos joins / filtros de pessoa/placa/endereço.
        ...
```

> **Nota para o executor:** abrir `search_by_texto` no mesmo arquivo, copiar a query e produzir uma versão *sem* a cláusula `Abordagem.guarnicao_id == guarnicao_id`. Manter os demais filtros idênticos.

Os 4 métodos globais usam exatamente as mesmas queries dos originais, removendo a cláusula `Abordagem.guarnicao_id == guarnicao_id`. Mantenha eager loading e ordenação idênticos.

**Step 4: Atualizar `AbordagemService` para escolher a variante**

Edit `app/services/abordagem_service.py`. Adicionar parâmetro `isolamento` em cada método relevante:

```python
    async def listar(
        self,
        guarnicao_id: int,
        skip: int = 0,
        limit: int = 20,
        isolamento: bool = True,
    ) -> Sequence[Abordagem]:
        """Lista abordagens. Se isolamento=False, retorna do sistema todo.

        Args:
            guarnicao_id: ID da equipe (usado se isolamento=True).
            skip, limit: paginação.
            isolamento: True filtra por guarnicao_id; False retorna global.
        """
        if isolamento:
            return await self.repo.list_by_guarnicao(guarnicao_id, skip, limit)
        return await self.repo.list_global(skip, limit)

    async def listar_por_data(
        self,
        guarnicao_id: int,
        data: date,
        isolamento: bool = True,
    ) -> Sequence[Abordagem]:
        if isolamento:
            return await self.repo.list_by_data(guarnicao_id, data)
        return await self.repo.list_by_data_global(data)

    async def buscar_por_texto(
        self,
        q: str,
        guarnicao_id: int,
        limit: int = 100,
        isolamento: bool = True,
    ) -> Sequence[Abordagem]:
        if isolamento:
            return await self.repo.search_by_texto(q, guarnicao_id, limit)
        return await self.repo.search_by_texto_global(q, limit)

    async def buscar_detalhe(
        self,
        abordagem_id: int,
        guarnicao_id: int,
        isolamento: bool = True,
    ) -> Abordagem:
        if isolamento:
            abordagem = await self.repo.get_detail(abordagem_id, guarnicao_id)
        else:
            abordagem = await self.repo.get_detail_global(abordagem_id)
        if not abordagem:
            raise NaoEncontradoError("Abordagem")
        return abordagem
```

**Step 5: Atualizar router de abordagens**

Edit `app/api/v1/abordagens.py`. No `listar_abordagens`, ler `user.guarnicao.isolamento_abordagens`:

```python
    if user.guarnicao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem equipe atribuída",
        )

    isolamento = bool(user.guarnicao and user.guarnicao.isolamento_abordagens)

    service = AbordagemService(db)
    if q is not None:
        abordagens = await service.buscar_por_texto(
            q=q, guarnicao_id=user.guarnicao_id, isolamento=isolamento
        )
    elif data is not None:
        abordagens = await service.listar_por_data(
            guarnicao_id=user.guarnicao_id, data=data, isolamento=isolamento
        )
    else:
        abordagens = await service.listar(
            guarnicao_id=user.guarnicao_id,
            skip=skip,
            limit=limit,
            isolamento=isolamento,
        )
```

E em `detalhe_abordagem`:

```python
    isolamento = bool(user.guarnicao and user.guarnicao.isolamento_abordagens)
    service = AbordagemService(db)
    try:
        abordagem = await service.buscar_detalhe(
            abordagem_id, user.guarnicao_id, isolamento=isolamento
        )
    except NaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Abordagem não encontrada"
        )
```

**Step 6: Rodar testes do toggle**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_abordagens_toggle.py -v
```

Expected: `4 passed`.

**Step 7: Rodar suite completa de abordagens (proteção contra regressão)**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest tests/integration/test_abordagens_api.py tests/integration/test_api_abordagens.py -v
```

Expected: todos passam. Se algum quebrar, é provável que o teste estava acoplado ao isolamento sempre-on; ajustar conforme necessário (de preferência mudando a fixture para definir `isolamento_abordagens=True` na guarnição padrão de teste, e não mudar comportamento da feature).

**Step 8: Commit**

```bash
git add app/repositories/abordagem_repo.py app/services/abordagem_service.py app/api/v1/abordagens.py tests/integration/test_abordagens_toggle.py
git commit -m "feat(abordagens): respeita toggle isolamento_abordagens da equipe

Quando a equipe do usuário tem isolamento_abordagens=False,
listagens e detalhes de abordagens retornam dados de todas as
equipes. Pessoas, veículos e ocorrências não são afetados."
```

---

## Task 9: Frontend — abas e estado base

**Files:**
- Modify: `frontend/js/pages/admin-usuarios.js`

**Step 1: Verificar como o frontend é servido / cache**

Run: `cd c:/projetos/argus_ai && docker compose ps` — confirmar que o frontend é servido com hot-reload (PWA local). Faça hard-refresh do navegador (`Ctrl+Shift+R`) para ver mudanças após cada step.

**Step 2: Substituir o conteúdo de `admin-usuarios.js`**

Reescrever o arquivo (manter API: `renderAdminUsuarios()` e `adminUsuariosPage()`). Estrutura completa:

```javascript
/**
 * Página de gestão de usuários e equipes — exclusivo para administradores.
 *
 * Organiza usuários em abas por equipe. A aba "Sem Equipe" lista usuários
 * sem guarnicao_id. Cada aba de equipe tem toggle de isolamento de abordagens
 * e permite mover usuários entre equipes. Aba "+ Nova Equipe" cria nova.
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
        </div>
        <button @click="abrirCriarUsuario()" class="btn btn-primary" style="font-size: 0.8125rem; padding: 0.375rem 0.75rem;">
          + Novo usuário
        </button>
      </div>

      <!-- Abas -->
      <div x-show="!carregando" style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-bottom: 1rem; border-bottom: 1px solid var(--color-border);">
        <button
          @click="abaAtiva = 'sem-equipe'"
          :style="abaAtiva === 'sem-equipe' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          Sem Equipe (<span x-text="usuariosSemEquipe.length"></span>)
        </button>
        <template x-for="e in equipes" :key="e.id">
          <button
            @click="abaAtiva = e.id"
            :style="abaAtiva === e.id ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
            style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
            x-text="e.nome + ' (' + usuariosDaEquipe(e.id).length + ')'"
          ></button>
        </template>
        <button
          @click="abaAtiva = 'nova-equipe'"
          :style="abaAtiva === 'nova-equipe' ? 'border-bottom: 2px solid var(--color-primary); color: var(--color-primary);' : 'color: var(--color-text-muted);'"
          style="padding: 0.5rem 0.75rem; font-family: var(--font-data); font-size: 0.8125rem; background: transparent; border: 0; cursor: pointer;"
        >
          + Nova Equipe
        </button>
      </div>

      <!-- Loading -->
      <div x-show="carregando" style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.875rem; text-align: center; padding: 2rem 0;">Carregando...</div>

      <!-- Conteúdo das abas -->
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
                        <option :value="e.id" x-text="e.nome"></option>
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

        <!-- Aba: Equipe específica -->
        <template x-if="abaAtiva !== 'sem-equipe' && abaAtiva !== 'nova-equipe'">
          <div>
            <template x-if="equipeAtiva">
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; margin-bottom: 0.75rem;">
                <div>
                  <p style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; font-size: 0.9375rem;" x-text="equipeAtiva.nome"></p>
                  <p style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;" x-text="equipeAtiva.unidade"></p>
                </div>
                <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                  <span style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;">Ver apenas abordagens da equipe</span>
                  <input
                    type="checkbox"
                    :checked="equipeAtiva.isolamento_abordagens"
                    @change="alternarIsolamento(equipeAtiva.id, $event.target.checked)"
                  />
                </label>
              </div>
            </template>
            <template x-if="usuariosDaEquipe(abaAtiva).length === 0">
              <p style="color: var(--color-text-muted); padding: 1rem; text-align: center;">Nenhum usuário nesta equipe.</p>
            </template>
            <div style="display: flex; flex-direction: column; gap: 0.75rem;">
              <template x-for="u in usuariosDaEquipe(abaAtiva)" :key="u.id">
                <div class="glass-card" style="padding: 1rem;" x-data="{ destinoId: '' }">
                  ${cardUsuario('u')}
                  <!-- Ações comuns -->
                  <div style="display: flex; gap: 0.5rem; margin-top: 0.75rem;">
                    <button @click="pausarUsuario(u)"
                            x-show="u.tem_sessao"
                            style="flex: 1; font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.5rem; border-radius: 4px; background: rgba(255,165,0,0.15); color: #FFA500; border: 1px solid rgba(255,165,0,0.3); cursor: pointer;">
                      Pausar acesso
                    </button>
                    <button @click="gerarSenha(u)" class="btn btn-secondary" style="flex: 1; font-size: 0.75rem; padding: 0.375rem 0.5rem;">
                      Gerar nova senha
                    </button>
                    <button @click="excluirUsuario(u)"
                            style="font-size: 0.75rem; font-family: var(--font-data); padding: 0.375rem 0.75rem; border-radius: 4px; background: rgba(255,107,0,0.15); color: var(--color-danger); border: 1px solid rgba(255,107,0,0.3); cursor: pointer;">
                      Excluir
                    </button>
                  </div>
                  <!-- Mover de equipe -->
                  <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; align-items: center;">
                    <select x-model="destinoId" style="flex: 1; padding: 0.375rem 0.5rem; font-size: 0.75rem; background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-text);">
                      <option value="">Mover para...</option>
                      <option value="null">Sem equipe</option>
                      <template x-for="e in equipes.filter(eq => eq.id !== u.guarnicao_id)" :key="e.id">
                        <option :value="e.id" x-text="e.nome"></option>
                      </template>
                    </select>
                    <button @click="moverUsuario(u.id, destinoId === 'null' ? null : (destinoId ? parseInt(destinoId) : undefined)); destinoId = ''" :disabled="!destinoId" class="btn btn-secondary" style="font-size: 0.75rem; padding: 0.375rem 0.75rem;">
                      Mover
                    </button>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>

        <!-- Aba: Nova Equipe -->
        <template x-if="abaAtiva === 'nova-equipe'">
          <div class="glass-card" style="padding: 1.5rem; max-width: 28rem;">
            <h3 style="color: var(--color-text); font-family: var(--font-display); font-weight: 600; margin-bottom: 1rem;">Nova equipe</h3>
            <div style="margin-bottom: 0.75rem;">
              <label class="login-field-label">Nome</label>
              <input type="text" x-model="novaEquipe.nome" placeholder="Ex: 3ª Cia - GU 01" />
            </div>
            <div style="margin-bottom: 1rem;">
              <label class="login-field-label">Unidade</label>
              <input type="text" x-model="novaEquipe.unidade" placeholder="Ex: 3º BPM" />
            </div>
            <button @click="criarEquipe()" :disabled="criandoEquipe || !novaEquipe.nome || !novaEquipe.unidade" class="btn btn-primary" style="width: 100%;">
              <span x-show="!criandoEquipe">Criar equipe</span>
              <span x-show="criandoEquipe">Criando...</span>
            </button>
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
                <option :value="e.id" x-text="e.nome"></option>
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
           x-text="(${varName}.posto_graduacao || 'Sem graduação') + (${varName}.nome_guerra ? ' ' + ${varName}.nome_guerra : '')"></p>
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
    abaAtiva: "sem-equipe",
    carregando: true,
    mostrarFormCriacao: false,
    novaMatricula: "",
    novaEquipeId: "",
    criando: false,
    novaEquipe: { nome: "", unidade: "" },
    criandoEquipe: false,
    excluindo: false,
    senhaGerada: null,

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.carregando = true;
      try {
        const [usuarios, equipes] = await Promise.all([
          api.get("/admin/usuarios"),
          api.get("/admin/equipes"),
        ]);
        const ordemRank = [
          "Soldado","Cabo","3º Sargento","2º Sargento","1º Sargento","Subtenente",
          "Aspirante","2º Tenente","1º Tenente","Capitão","Major","Tenente-Coronel","Coronel",
        ];
        this.usuarios = usuarios.sort((a, b) => {
          const ra = ordemRank.indexOf(a.posto_graduacao ?? "");
          const rb = ordemRank.indexOf(b.posto_graduacao ?? "");
          if (rb !== ra) return rb - ra;
          return (parseInt(a.matricula) || 0) - (parseInt(b.matricula) || 0);
        });
        this.equipes = equipes;
        // Se aba ativa apontava para uma equipe que sumiu, fallback para sem-equipe
        if (typeof this.abaAtiva === "number" && !this.equipes.some(e => e.id === this.abaAtiva)) {
          this.abaAtiva = "sem-equipe";
        }
      } catch {
        showToast("Erro ao carregar dados", "error");
      } finally {
        this.carregando = false;
      }
    },

    get usuariosSemEquipe() {
      return this.usuarios.filter(u => u.guarnicao_id === null || u.guarnicao_id === undefined);
    },

    usuariosDaEquipe(equipeId) {
      return this.usuarios.filter(u => u.guarnicao_id === equipeId);
    },

    get equipeAtiva() {
      return this.equipes.find(e => e.id === this.abaAtiva) || null;
    },

    abrirCriarUsuario() {
      this.novaMatricula = "";
      this.novaEquipeId = typeof this.abaAtiva === "number" ? String(this.abaAtiva) : "";
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
      // destinoId: number | null | undefined. undefined = não fazer nada.
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
      if (!this.novaEquipe.nome.trim() || !this.novaEquipe.unidade.trim()) return;
      this.criandoEquipe = true;
      try {
        const equipe = await api.post("/admin/equipes", {
          nome: this.novaEquipe.nome.trim(),
          unidade: this.novaEquipe.unidade.trim(),
        });
        this.novaEquipe = { nome: "", unidade: "" };
        await this.carregar();
        this.abaAtiva = equipe.id;
      } catch (e) {
        showToast(e.message || "Erro ao criar equipe", "error");
      } finally {
        this.criandoEquipe = false;
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
        await this.carregar(); // recarrega para reverter o checkbox
      }
    },
  };
}
```

> **Nota:** o helper `cardUsuario(varName)` é uma função JS que retorna string — chamada via interpolação `${cardUsuario('u')}` no template literal acima.

**Step 3: Validar manualmente no navegador**

1. Subir docker: `cd c:/projetos/argus_ai && docker compose up -d`
2. Abrir `http://localhost:3000` (ou porta do seu compose) e logar como admin.
3. Acessar "Gerenciar usuários".
4. Conferir todas as abas, criar uma nova equipe, mover usuário, alternar toggle.
5. Conferir DevTools console: zero erros.

**Step 4: Atualizar Service Worker version (cache PWA)**

```bash
cd c:/projetos/argus_ai && git rev-parse --short HEAD
```

Se houver script automático para isso, ele já cuida. Caso contrário, **forçar hard-refresh** durante teste é suficiente. *(Ver commit 8d22ef4 — versionamento automático de cache por commit hash.)*

**Step 5: Commit**

```bash
git add frontend/js/pages/admin-usuarios.js
git commit -m "feat(frontend): abas por equipe na página de gerenciar usuários

- Aba 'Sem Equipe' lista usuários sem guarnicao_id
- Cada equipe tem aba com toggle de isolamento de abordagens
- Aba '+ Nova Equipe' cria equipe inline
- Modal de criar usuário inclui seletor de equipe
- Cards permitem mover usuário entre equipes"
```

---

## Task 10: Verificação final ponta-a-ponta + lint

**Step 1: Lint completo**

```bash
cd c:/projetos/argus_ai && make lint
```

Expected: zero erros. Corrigir o que aparecer.

**Step 2: Suite completa de testes**

```bash
cd c:/projetos/argus_ai && docker compose exec api pytest -x
```

Expected: todos passam.

**Step 3: Smoke test manual**

Subir o sistema (`docker compose up -d`) e validar no navegador (admin):

- [ ] Login como admin funciona
- [ ] "Gerenciar usuários" carrega sem erros no console
- [ ] Aba "Sem Equipe" aparece, mesmo vazia
- [ ] Criar nova equipe via "+ Nova Equipe" gera aba que aparece
- [ ] Criar usuário com equipe selecionada — usuário aparece naquela aba
- [ ] Criar usuário sem equipe — usuário aparece em "Sem Equipe"
- [ ] Mover usuário de "Sem Equipe" para uma equipe funciona
- [ ] Mover usuário entre equipes funciona
- [ ] Toggle de isolamento numa equipe funciona (recarregar ainda mostra valor correto)
- [ ] Login como usuário comum dessa equipe: com toggle ON, vê apenas suas abordagens; com OFF, vê todas
- [ ] Pessoas abordadas continuam sempre visíveis para todos (independentemente do toggle)

**Step 4: Documentar status no MEMORY se algo importante aparecer**

Se surgirem comportamentos não óbvios (ex: o que acontece com tokens existentes quando o admin move usuário entre equipes), considerar atualizar `C:\Users\User\.claude\projects\c--projetos-argus-ai\memory\` com uma nota relevante.

---

## Notas e contexto importante

### Por que `criar_usuario` deixa de criar "Geral" automaticamente
Antes: `guarnicao_id=None` causava criação implícita da equipe "Geral". Agora: o admin tem controle explícito via UI; `None` é estado válido e legítimo (aba "Sem Equipe").

### Por que `EquipeRead` é alias de `GuarnicaoRead`
Consumidores legados continuam usando `GuarnicaoRead`. Novos endpoints e código novo usam `EquipeRead`. Sem dois schemas paralelos.

### Por que mantemos métodos `_global` no repositório (e não `if/else` em uma única função)
Cada query tem eager loading e ordenação específicos. Forçar branching condicional dentro de uma única função torna o código difícil de ler e degrada testabilidade. Duas variantes claras > uma função "esperta".

### Tokens JWT após mover usuário entre equipes
O JWT carrega `guarnicao_id` no claim. Quando o admin move um usuário, o token antigo continua válido (mesma session_id) mas com o `guarnicao_id` desatualizado até o próximo refresh. Isso é tolerável: na pior hipótese, o usuário vê dados da equipe antiga até refazer login. **Não fixar agora** — adicione TODO ao MEMORY se quiser endurecer depois.

### Pessoas e veículos
**Não foram tocados nesta feature.** O isolamento por equipe afeta **apenas** Abordagem (e endpoints derivados). Pessoas, veículos e ocorrências continuam visíveis a todos.

### Migrations e rollback
O `downgrade()` da migration de Task 1 remove a coluna sem perda de dados (todos os valores `True` seriam destruídos, mas isolamento é configuração, não dado de domínio).

### Fixture de teste `guarnicao` em conftest
A fixture cria a equipe com `isolamento_abordagens=False` por padrão (omissão). Os testes do toggle usam `db_session.flush()` para alterar o valor durante o teste.
