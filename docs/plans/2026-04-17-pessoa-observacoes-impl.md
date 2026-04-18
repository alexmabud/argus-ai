# Observações da Pessoa — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar container de observações na ficha da pessoa — nova tabela `pessoa_observacoes` com CRUD completo (backend FastAPI + frontend Alpine.js).

**Architecture:** Nova tabela `pessoa_observacoes` vinculada à `Pessoa` por FK, seguindo o padrão de `vinculos_manuais`. Service próprio (`PessoaObservacaoService`). Frontend: container Alpine.js em `pessoa-detalhe.js` inserido após o container de vínculos (linha 728).

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.0 async / Alembic / Pydantic v2 / Alpine.js

---

### Task 1: Modelo `PessoaObservacao`

**Files:**
- Create: `app/models/pessoa_observacao.py`
- Modify: `app/models/pessoa.py` (adicionar relationship)
- Modify: `app/models/__init__.py` (exportar novo modelo)

**Step 1: Criar `app/models/pessoa_observacao.py`**

```python
"""Modelo de PessoaObservacao — observações livres vinculadas a uma pessoa.

Registra anotações operacionais sobre uma pessoa abordada, com histórico
cronológico e soft delete para rastreabilidade completa.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class PessoaObservacao(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Observação livre vinculada a uma pessoa.

    Registra anotações operacionais com histórico cronológico. Implementa
    soft delete para nunca perder dados (LGPD), multi-tenancy por guarnição
    e audit log em todas as mutações.

    Attributes:
        id: Identificador único.
        pessoa_id: ID da pessoa dona da observação.
        texto: Conteúdo da observação.
        guarnicao_id: Guarnição (herdado de MultiTenantMixin).
    """

    __tablename__ = "pessoa_observacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True
    )
    texto: Mapped[str] = mapped_column(Text)

    pessoa = relationship("Pessoa", back_populates="observacoes_lista")
```

**Step 2: Adicionar relationship em `app/models/pessoa.py`**

Adicionar import no bloco `TYPE_CHECKING` (após linha 18):
```python
    from app.models.pessoa_observacao import PessoaObservacao
```

Adicionar relationship após `vinculos_manuais` (após linha 84):
```python
    observacoes_lista: Mapped[list[PessoaObservacao]] = relationship(
        "PessoaObservacao",
        back_populates="pessoa",
        lazy="selectin",
        order_by="PessoaObservacao.criado_em.desc()",
    )
```

**Step 3: Exportar em `app/models/__init__.py`**

Adicionar linha no final:
```python
from app.models.pessoa_observacao import PessoaObservacao  # noqa: F401
```

**Step 4: Commit**
```bash
git add app/models/pessoa_observacao.py app/models/pessoa.py app/models/__init__.py
git commit -m "feat(model): adicionar PessoaObservacao com soft delete e multi-tenancy"
```

---

### Task 2: Migration Alembic

**Files:**
- Run: `make migrate msg="adicionar tabela pessoa_observacoes"`
- Verify: `alembic/versions/<hash>_adicionar_tabela_pessoa_observacoes.py`

**Step 1: Gerar migration**
```bash
make migrate msg="adicionar tabela pessoa_observacoes"
```

**Step 2: Verificar o arquivo gerado**

O arquivo deve conter `op.create_table('pessoa_observacoes', ...)` com as colunas:
`id`, `pessoa_id`, `texto`, `guarnicao_id`, `criado_em`, `atualizado_em`, `ativo`, `desativado_em`, `desativado_por_id`.
Se `upgrade()` estiver vazio (auto-detect falhou), escrever manualmente:

```python
def upgrade() -> None:
    op.create_table(
        'pessoa_observacoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pessoa_id', sa.Integer(), nullable=False),
        sa.Column('texto', sa.Text(), nullable=False),
        sa.Column('guarnicao_id', sa.Integer(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('desativado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('desativado_por_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['guarnicao_id'], ['guarnicoes.id']),
        sa.ForeignKeyConstraint(['pessoa_id'], ['pessoas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['desativado_por_id'], ['usuarios.id'],
            use_alter=True, name='fk_pessoa_observacoes_desativado_por_id'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pessoa_observacoes_pessoa_id', 'pessoa_observacoes', ['pessoa_id'])
    op.create_index('ix_pessoa_observacoes_guarnicao_id', 'pessoa_observacoes', ['guarnicao_id'])
    op.create_index('ix_pessoa_observacoes_ativo', 'pessoa_observacoes', ['ativo'])


def downgrade() -> None:
    op.drop_index('ix_pessoa_observacoes_ativo', table_name='pessoa_observacoes')
    op.drop_index('ix_pessoa_observacoes_guarnicao_id', table_name='pessoa_observacoes')
    op.drop_index('ix_pessoa_observacoes_pessoa_id', table_name='pessoa_observacoes')
    op.drop_table('pessoa_observacoes')
```

**Step 3: Commit**
```bash
git add alembic/versions/
git commit -m "feat(migration): criar tabela pessoa_observacoes"
```

---

### Task 3: Schemas Pydantic

**Files:**
- Create: `app/schemas/pessoa_observacao.py`

**Step 1: Criar `app/schemas/pessoa_observacao.py`**

```python
"""Schemas Pydantic para observações de pessoas.

Define estruturas de requisição e resposta para criação, atualização
e leitura de observações vinculadas a pessoas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PessoaObservacaoCreate(BaseModel):
    """Requisição de criação de observação.

    Attributes:
        texto: Conteúdo da observação. Obrigatório, mínimo 1 caractere.
    """

    texto: str = Field(..., min_length=1, max_length=2000)


class PessoaObservacaoUpdate(BaseModel):
    """Requisição de atualização de observação.

    Attributes:
        texto: Novo conteúdo da observação. Obrigatório, mínimo 1 caractere.
    """

    texto: str = Field(..., min_length=1, max_length=2000)


class PessoaObservacaoRead(BaseModel):
    """Dados de leitura de observação.

    Attributes:
        id: Identificador único.
        texto: Conteúdo da observação.
        criado_em: Timestamp de criação (para exibição na ficha).
    """

    id: int
    texto: str
    criado_em: datetime

    model_config = {"from_attributes": True}
```

**Step 2: Commit**
```bash
git add app/schemas/pessoa_observacao.py
git commit -m "feat(schema): schemas Pydantic para PessoaObservacao"
```

---

### Task 4: Service `PessoaObservacaoService`

**Files:**
- Create: `app/services/pessoa_observacao_service.py`

**Step 1: Criar `app/services/pessoa_observacao_service.py`**

```python
"""Serviço de lógica de negócio para observações de pessoas.

Gerencia criação, listagem, atualização e soft delete de observações
vinculadas a pessoas, com verificação de tenant e auditoria.
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AcessoNegadoError, NaoEncontradoError
from app.core.permissions import TenantFilter
from app.models.pessoa import Pessoa
from app.models.pessoa_observacao import PessoaObservacao
from app.models.usuario import Usuario
from app.repositories.base import BaseRepository
from app.schemas.pessoa_observacao import PessoaObservacaoCreate, PessoaObservacaoUpdate
from app.services.audit_service import AuditService


class PessoaObservacaoService:
    """Serviço de observações de pessoas.

    Gerencia o ciclo de vida de observações vinculadas a pessoas abordadas.
    Verifica isolamento de tenant em todas as operações e registra auditoria
    em todas as mutações.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        pessoa_repo: Repositório base para Pessoa.
        obs_repo: Repositório base para PessoaObservacao.
        audit: Serviço de auditoria.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço de observações.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.pessoa_repo = BaseRepository(Pessoa, db)
        self.obs_repo = BaseRepository(PessoaObservacao, db)
        self.audit = AuditService(db)

    async def _get_pessoa_verificado(self, pessoa_id: int, user: Usuario) -> Pessoa:
        """Busca pessoa verificando existência e tenant.

        Args:
            pessoa_id: ID da pessoa.
            user: Usuário autenticado.

        Returns:
            Pessoa encontrada.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
        """
        pessoa = await self.pessoa_repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa não encontrada.")
        TenantFilter.verificar(pessoa, user)
        return pessoa

    async def listar(self, pessoa_id: int, user: Usuario) -> list[PessoaObservacao]:
        """Lista observações ativas de uma pessoa, ordenadas da mais recente.

        Args:
            pessoa_id: ID da pessoa.
            user: Usuário autenticado.

        Returns:
            Lista de PessoaObservacao ativas, ordenadas por criado_em desc.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa de outra guarnição.
        """
        await self._get_pessoa_verificado(pessoa_id, user)
        result = await self.db.execute(
            select(PessoaObservacao)
            .where(
                PessoaObservacao.pessoa_id == pessoa_id,
                PessoaObservacao.ativo == True,  # noqa: E712
            )
            .order_by(PessoaObservacao.criado_em.desc())
        )
        return list(result.scalars().all())

    async def criar(
        self,
        pessoa_id: int,
        data: PessoaObservacaoCreate,
        user: Usuario,
        ip_address: str | None = None,
    ) -> PessoaObservacao:
        """Cria nova observação vinculada a uma pessoa.

        Args:
            pessoa_id: ID da pessoa.
            data: Dados da observação (texto).
            user: Usuário autenticado.
            ip_address: IP da requisição (para auditoria).

        Returns:
            PessoaObservacao criada.

        Raises:
            NaoEncontradoError: Se pessoa não existe.
            AcessoNegadoError: Se pessoa de outra guarnição.
        """
        await self._get_pessoa_verificado(pessoa_id, user)
        obs = PessoaObservacao(
            pessoa_id=pessoa_id,
            texto=data.texto,
            guarnicao_id=user.guarnicao_id,
        )
        await self.obs_repo.create(obs)
        await self.audit.log(
            usuario_id=user.id,
            acao="CREATE",
            recurso="pessoa_observacao",
            recurso_id=obs.id,
            detalhes={"pessoa_id": pessoa_id},
            ip_address=ip_address,
        )
        return obs

    async def atualizar(
        self,
        obs_id: int,
        pessoa_id: int,
        data: PessoaObservacaoUpdate,
        user: Usuario,
        ip_address: str | None = None,
    ) -> PessoaObservacao:
        """Atualiza o texto de uma observação existente.

        Args:
            obs_id: ID da observação.
            pessoa_id: ID da pessoa dona da observação.
            data: Novo texto da observação.
            user: Usuário autenticado.
            ip_address: IP da requisição (para auditoria).

        Returns:
            PessoaObservacao atualizada.

        Raises:
            NaoEncontradoError: Se observação não existe ou não pertence à pessoa.
            AcessoNegadoError: Se observação de outra guarnição.
        """
        obs = await self._get_obs_verificada(obs_id, pessoa_id, user)
        await self.obs_repo.update(obs, {"texto": data.texto})
        await self.audit.log(
            usuario_id=user.id,
            acao="UPDATE",
            recurso="pessoa_observacao",
            recurso_id=obs_id,
            detalhes={"pessoa_id": pessoa_id},
            ip_address=ip_address,
        )
        return obs

    async def deletar(
        self,
        obs_id: int,
        pessoa_id: int,
        user: Usuario,
        ip_address: str | None = None,
    ) -> None:
        """Soft delete de uma observação.

        Args:
            obs_id: ID da observação.
            pessoa_id: ID da pessoa dona da observação.
            user: Usuário autenticado.
            ip_address: IP da requisição (para auditoria).

        Raises:
            NaoEncontradoError: Se observação não existe ou não pertence à pessoa.
            AcessoNegadoError: Se observação de outra guarnição.
        """
        obs = await self._get_obs_verificada(obs_id, pessoa_id, user)
        await self.obs_repo.soft_delete(obs, deleted_by_id=user.id)
        await self.audit.log(
            usuario_id=user.id,
            acao="DELETE",
            recurso="pessoa_observacao",
            recurso_id=obs_id,
            detalhes={"pessoa_id": pessoa_id},
            ip_address=ip_address,
        )

    async def _get_obs_verificada(
        self, obs_id: int, pessoa_id: int, user: Usuario
    ) -> PessoaObservacao:
        """Busca observação verificando existência, vínculo com pessoa e tenant.

        Args:
            obs_id: ID da observação.
            pessoa_id: ID esperado da pessoa dona.
            user: Usuário autenticado.

        Returns:
            PessoaObservacao encontrada.

        Raises:
            NaoEncontradoError: Se observação não existe ou não pertence à pessoa.
            AcessoNegadoError: Se observação de outra guarnição.
        """
        obs = await self.obs_repo.get(obs_id)
        if not obs or obs.pessoa_id != pessoa_id:
            raise NaoEncontradoError("Observação não encontrada.")
        if obs.guarnicao_id != user.guarnicao_id:
            raise AcessoNegadoError("Acesso negado.")
        return obs
```

**Step 2: Commit**
```bash
git add app/services/pessoa_observacao_service.py
git commit -m "feat(service): PessoaObservacaoService com CRUD e auditoria"
```

---

### Task 5: Testes Unitários do Service

**Files:**
- Create: `tests/unit/test_pessoa_observacao_service.py`

**Step 1: Criar testes unitários**

```python
"""Testes unitários para PessoaObservacaoService.

Verifica criação, listagem, atualização e soft delete de observações,
incluindo verificação de tenant e tratamento de erros.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AcessoNegadoError, NaoEncontradoError
from app.models.pessoa import Pessoa
from app.models.pessoa_observacao import PessoaObservacao
from app.models.usuario import Usuario
from app.schemas.pessoa_observacao import PessoaObservacaoCreate, PessoaObservacaoUpdate
from app.services.pessoa_observacao_service import PessoaObservacaoService


def make_user(guarnicao_id: int = 1) -> Usuario:
    """Cria usuário mock para testes.

    Args:
        guarnicao_id: ID da guarnição do usuário.

    Returns:
        Usuário mock com id e guarnicao_id.
    """
    u = MagicMock(spec=Usuario)
    u.id = 10
    u.guarnicao_id = guarnicao_id
    return u


def make_pessoa(id: int = 1, guarnicao_id: int = 1) -> Pessoa:
    """Cria pessoa mock para testes.

    Args:
        id: ID da pessoa.
        guarnicao_id: Guarnição da pessoa.

    Returns:
        Pessoa mock ativa com id e guarnicao_id.
    """
    p = MagicMock(spec=Pessoa)
    p.id = id
    p.guarnicao_id = guarnicao_id
    p.ativo = True
    return p


def make_obs(id: int = 1, pessoa_id: int = 1, guarnicao_id: int = 1) -> PessoaObservacao:
    """Cria observação mock para testes.

    Args:
        id: ID da observação.
        pessoa_id: ID da pessoa dona.
        guarnicao_id: Guarnição da observação.

    Returns:
        PessoaObservacao mock ativa.
    """
    obs = MagicMock(spec=PessoaObservacao)
    obs.id = id
    obs.pessoa_id = pessoa_id
    obs.guarnicao_id = guarnicao_id
    obs.ativo = True
    obs.texto = "Observação teste"
    return obs


@pytest.fixture
def db():
    """Fixture de sessão de banco mock."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def service(db):
    """Fixture de PessoaObservacaoService com mocks.

    Args:
        db: Sessão mock do banco.

    Returns:
        PessoaObservacaoService com repos e audit mockados.
    """
    svc = PessoaObservacaoService(db)
    svc.pessoa_repo = AsyncMock()
    svc.obs_repo = AsyncMock()
    svc.audit = AsyncMock()
    return svc


class TestCriarObservacao:
    """Testes para PessoaObservacaoService.criar."""

    async def test_cria_com_sucesso(self, service):
        """Testa criação retorna PessoaObservacao com dados corretos.

        Args:
            service: Service com mocks.
        """
        user = make_user()
        pessoa = make_pessoa()
        service.pessoa_repo.get = AsyncMock(return_value=pessoa)
        service.obs_repo.create = AsyncMock(side_effect=lambda obs: obs)

        data = PessoaObservacaoCreate(texto="Texto da observação")
        result = await service.criar(1, data, user)

        assert result.texto == "Texto da observação"
        assert result.pessoa_id == 1
        assert result.guarnicao_id == user.guarnicao_id
        service.audit.log.assert_awaited_once()

    async def test_pessoa_inexistente_levanta_nao_encontrado(self, service):
        """Testa que NaoEncontradoError é levantado se pessoa não existe.

        Args:
            service: Service com mocks.
        """
        service.pessoa_repo.get = AsyncMock(return_value=None)
        data = PessoaObservacaoCreate(texto="Texto")

        with pytest.raises(NaoEncontradoError):
            await service.criar(999, data, make_user())

    async def test_pessoa_outra_guarnicao_levanta_acesso_negado(self, service):
        """Testa que AcessoNegadoError é levantado se pessoa é de outra guarnição.

        Args:
            service: Service com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(guarnicao_id=99)
        service.pessoa_repo.get = AsyncMock(return_value=pessoa)
        data = PessoaObservacaoCreate(texto="Texto")

        with pytest.raises(AcessoNegadoError):
            await service.criar(1, data, user)


class TestAtualizarObservacao:
    """Testes para PessoaObservacaoService.atualizar."""

    async def test_atualiza_com_sucesso(self, service):
        """Testa atualização retorna observação com novo texto.

        Args:
            service: Service com mocks.
        """
        user = make_user()
        obs = make_obs()
        service.obs_repo.get = AsyncMock(return_value=obs)
        service.obs_repo.update = AsyncMock(side_effect=lambda o, d: o)

        data = PessoaObservacaoUpdate(texto="Novo texto")
        await service.atualizar(1, 1, data, user)

        service.obs_repo.update.assert_awaited_once_with(obs, {"texto": "Novo texto"})
        service.audit.log.assert_awaited_once()

    async def test_obs_inexistente_levanta_nao_encontrado(self, service):
        """Testa que NaoEncontradoError é levantado se observação não existe.

        Args:
            service: Service com mocks.
        """
        service.obs_repo.get = AsyncMock(return_value=None)
        data = PessoaObservacaoUpdate(texto="Novo texto")

        with pytest.raises(NaoEncontradoError):
            await service.atualizar(999, 1, data, make_user())

    async def test_obs_outra_guarnicao_levanta_acesso_negado(self, service):
        """Testa que AcessoNegadoError é levantado se observação é de outra guarnição.

        Args:
            service: Service com mocks.
        """
        user = make_user(guarnicao_id=1)
        obs = make_obs(guarnicao_id=99)
        service.obs_repo.get = AsyncMock(return_value=obs)
        data = PessoaObservacaoUpdate(texto="Novo texto")

        with pytest.raises(AcessoNegadoError):
            await service.atualizar(1, 1, data, user)


class TestDeletarObservacao:
    """Testes para PessoaObservacaoService.deletar."""

    async def test_deleta_com_soft_delete(self, service):
        """Testa que deletar executa soft delete e registra auditoria.

        Args:
            service: Service com mocks.
        """
        user = make_user()
        obs = make_obs()
        service.obs_repo.get = AsyncMock(return_value=obs)
        service.obs_repo.soft_delete = AsyncMock(return_value=obs)

        await service.deletar(1, 1, user)

        service.obs_repo.soft_delete.assert_awaited_once_with(obs, deleted_by_id=user.id)
        service.audit.log.assert_awaited_once()

    async def test_obs_inexistente_levanta_nao_encontrado(self, service):
        """Testa que NaoEncontradoError é levantado se observação não existe.

        Args:
            service: Service com mocks.
        """
        service.obs_repo.get = AsyncMock(return_value=None)

        with pytest.raises(NaoEncontradoError):
            await service.deletar(999, 1, make_user())
```

**Step 2: Rodar testes unitários**
```bash
pytest tests/unit/test_pessoa_observacao_service.py -v
```
Esperado: todos os testes PASS.

**Step 3: Commit**
```bash
git add tests/unit/test_pessoa_observacao_service.py
git commit -m "test(unit): testes unitários para PessoaObservacaoService"
```

---

### Task 6: Endpoints REST

**Files:**
- Modify: `app/api/v1/pessoas.py` (adicionar 4 endpoints ao router existente)

**Step 1: Adicionar imports em `app/api/v1/pessoas.py`**

No bloco de imports (após a linha `from app.schemas.vinculo_manual import ...`), adicionar:
```python
from app.schemas.pessoa_observacao import (
    PessoaObservacaoCreate,
    PessoaObservacaoRead,
    PessoaObservacaoUpdate,
)
from app.services.pessoa_observacao_service import PessoaObservacaoService
```

**Step 2: Adicionar 4 endpoints no final de `app/api/v1/pessoas.py`**

Adicionar após o último endpoint existente (após linha `await db.commit()` do endpoint de remover vínculo):

```python
# ---------------------------------------------------------------------------
# Observações da Pessoa
# ---------------------------------------------------------------------------


@router.get(
    "/{pessoa_id}/observacoes",
    response_model=list[PessoaObservacaoRead],
)
@limiter.limit("30/minute")
async def listar_observacoes(
    request: Request,
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[PessoaObservacaoRead]:
    """Lista observações ativas de uma pessoa, da mais recente para a mais antiga.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de PessoaObservacaoRead.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.
    """
    service = PessoaObservacaoService(db)
    observacoes = await service.listar(pessoa_id, user)
    return [PessoaObservacaoRead.model_validate(o) for o in observacoes]


@router.post(
    "/{pessoa_id}/observacoes",
    response_model=PessoaObservacaoRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def criar_observacao(
    request: Request,
    pessoa_id: int,
    data: PessoaObservacaoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaObservacaoRead:
    """Cria nova observação vinculada a uma pessoa.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa.
        data: Dados da observação (texto).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaObservacaoRead com dados da observação criada.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.

    Status Code:
        201: Observação criada.
    """
    service = PessoaObservacaoService(db)
    obs = await service.criar(
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(obs)
    return PessoaObservacaoRead.model_validate(obs)


@router.patch(
    "/{pessoa_id}/observacoes/{obs_id}",
    response_model=PessoaObservacaoRead,
)
@limiter.limit("30/minute")
async def atualizar_observacao(
    request: Request,
    pessoa_id: int,
    obs_id: int,
    data: PessoaObservacaoUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaObservacaoRead:
    """Atualiza o texto de uma observação existente.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona da observação.
        obs_id: ID da observação.
        data: Novo texto da observação.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaObservacaoRead com texto atualizado.

    Raises:
        NaoEncontradoError: Se observação não existe.
        AcessoNegadoError: Se observação de outra guarnição.
    """
    service = PessoaObservacaoService(db)
    obs = await service.atualizar(
        obs_id,
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(obs)
    return PessoaObservacaoRead.model_validate(obs)


@router.delete(
    "/{pessoa_id}/observacoes/{obs_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@limiter.limit("30/minute")
async def deletar_observacao(
    request: Request,
    pessoa_id: int,
    obs_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Soft delete de uma observação.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona da observação.
        obs_id: ID da observação.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Raises:
        NaoEncontradoError: Se observação não existe.
        AcessoNegadoError: Se observação de outra guarnição.

    Status Code:
        204: Observação removida.
    """
    service = PessoaObservacaoService(db)
    await service.deletar(
        obs_id,
        pessoa_id,
        user,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
```

**Step 3: Rodar lint**
```bash
make lint
```
Esperado: sem erros.

**Step 4: Commit**
```bash
git add app/api/v1/pessoas.py app/schemas/pessoa_observacao.py app/services/pessoa_observacao_service.py
git commit -m "feat(api): endpoints CRUD para observacoes de pessoa"
```

---

### Task 7: Testes de Integração da API

**Files:**
- Create: `tests/integration/test_api_pessoa_observacoes.py`

**Step 1: Criar testes de integração**

```python
"""Testes de integração para endpoints de observações de pessoas.

Testa criação, listagem, atualização e soft delete de observações,
incluindo isolamento multi-tenant e validações.
"""

import pytest
from httpx import AsyncClient


class TestCriarObservacao:
    """Testes do endpoint POST /api/v1/pessoas/{id}/observacoes."""

    async def test_criar_observacao_retorna_201(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa criação de observação retorna 201 com dados corretos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Observação de teste"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["texto"] == "Observação de teste"
        assert "id" in data
        assert "criado_em" in data

    async def test_criar_sem_auth_retorna_401(self, client: AsyncClient, pessoa):
        """Testa que requisição sem token retorna 401.

        Args:
            client: Cliente HTTP assincrónico.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Teste"},
        )
        assert response.status_code == 401

    async def test_texto_vazio_retorna_422(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa que texto vazio retorna 422.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_pessoa_inexistente_retorna_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Testa que pessoa inexistente retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.post(
            "/api/v1/pessoas/99999/observacoes",
            json={"texto": "Observação"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListarObservacoes:
    """Testes do endpoint GET /api/v1/pessoas/{id}/observacoes."""

    async def test_listar_retorna_lista_vazia(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa que listagem retorna lista vazia quando não há observações.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.get(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_listar_retorna_observacoes_criadas(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa que listagem retorna observações criadas.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Primeira"},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Segunda"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Mais recente primeiro
        assert data[0]["texto"] == "Segunda"


class TestAtualizarObservacao:
    """Testes do endpoint PATCH /api/v1/pessoas/{id}/observacoes/{obs_id}."""

    async def test_atualizar_texto_retorna_200(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa que atualização retorna 200 com novo texto.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Texto original"},
            headers=auth_headers,
        )
        obs_id = create_resp.json()["id"]

        response = await client.patch(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/{obs_id}",
            json={"texto": "Texto atualizado"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["texto"] == "Texto atualizado"

    async def test_obs_inexistente_retorna_404(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa que observação inexistente retorna 404.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        response = await client.patch(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/99999",
            json={"texto": "Novo texto"},
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestDeletarObservacao:
    """Testes do endpoint DELETE /api/v1/pessoas/{id}/observacoes/{obs_id}."""

    async def test_deletar_retorna_204(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa que soft delete retorna 204.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Observação para deletar"},
            headers=auth_headers,
        )
        obs_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/{obs_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_obs_deletada_nao_aparece_na_listagem(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Testa que observação deletada não aparece mais na listagem.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            json={"texto": "Para deletar"},
            headers=auth_headers,
        )
        obs_id = create_resp.json()["id"]

        await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/observacoes/{obs_id}",
            headers=auth_headers,
        )

        list_resp = await client.get(
            f"/api/v1/pessoas/{pessoa.id}/observacoes",
            headers=auth_headers,
        )
        ids = [o["id"] for o in list_resp.json()]
        assert obs_id not in ids
```

**Step 2: Rodar testes de integração**
```bash
pytest tests/integration/test_api_pessoa_observacoes.py -v
```
Esperado: todos os testes PASS.

**Step 3: Rodar todos os testes**
```bash
make test
```
Esperado: sem regressões.

**Step 4: Commit**
```bash
git add tests/integration/test_api_pessoa_observacoes.py tests/unit/test_pessoa_observacao_service.py
git commit -m "test(integration): testes de integração para observacoes de pessoa"
```

---

### Task 8: Frontend — Estado e Métodos Alpine.js

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Step 1: Adicionar variáveis de estado após o bloco de vínculos manuais**

Localizar o bloco de vínculos manuais (linhas ~873-883). Após a linha `_buscaTimer: null,`, inserir:

```javascript
    // Observações
    observacoes: [],
    modalObservacao: false,
    obsForm: { id: null, texto: '' },
    salvandoObs: false,
```

**Step 2: Adicionar chamada `carregarObservacoes()` no método `load()`**

Localizar o método `load()` (linha ~940). Após a linha:
```javascript
        this.vinculosManuais = this.pessoa.vinculos_manuais || [];
```
Adicionar:
```javascript
        // Carregar observações da pessoa
        await this.carregarObservacoes();
```

**Step 3: Adicionar os 4 métodos ao objeto Alpine.js**

Localizar o método `removerVinculo` (linha ~1211). Após o fechamento deste método (após `},`), adicionar:

```javascript
    async carregarObservacoes() {
      try {
        this.observacoes = await api.get(`/pessoas/${pessoaId}/observacoes`);
      } catch {
        this.observacoes = [];
      }
    },

    abrirModalObservacao(obs = null) {
      if (obs) {
        this.obsForm = { id: obs.id, texto: obs.texto };
      } else {
        this.obsForm = { id: null, texto: '' };
      }
      this.modalObservacao = true;
    },

    async salvarObservacao() {
      if (!this.obsForm.texto.trim()) return;
      this.salvandoObs = true;
      try {
        if (this.obsForm.id) {
          const atualizada = await api.patch(
            `/pessoas/${pessoaId}/observacoes/${this.obsForm.id}`,
            { texto: this.obsForm.texto.trim() }
          );
          const idx = this.observacoes.findIndex(o => o.id === this.obsForm.id);
          if (idx !== -1) this.observacoes[idx] = atualizada;
        } else {
          const nova = await api.post(`/pessoas/${pessoaId}/observacoes`, {
            texto: this.obsForm.texto.trim()
          });
          this.observacoes.unshift(nova);
        }
        this.modalObservacao = false;
        this.obsForm = { id: null, texto: '' };
      } catch (err) {
        alert(err.message || 'Erro ao salvar observação.');
      } finally {
        this.salvandoObs = false;
      }
    },

    async deletarObservacao(obsId) {
      if (!confirm('Remover esta observação?')) return;
      try {
        await api.del(`/pessoas/${pessoaId}/observacoes/${obsId}`);
        this.observacoes = this.observacoes.filter(o => o.id !== obsId);
      } catch (err) {
        alert(err.message || 'Erro ao remover observação.');
      }
    },
```

**Step 4: Commit**
```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): estado e métodos Alpine.js para observacoes"
```

---

### Task 9: Frontend — Container HTML e Modal

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Step 1: Inserir container de observações após o fechamento do container de vínculos**

Localizar a linha 728 (fechamento `</div>` do container de vínculos):
```html
          </div>

          <!-- Histórico de abordagens -->
```

Inserir entre essas duas linhas o HTML do container de observações:

```html
          <!-- Observações da Pessoa -->
          <div class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border); flex: 1; margin-right: 0.5rem;">Observações</h3>
              <button @click="abrirModalObservacao()"
                      style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-size: 0.75rem; font-family: var(--font-data); font-weight: 600; letter-spacing: 0.05em; padding: 0; opacity: 0.85; transition: opacity 0.15s;"
                      onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.85'">
                + Nova Observação
              </button>
            </div>

            <!-- Lista de observações -->
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <template x-for="obs in observacoes" :key="obs.id">
                <div class="card-led-purple" style="position: relative; border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem; display: flex; flex-direction: column; gap: 0.25rem;">
                  <!-- Data no canto superior direito + botões de ação -->
                  <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.5rem;">
                    <span x-show="obs.criado_em" style="font-size: 10px; color: var(--color-text-dim);"
                          x-text="new Date(obs.criado_em).toLocaleDateString('pt-BR') + ' ' + new Date(obs.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
                    <button @click="abrirModalObservacao(obs)"
                            style="color: var(--color-text-dim); background: none; border: none; cursor: pointer; padding: 0;"
                            onmouseover="this.style.color='var(--color-primary)'" onmouseout="this.style.color='var(--color-text-dim)'"
                            title="Editar observação">
                      <svg style="width: 0.875rem; height: 0.875rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10"/>
                      </svg>
                    </button>
                    <button @click="deletarObservacao(obs.id)"
                            style="color: var(--color-text-dim); background: none; border: none; cursor: pointer; padding: 0;"
                            onmouseover="this.style.color='var(--color-danger)'" onmouseout="this.style.color='var(--color-text-dim)'"
                            title="Remover observação">
                      <svg style="width: 0.875rem; height: 0.875rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                  <!-- Texto da observação -->
                  <p style="font-size: 0.8125rem; color: var(--color-text-muted); margin: 0; white-space: pre-wrap;" x-text="obs.texto"></p>
                </div>
              </template>
            </div>

            <!-- Mensagem quando não há observações -->
            <div x-show="!observacoes.length"
                 style="font-size: 0.75rem; color: var(--color-text-dim); text-align: center; padding: 0.5rem 0;">
              Nenhuma observação cadastrada
            </div>
          </div>
```

**Step 2: Inserir modal de criar/editar observação**

Localizar o modal de vínculo (linha ~415, buscar por `<!-- Modal de cadastro de vínculo manual -->`). Antes dessa linha, inserir o modal de observação:

```html
          <!-- Modal de criar/editar observação -->
          <div x-show="modalObservacao" x-cloak
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem;">
            <div class="glass-card" style="width: 100%; max-width: 480px; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; position: relative;">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="font-family: var(--font-data); font-size: 0.875rem; font-weight: 700; color: var(--color-text); margin: 0; text-transform: uppercase; letter-spacing: 0.05em;"
                    x-text="obsForm.id ? 'Editar Observação' : 'Nova Observação'"></h3>
                <button @click="modalObservacao = false"
                        style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); font-size: 1.25rem; line-height: 1;">×</button>
              </div>

              <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-dim); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">
                  Observação <span style="color: var(--color-danger)">*</span>
                </label>
                <textarea x-model="obsForm.texto" rows="4"
                          placeholder="Digite a observação..."
                          style="background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.625rem; color: var(--color-text); font-size: 0.875rem; font-family: var(--font-data); resize: vertical; outline: none;"
                          @focus="$el.style.borderColor='var(--color-primary)'"
                          @blur="$el.style.borderColor='var(--color-border)'"></textarea>
              </div>

              <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                <button @click="modalObservacao = false"
                        style="padding: 0.5rem 1rem; background: none; border: 1px solid var(--color-border); border-radius: 4px; color: var(--color-text-dim); cursor: pointer; font-size: 0.8125rem; font-family: var(--font-data);">
                  Cancelar
                </button>
                <button @click="salvarObservacao()" :disabled="salvandoObs || !obsForm.texto.trim()"
                        style="padding: 0.5rem 1rem; background: var(--color-primary); border: none; border-radius: 4px; color: #000; font-weight: 700; cursor: pointer; font-size: 0.8125rem; font-family: var(--font-data); opacity: 1; transition: opacity 0.15s;"
                        :style="(salvandoObs || !obsForm.texto.trim()) ? 'opacity: 0.5; cursor: not-allowed;' : ''">
                  <span x-show="!salvandoObs" x-text="obsForm.id ? 'Salvar' : 'Adicionar'"></span>
                  <span x-show="salvandoObs">Salvando...</span>
                </button>
              </div>
            </div>
          </div>
```

**Step 3: Testar visualmente**

Iniciar o servidor local (`make dev`), abrir a ficha de um abordado, verificar:
- Container "Observações" aparece abaixo do container de vínculos
- Botão "+ Nova Observação" abre modal
- Criar observação → aparece no container com data no canto superior direito
- Botão editar → modal abre com texto preenchido, salva e atualiza
- Botão deletar → confirma e remove da lista
- Estado vazio ("Nenhuma observação cadastrada") aparece quando lista está vazia

**Step 4: Commit final**
```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): container de observacoes na ficha do abordado"
```

---

### Task 10: Verificação Final

**Step 1: Rodar todos os testes**
```bash
make test
```
Esperado: todos os testes passam, sem regressões.

**Step 2: Rodar lint**
```bash
make lint
```
Esperado: sem erros.

**Step 3: Commit de encerramento (se necessário)**
```bash
git add -A
git commit -m "feat(observacoes): feature completa — backend + frontend"
```
