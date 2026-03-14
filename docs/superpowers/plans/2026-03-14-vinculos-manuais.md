# Vínculos Manuais entre Pessoas — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que operadores cadastrem vínculos manuais (ex: "Irmão", "Sócio") entre pessoas na ficha de detalhe, com tipo obrigatório e descrição opcional.

**Architecture:** Nova tabela `vinculos_manuais` independente de `relacionamento_pessoas`. Três novos métodos em `PessoaService`. Dois novos endpoints REST. Container de vínculos no frontend dividido em duas seções com modal de cadastro.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.0 async / Alembic / Alpine.js / Tailwind

> **Nota YAGNI:** O assembly de `PessoaDetail` no router é mantido como está (padrão estabelecido). Os vínculos manuais são adicionados seguindo o mesmo padrão existente para os vínculos automáticos — sem refatoração do código de assembly existente.

---

## Chunk 1: Backend — Model, Schemas, Migration

### Task 1: Model `VinculoManual`

**Files:**
- Create: `app/models/vinculo_manual.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1.1: Criar `app/models/vinculo_manual.py`**

```python
"""Modelo de VinculoManual — vínculo entre pessoas cadastrado manualmente.

Define relacionamentos manuais entre pessoas, registrados pelo operador
com tipo (ex: 'Irmão') e descrição opcional, independente de abordagens.
"""

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, MultiTenantMixin, SoftDeleteMixin, TimestampMixin


class VinculoManual(Base, TimestampMixin, SoftDeleteMixin, MultiTenantMixin):
    """Vínculo manual entre duas pessoas, cadastrado pelo operador.

    Registra relacionamentos conhecidos operacionalmente que não constam
    em abordagens. Diferente de RelacionamentoPessoa, não tem direção
    forçada (A→B e B→A são registros distintos e ambos permitidos).

    Attributes:
        id: Identificador único.
        pessoa_id: ID da pessoa dona do vínculo (quem está sendo visualizado).
        pessoa_vinculada_id: ID da pessoa vinculada.
        tipo: Tipo do vínculo — palavra curta obrigatória (ex: 'Irmão').
        descricao: Detalhe livre opcional (ex: 'Traficando junto na casa ao lado').
        guarnicao_id: Guarnição (herdado de MultiTenantMixin).

    Nota:
        - UNIQUE(pessoa_id, pessoa_vinculada_id) evita duplicatas.
        - CHECK(pessoa_id != pessoa_vinculada_id) impede auto-vínculo.
        - Soft delete via SoftDeleteMixin (ativo, desativado_em, desativado_por_id).
    """

    __tablename__ = "vinculos_manuais"

    id: Mapped[int] = mapped_column(primary_key=True)
    pessoa_id: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True
    )
    pessoa_vinculada_id: Mapped[int] = mapped_column(
        ForeignKey("pessoas.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(100))
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    pessoa = relationship(
        "Pessoa",
        foreign_keys=[pessoa_id],
        back_populates="vinculos_manuais",
    )
    # lazy="selectin" é obrigatório: o router acessa .pessoa_vinculada.nome
    # e .foto_principal_url em contexto async — sem selectin causaria MissingGreenlet.
    pessoa_vinculada = relationship(
        "Pessoa",
        foreign_keys=[pessoa_vinculada_id],
        lazy="selectin",
    )

    __table_args__ = (
        # Constraint padrão sem filtro ativo — consistente com RelacionamentoPessoa.
        # Registro soft-deleted mantém o slot único (comportamento intencional:
        # vínculo excluído não deve ser recriado silenciosamente).
        # pessoa_id e pessoa_vinculada_id são PKs globais (não por tenant),
        # portanto UNIQUE(pessoa_id, pessoa_vinculada_id) é naturalmente
        # tenant-scoped sem incluir guarnicao_id.
        UniqueConstraint("pessoa_id", "pessoa_vinculada_id", name="uq_vinculo_manual"),
        CheckConstraint("pessoa_id != pessoa_vinculada_id", name="ck_vinculo_manual_diferente"),
        # Índices explícitos além dos gerados por index=True nos campos.
        # guarnicao_id já é indexado pelo MultiTenantMixin via index=True.
        Index("idx_vinculo_manual_pessoa", "pessoa_id"),
        Index("idx_vinculo_manual_vinculada", "pessoa_vinculada_id"),
    )
```

- [ ] **Step 1.2: Adicionar `vinculos_manuais` no model `Pessoa`**

Em `app/models/pessoa.py`, adicionar o relationship após `relacionamentos_como_b`.
O atributo se chama `vinculos_manuais` e o `back_populates` deve bater com o nome do
relationship em `VinculoManual` (que usa `back_populates="vinculos_manuais"`):

```python
# após relacionamentos_como_b = relationship(...)
vinculos_manuais = relationship(
    "VinculoManual",
    foreign_keys="VinculoManual.pessoa_id",
    back_populates="pessoa",
    lazy="selectin",
)
```

> **`back_populates` summary:**
> - `VinculoManual.pessoa` ↔ `Pessoa.vinculos_manuais` (via `pessoa_id`)
> - `VinculoManual.pessoa_vinculada` — sem `back_populates` (leitura apenas)

- [ ] **Step 1.3: Registrar no `app/models/__init__.py`**

Adicionar ao final das importações:

```python
from app.models.vinculo_manual import VinculoManual  # noqa: F401
```

- [ ] **Step 1.4: Commit**

```bash
git add app/models/vinculo_manual.py app/models/__init__.py app/models/pessoa.py
git commit -m "feat(model): adicionar VinculoManual para vínculos manuais entre pessoas"
```

---

### Task 2: Schemas

**Files:**
- Create: `app/schemas/vinculo_manual.py`
- Modify: `app/schemas/pessoa.py`

- [ ] **Step 2.1: Criar `app/schemas/vinculo_manual.py`**

```python
"""Schemas Pydantic para vínculos manuais entre pessoas.

Define estruturas de requisição e resposta para criação e leitura
de vínculos manuais cadastrados pelo operador.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VinculoManualCreate(BaseModel):
    """Requisição de criação de vínculo manual.

    Attributes:
        pessoa_vinculada_id: ID da pessoa a ser vinculada.
        tipo: Tipo do vínculo (ex: 'Irmão', 'Pai', 'Sócio'). Obrigatório.
        descricao: Detalhe adicional sobre o vínculo (opcional).
    """

    pessoa_vinculada_id: int
    tipo: str = Field(..., min_length=1, max_length=100)
    descricao: str | None = Field(None, max_length=500)


class VinculoManualRead(BaseModel):
    """Dados de leitura de vínculo manual.

    Attributes:
        id: Identificador único do vínculo.
        pessoa_vinculada_id: ID da pessoa vinculada.
        nome: Nome da pessoa vinculada.
        foto_principal_url: URL da foto da pessoa vinculada (para exibição).
        tipo: Tipo do vínculo (ex: 'Irmão').
        descricao: Detalhe adicional sobre o vínculo.
        criado_em: Timestamp de criação do vínculo.
    """

    id: int
    pessoa_vinculada_id: int
    nome: str
    foto_principal_url: str | None = None
    tipo: str
    descricao: str | None = None
    criado_em: datetime

    model_config = {"from_attributes": True}
```

> **Nota sobre `nome` e `foto_principal_url`:** Esses campos não existem no model `VinculoManual` — vêm da `Pessoa` vinculada. O `from_attributes=True` não resolve relacionamentos automaticamente. **Os valores são preenchidos explicitamente pelo router** quando constrói `VinculoManualRead(nome=vm.pessoa_vinculada.nome, ...)`. O `model_config` está correto mas não é suficiente sozinho — ver Task 5.

> **Não há import circular:** `vinculo_manual.py` (schema) não importa nada de `pessoa.py`. A dependência é de mão única: `pessoa.py` importa `VinculoManualRead` de `vinculo_manual.py`.

- [ ] **Step 2.2: Adicionar `vinculos_manuais` em `PessoaDetail` (`app/schemas/pessoa.py`)**

Adicionar import no topo do arquivo:
```python
from app.schemas.vinculo_manual import VinculoManualRead
```

Adicionar campo em `PessoaDetail`:
```python
vinculos_manuais: list[VinculoManualRead] = []
```

Atualizar docstring do campo `relacionamentos` em `PessoaDetail`:
```
vinculos_manuais: Lista de vínculos manuais cadastrados pelo operador.
```

- [ ] **Step 2.3: Commit**

```bash
git add app/schemas/vinculo_manual.py app/schemas/pessoa.py
git commit -m "feat(schema): adicionar VinculoManualCreate, VinculoManualRead e campo em PessoaDetail"
```

---

### Task 3: Migration Alembic

**Files:**
- Create: `alembic/versions/<hash>_adicionar_vinculos_manuais.py`

- [ ] **Step 3.1: Gerar migration**

```bash
make migrate msg="adicionar vinculos manuais"
```

- [ ] **Step 3.2: Verificar migration gerada**

Abra o arquivo gerado em `alembic/versions/`. Confirme que contém:
- Criação da tabela `vinculos_manuais`
- Campos: `id`, `pessoa_id`, `pessoa_vinculada_id`, `tipo`, `descricao`, `guarnicao_id`, `ativo`, `desativado_em`, `desativado_por_id`, `criado_em`, `atualizado_em`
- Constraints: `uq_vinculo_manual`, `ck_vinculo_manual_diferente`
- FKs para `pessoas.id` e `guarnicoes.id`

Se algum campo estiver faltando, edite a migration manualmente.

- [ ] **Step 3.3: Aplicar migration no banco de desenvolvimento**

```bash
docker compose exec api alembic upgrade head
# ou se rodando local:
alembic upgrade head
```

Esperado: `Running upgrade ... -> <hash>, adicionar vinculos manuais`

- [ ] **Step 3.4: Commit**

```bash
git add alembic/versions/
git commit -m "feat(migration): criar tabela vinculos_manuais"
```

---

## Chunk 2: Backend — Service + Endpoints + Testes

### Task 4: Métodos de service + testes unitários

**Files:**
- Modify: `app/services/pessoa_service.py`
- Create: `tests/unit/test_vinculo_manual_service.py`

- [ ] **Step 4.1: Escrever testes unitários primeiro**

Criar `tests/unit/test_vinculo_manual_service.py`:

```python
"""Testes unitários para métodos de vínculo manual em PessoaService.

Verifica criação, listagem e remoção de vínculos manuais com
isolamento multi-tenant e auditoria.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AcessoNegadoError, ConflitoDadosError, NaoEncontradoError
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.vinculo_manual import VinculoManual
from app.schemas.vinculo_manual import VinculoManualCreate
from app.services.pessoa_service import PessoaService


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


def make_pessoa(id: int, guarnicao_id: int = 1) -> Pessoa:
    """Cria pessoa mock para testes.

    Args:
        id: ID da pessoa.
        guarnicao_id: ID da guarnição da pessoa.

    Returns:
        Pessoa mock com id, guarnicao_id e ativo=True.
    """
    p = MagicMock(spec=Pessoa)
    p.id = id
    p.guarnicao_id = guarnicao_id
    p.ativo = True
    p.nome = f"Pessoa {id}"
    p.foto_principal_url = None
    return p


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
    """Fixture de PessoaService com db mock.

    Args:
        db: Sessão mock do banco.

    Returns:
        PessoaService com repositório e audit mockados.
    """
    svc = PessoaService(db)
    svc.repo = AsyncMock()
    svc.audit = AsyncMock()
    return svc


class TestCriarVinculoManual:
    """Testes para PessoaService.criar_vinculo_manual."""

    async def test_cria_vinculo_com_sucesso(self, service):
        """Testa criação de vínculo manual retorna VinculoManual.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        vinculada = make_pessoa(id=2, guarnicao_id=1)
        service.repo.get = AsyncMock(side_effect=[pessoa, vinculada])

        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Irmão", descricao="Mora junto")
        result = await service.criar_vinculo_manual(1, data, user)

        assert isinstance(result, VinculoManual)
        assert result.pessoa_id == 1
        assert result.pessoa_vinculada_id == 2
        assert result.tipo == "Irmão"
        assert result.descricao == "Mora junto"
        service.audit.log.assert_awaited_once()

    async def test_pessoa_nao_encontrada_levanta_erro(self, service):
        """Testa que NaoEncontradoError é levantado se pessoa não existe.

        Args:
            service: PessoaService com mocks.
        """
        service.repo.get = AsyncMock(return_value=None)
        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Irmão")

        with pytest.raises(NaoEncontradoError):
            await service.criar_vinculo_manual(999, data, make_user())

    async def test_vinculada_outra_guarnicao_levanta_acesso_negado(self, service):
        """Testa que AcessoNegadoError é levantado se vinculada é de outra guarnição.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        vinculada_outra = make_pessoa(id=2, guarnicao_id=99)
        service.repo.get = AsyncMock(side_effect=[pessoa, vinculada_outra])

        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Sócio")

        with pytest.raises(AcessoNegadoError):
            await service.criar_vinculo_manual(1, data, user)

    async def test_vinculo_duplicado_levanta_conflito(self, service):
        """Testa que ConflitoDadosError é levantado em duplicata.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        pessoa = make_pessoa(id=1, guarnicao_id=1)
        vinculada = make_pessoa(id=2, guarnicao_id=1)
        service.repo.get = AsyncMock(side_effect=[pessoa, vinculada])
        service.db.flush = AsyncMock(side_effect=IntegrityError(None, None, None))
        service.db.rollback = AsyncMock()

        data = VinculoManualCreate(pessoa_vinculada_id=2, tipo="Irmão")

        with pytest.raises(ConflitoDadosError):
            await service.criar_vinculo_manual(1, data, user)


class TestRemoverVinculoManual:
    """Testes para PessoaService.remover_vinculo_manual."""

    async def test_remove_vinculo_com_soft_delete(self, service):
        """Testa que remoção executa soft delete corretamente.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        vinculo = MagicMock(spec=VinculoManual)
        vinculo.id = 5
        vinculo.ativo = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = vinculo
        service.db.execute = AsyncMock(return_value=mock_result)

        await service.remover_vinculo_manual(5, 1, user)

        assert vinculo.ativo is False
        assert vinculo.desativado_por_id == user.id
        assert vinculo.desativado_em is not None
        service.audit.log.assert_awaited_once()

    async def test_vinculo_nao_encontrado_levanta_erro(self, service):
        """Testa que NaoEncontradoError é levantado se vínculo não existe.

        Args:
            service: PessoaService com mocks.
        """
        user = make_user(guarnicao_id=1)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        service.db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(NaoEncontradoError):
            await service.remover_vinculo_manual(999, 1, user)
```

- [ ] **Step 4.2: Rodar testes — devem falhar**

```bash
pytest tests/unit/test_vinculo_manual_service.py -v
```

Esperado: `FAILED` — métodos não existem ainda.

- [ ] **Step 4.3: Implementar métodos em `app/services/pessoa_service.py`**

Adicionar imports no topo do arquivo:
```python
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AcessoNegadoError, ConflitoDadosError, NaoEncontradoError
from app.models.vinculo_manual import VinculoManual
from app.schemas.vinculo_manual import VinculoManualCreate
```

> Nota: `NaoEncontradoError` e `ConflitoDadosError` já estão importados — não duplicar. Adicionar apenas `AcessoNegadoError`, `select`, `IntegrityError`, `VinculoManual`, `VinculoManualCreate`, `UTC`, `datetime` se ainda não presentes.

Adicionar os três métodos ao final da classe `PessoaService`:

```python
async def criar_vinculo_manual(
    self,
    pessoa_id: int,
    data: VinculoManualCreate,
    user: Usuario,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> VinculoManual:
    """Cria vínculo manual entre duas pessoas com validação de tenant.

    Verifica que ambas as pessoas pertencem à mesma guarnição antes
    de criar. Captura IntegrityError do banco para duplicatas.
    Registra auditoria na criação.

    Args:
        pessoa_id: ID da pessoa dona do vínculo.
        data: Dados do vínculo (pessoa_vinculada_id, tipo, descricao).
        user: Usuário autenticado.
        ip_address: IP da requisição para auditoria.
        user_agent: User-Agent para auditoria.

    Returns:
        VinculoManual criado.

    Raises:
        NaoEncontradoError: Se pessoa ou pessoa vinculada não existem.
        AcessoNegadoError: Se pessoa não pertence à guarnição do user,
            ou se pessoa vinculada pertence a outra guarnição.
        ConflitoDadosError: Se vínculo já existe (UNIQUE constraint).
    """
    pessoa = await self.repo.get(pessoa_id)
    if not pessoa:
        raise NaoEncontradoError("Pessoa")
    TenantFilter.check_ownership(pessoa, user)

    vinculada = await self.repo.get(data.pessoa_vinculada_id)
    if not vinculada:
        raise NaoEncontradoError("Pessoa vinculada")
    if vinculada.guarnicao_id != user.guarnicao_id:
        raise AcessoNegadoError("Pessoa vinculada pertence a outra guarnição")

    vinculo = VinculoManual(
        pessoa_id=pessoa_id,
        pessoa_vinculada_id=data.pessoa_vinculada_id,
        tipo=data.tipo,
        descricao=data.descricao,
        guarnicao_id=user.guarnicao_id,
    )
    self.db.add(vinculo)
    try:
        await self.db.flush()
    except IntegrityError:
        await self.db.rollback()
        raise ConflitoDadosError("Vínculo já cadastrado entre essas pessoas")

    await self.audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="vinculo_manual",
        recurso_id=vinculo.id,
        detalhes={
            "pessoa_id": pessoa_id,
            "pessoa_vinculada_id": data.pessoa_vinculada_id,
            "tipo": data.tipo,
        },
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return vinculo

async def listar_vinculos_manuais(
    self,
    pessoa_id: int,
    user: Usuario,
) -> list[VinculoManual]:
    """Lista vínculos manuais ativos de uma pessoa.

    Filtra por pessoa_id e guarnicao_id do user, excluindo
    registros com soft delete (ativo=False).

    Args:
        pessoa_id: ID da pessoa.
        user: Usuário autenticado (para filtro de guarnição).

    Returns:
        Lista de VinculoManual ativos da pessoa.
    """
    query = select(VinculoManual).where(
        VinculoManual.pessoa_id == pessoa_id,
        VinculoManual.guarnicao_id == user.guarnicao_id,
        VinculoManual.ativo == True,  # noqa: E712
    )
    result = await self.db.execute(query)
    return list(result.scalars().all())

async def remover_vinculo_manual(
    self,
    vinculo_id: int,
    pessoa_id: int,
    user: Usuario,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Remove vínculo manual com soft delete.

    Marca o vínculo como inativo sem remoção física. Verifica
    que o vínculo pertence à guarnição do usuário.

    Args:
        vinculo_id: ID do vínculo a remover.
        pessoa_id: ID da pessoa dona do vínculo (validação extra).
        user: Usuário autenticado.
        ip_address: IP da requisição para auditoria.
        user_agent: User-Agent para auditoria.

    Raises:
        NaoEncontradoError: Se vínculo não existe ou não pertence
            à guarnição do user.
    """
    query = select(VinculoManual).where(
        VinculoManual.id == vinculo_id,
        VinculoManual.pessoa_id == pessoa_id,
        VinculoManual.guarnicao_id == user.guarnicao_id,
        VinculoManual.ativo == True,  # noqa: E712
    )
    result = await self.db.execute(query)
    vinculo = result.scalar_one_or_none()
    if not vinculo:
        raise NaoEncontradoError("Vínculo manual")

    vinculo.ativo = False
    vinculo.desativado_em = datetime.now(UTC)
    vinculo.desativado_por_id = user.id
    await self.db.flush()

    await self.audit.log(
        usuario_id=user.id,
        acao="DELETE",
        recurso="vinculo_manual",
        recurso_id=vinculo_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
```

- [ ] **Step 4.4: Rodar testes — devem passar**

```bash
pytest tests/unit/test_vinculo_manual_service.py -v
```

Esperado: todos `PASSED`.

- [ ] **Step 4.5: Commit**

```bash
git add app/services/pessoa_service.py tests/unit/test_vinculo_manual_service.py
git commit -m "feat(service): adicionar criar/listar/remover vínculo manual em PessoaService"
```

---

### Task 5: Endpoints REST + testes de integração

**Files:**
- Modify: `app/api/v1/pessoas.py`
- Create: `tests/integration/test_api_vinculos_manuais.py`

- [ ] **Step 5.1: Escrever testes de integração primeiro**

Criar `tests/integration/test_api_vinculos_manuais.py`:

```python
"""Testes de integração para endpoints de vínculos manuais.

Testa criação, listagem via detalhe e remoção de vínculos manuais,
incluindo isolamento multi-tenant.
"""

import pytest
from httpx import AsyncClient


class TestCriarVinculoManual:
    """Testes do endpoint POST /api/v1/pessoas/{id}/vinculos-manuais."""

    async def test_criar_vinculo_sucesso(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa criação de vínculo manual retorna 201 com dados corretos.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={
                "pessoa_vinculada_id": outra_pessoa.id,
                "tipo": "Irmão",
                "descricao": "Mora junto",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tipo"] == "Irmão"
        assert data["descricao"] == "Mora junto"
        assert data["pessoa_vinculada_id"] == outra_pessoa.id
        assert data["nome"] == outra_pessoa.nome
        assert "id" in data
        assert "criado_em" in data

    async def test_criar_vinculo_sem_descricao(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que descrição é opcional.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Sócio"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["descricao"] is None

    async def test_criar_vinculo_duplicado_retorna_409(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que vínculo duplicado retorna 409.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        payload = {"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Amigo"}
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json=payload,
            headers=auth_headers,
        )
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_criar_sem_auth_retorna_403(
        self,
        client: AsyncClient,
        pessoa,
        outra_pessoa,
    ):
        """Testa que requisição sem token retorna 403.

        Args:
            client: Cliente HTTP assincrónico.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Amigo"},
        )
        assert response.status_code == 403

    async def test_tipo_obrigatorio_retorna_422(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que tipo ausente retorna 422.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        response = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestVinculoManualNoDetalhe:
    """Testes de vinculos_manuais em GET /api/v1/pessoas/{id}."""

    async def test_detalhe_inclui_vinculos_manuais(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que detalhe da pessoa inclui campo vinculos_manuais.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Pai"},
            headers=auth_headers,
        )
        response = await client.get(
            f"/api/v1/pessoas/{pessoa.id}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "vinculos_manuais" in data
        assert len(data["vinculos_manuais"]) == 1
        assert data["vinculos_manuais"][0]["tipo"] == "Pai"
        assert data["vinculos_manuais"][0]["nome"] == outra_pessoa.nome


class TestRemoverVinculoManual:
    """Testes do endpoint DELETE /api/v1/pessoas/{id}/vinculos-manuais/{vid}."""

    async def test_remover_vinculo_retorna_204(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa remoção de vínculo retorna 204.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Amigo"},
            headers=auth_headers,
        )
        vinculo_id = create_resp.json()["id"]

        response = await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais/{vinculo_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    async def test_vinculo_removido_nao_aparece_no_detalhe(
        self,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
        outra_pessoa,
    ):
        """Testa que vínculo removido não aparece mais no detalhe.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa da guarnição.
            outra_pessoa: Fixture de outra pessoa da mesma guarnição.
        """
        create_resp = await client.post(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais",
            json={"pessoa_vinculada_id": outra_pessoa.id, "tipo": "Ex-sócio"},
            headers=auth_headers,
        )
        vinculo_id = create_resp.json()["id"]

        await client.delete(
            f"/api/v1/pessoas/{pessoa.id}/vinculos-manuais/{vinculo_id}",
            headers=auth_headers,
        )

        detail_resp = await client.get(
            f"/api/v1/pessoas/{pessoa.id}", headers=auth_headers
        )
        vinculos = detail_resp.json()["vinculos_manuais"]
        assert all(v["id"] != vinculo_id for v in vinculos)
```

> **Nota sobre fixtures:** Os testes usam fixtures `pessoa` e `outra_pessoa`. Verifique se `tests/conftest.py` já tem essas fixtures ou adicione-as. Se `conftest.py` já tem fixture `pessoa`, use-a. Caso contrário, adicione em `tests/integration/test_api_vinculos_manuais.py`:

```python
@pytest.fixture
async def pessoa(db_session, guarnicao):
    """Fixture de pessoa da guarnição para testes.

    Args:
        db_session: Sessão do banco de teste.
        guarnicao: Guarnição de teste.

    Returns:
        Pessoa criada no banco de teste.
    """
    from app.models.pessoa import Pessoa
    p = Pessoa(nome="Pessoa Teste", guarnicao_id=guarnicao.id)
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def outra_pessoa(db_session, guarnicao):
    """Fixture de segunda pessoa da mesma guarnição.

    Args:
        db_session: Sessão do banco de teste.
        guarnicao: Guarnição de teste.

    Returns:
        Segunda pessoa criada no banco de teste.
    """
    from app.models.pessoa import Pessoa
    p = Pessoa(nome="Outra Pessoa Teste", guarnicao_id=guarnicao.id)
    db_session.add(p)
    await db_session.flush()
    return p
```

- [ ] **Step 5.2: Rodar testes — devem falhar**

```bash
pytest tests/integration/test_api_vinculos_manuais.py -v
```

Esperado: `FAILED` — endpoints não existem.

- [ ] **Step 5.3: Adicionar imports e endpoints em `app/api/v1/pessoas.py`**

Adicionar imports novos no topo:
```python
from app.schemas.vinculo_manual import VinculoManualCreate, VinculoManualRead
```

Adicionar dois novos endpoints ao final do arquivo:

```python
@router.post(
    "/{pessoa_id}/vinculos-manuais",
    response_model=VinculoManualRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def criar_vinculo_manual(
    request: Request,
    pessoa_id: int,
    data: VinculoManualCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VinculoManualRead:
    """Cria vínculo manual entre duas pessoas.

    Permite registrar relacionamentos conhecidos operacionalmente
    que não constam em abordagens (ex: 'Irmão', 'Sócio').

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona do vínculo.
        data: Dados do vínculo (pessoa_vinculada_id, tipo, descricao).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        VinculoManualRead com dados do vínculo criado.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa vinculada é de outra guarnição.
        ConflitoDadosError: Se vínculo já cadastrado.

    Status Code:
        201: Vínculo criado.
        403: Acesso negado.
        404: Pessoa não encontrada.
        409: Vínculo duplicado.
        422: Dados inválidos (tipo ausente, etc).
        429: Rate limit.
    """
    service = PessoaService(db)
    vinculo = await service.criar_vinculo_manual(
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    vinculada = vinculo.pessoa_vinculada
    return VinculoManualRead(
        id=vinculo.id,
        pessoa_vinculada_id=vinculo.pessoa_vinculada_id,
        nome=vinculada.nome if vinculada else "",
        foto_principal_url=vinculada.foto_principal_url if vinculada else None,
        tipo=vinculo.tipo,
        descricao=vinculo.descricao,
        criado_em=vinculo.criado_em,
    )


@router.delete(
    "/{pessoa_id}/vinculos-manuais/{vinculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remover_vinculo_manual(
    request: Request,
    pessoa_id: int,
    vinculo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Remove vínculo manual (soft delete).

    Marca o vínculo como inativo sem remoção física. Registra auditoria.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona do vínculo.
        vinculo_id: ID do vínculo a remover.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Raises:
        NaoEncontradoError: Se vínculo não existe ou não pertence à guarnição.

    Status Code:
        204: Vínculo removido.
        404: Vínculo não encontrado.
    """
    service = PessoaService(db)
    await service.remover_vinculo_manual(
        vinculo_id,
        pessoa_id,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
```

- [ ] **Step 5.4: Atualizar `detalhe_pessoa` para incluir `vinculos_manuais`**

No endpoint `detalhe_pessoa` existente, adicionar carregamento de vínculos manuais logo após montar `vinculos`:

```python
# Após: for rel in pessoa.relacionamentos_como_b: ...

# Carregar vínculos manuais
vinculos_manuais_db = await service.listar_vinculos_manuais(pessoa_id, user)
vinculos_manuais = [
    VinculoManualRead(
        id=vm.id,
        pessoa_vinculada_id=vm.pessoa_vinculada_id,
        nome=vm.pessoa_vinculada.nome if vm.pessoa_vinculada else "",
        foto_principal_url=vm.pessoa_vinculada.foto_principal_url if vm.pessoa_vinculada else None,
        tipo=vm.tipo,
        descricao=vm.descricao,
        criado_em=vm.criado_em,
    )
    for vm in vinculos_manuais_db
]
```

E adicionar `vinculos_manuais=vinculos_manuais` no `return PessoaDetail(...)`.

- [ ] **Step 5.5: Rodar testes — devem passar**

```bash
pytest tests/integration/test_api_vinculos_manuais.py -v
```

Esperado: todos `PASSED`.

- [ ] **Step 5.6: Rodar suite completa para garantir não-regressão**

```bash
pytest tests/ -v --tb=short
```

Esperado: todos os testes existentes continuam passando.

- [ ] **Step 5.7: Commit**

```bash
git add app/api/v1/pessoas.py tests/integration/test_api_vinculos_manuais.py
git commit -m "feat(api): adicionar endpoints de vínculo manual em /pessoas"
```

---

## Chunk 3: Frontend

### Task 6: Atualizar `pessoa-detalhe.js`

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

- [ ] **Step 6.1: Adicionar estado Alpine.js**

Na função `pessoaDetalhePage(pessoaId)`, dentro do objeto retornado, adicionar após `_mapaObserver: null`:

```js
// Vínculos manuais
vinculosManuais: [],
modalVinculo: false,
buscaVinculo: '',
resultadosBusca: [],
buscandoPessoa: false,
pessoaSelecionada: null,
novoVinculo: { tipo: '', descricao: '' },
subFormNovaPessoa: false,
novaPessoaForm: { nome: '', cpf: '', apelido: '', data_nascimento: '' },
_buscaTimer: null,
```

- [ ] **Step 6.2: Carregar `vinculos_manuais` no `load()`**

No método `load()`, após `this.pessoa = await api.get(...)`, adicionar:

```js
this.vinculosManuais = this.pessoa.vinculos_manuais || [];
```

- [ ] **Step 6.3: Adicionar métodos de vínculo manual**

Após o método `goBack()`, adicionar os novos métodos:

```js
// ------- Vínculos Manuais -------

abrirModalVinculo() {
  this.modalVinculo = true;
  this.buscaVinculo = '';
  this.resultadosBusca = [];
  this.pessoaSelecionada = null;
  this.novoVinculo = { tipo: '', descricao: '' };
  this.subFormNovaPessoa = false;
  this.novaPessoaForm = { nome: '', cpf: '', apelido: '', data_nascimento: '' };
},

fecharModalVinculo() {
  this.modalVinculo = false;
},

onBuscaVinculo() {
  clearTimeout(this._buscaTimer);
  const q = this.buscaVinculo.trim();
  if (q.length < 2) { this.resultadosBusca = []; return; }
  this._buscaTimer = setTimeout(() => this._executarBusca(q), 400);
},

async _executarBusca(q) {
  this.buscandoPessoa = true;
  try {
    const results = await api.get(`/pessoas?nome=${encodeURIComponent(q)}&limit=5`);
    // Excluir a própria pessoa da lista
    // pessoaId é closure da função pessoaDetalhePage(pessoaId) — NÃO usar ${} aqui
    this.resultadosBusca = results.filter(p => p.id !== pessoaId);
  } catch { this.resultadosBusca = []; }
  finally { this.buscandoPessoa = false; }
},

selecionarPessoa(p) {
  this.pessoaSelecionada = p;
  this.resultadosBusca = [];
  this.subFormNovaPessoa = false;
},

iniciarCadastroNovo() {
  this.pessoaSelecionada = null;
  this.subFormNovaPessoa = true;
  this.novaPessoaForm.nome = this.buscaVinculo.trim();
},

async cadastrarNovaPessoa() {
  if (!this.novaPessoaForm.nome.trim()) return;
  try {
    const nova = await api.post('/pessoas/', {
      nome: this.novaPessoaForm.nome,
      cpf: this.novaPessoaForm.cpf || undefined,
      apelido: this.novaPessoaForm.apelido || undefined,
      data_nascimento: this.novaPessoaForm.data_nascimento || undefined,
    });
    this.selecionarPessoa(nova);
  } catch (err) {
    alert(err.message || 'Erro ao cadastrar pessoa.');
  }
},

async salvarVinculo() {
  if (!this.pessoaSelecionada || !this.novoVinculo.tipo.trim()) return;
  try {
    const vinculo = await api.post(`/pessoas/${pessoaId}/vinculos-manuais`, {
      pessoa_vinculada_id: this.pessoaSelecionada.id,
      tipo: this.novoVinculo.tipo.trim(),
      descricao: this.novoVinculo.descricao.trim() || undefined,
    });
    this.vinculosManuais.unshift(vinculo);
    this.fecharModalVinculo();
  } catch (err) {
    alert(err.message || 'Erro ao salvar vínculo.');
  }
},
```

- [ ] **Step 6.4: Substituir container de vínculos no HTML**

Em `renderPessoaDetalhe`, substituir o bloco:

```html
<!-- Relacionamentos (vínculos) -->
<div x-show="pessoa.relacionamentos?.length > 0" class="card space-y-2">
  <h3 class="text-sm font-semibold text-slate-300">
    Vínculos (<span x-text="pessoa.relacionamentos.length"></span>)
  </h3>
  ...bloco existente...
</div>
```

pelo novo bloco unificado:

```html
<!-- Vínculos (automáticos + manuais) -->
<div class="card space-y-2">
  <div class="flex items-center justify-between">
    <h3 class="text-sm font-semibold text-slate-300">Vínculos</h3>
    <button @click="abrirModalVinculo()"
            class="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded transition-colors">
      + Adicionar
    </button>
  </div>

  <!-- Seção 1: Vínculos em Abordagem -->
  <div x-show="pessoa.relacionamentos?.length > 0" class="space-y-1">
    <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
      Vínculos em Abordagem (<span x-text="pessoa.relacionamentos.length"></span>)
    </p>
    <div class="space-y-2">
      <template x-for="rel in pessoa.relacionamentos" :key="rel.pessoa_id">
        <div @click="viewPessoa(rel.pessoa_id)"
             class="flex items-center justify-between border border-slate-700/40 border-l-4 border-l-orange-500 rounded-lg p-3 cursor-pointer hover:bg-slate-800/50">
          <div class="flex items-center gap-2">
            <template x-if="rel.foto_principal_url">
              <img :src="rel.foto_principal_url"
                   class="w-8 h-8 rounded-full object-cover border-2 border-slate-600 shrink-0"
                   loading="lazy">
            </template>
            <template x-if="!rel.foto_principal_url">
              <div class="w-8 h-8 rounded-full bg-slate-700 border-2 border-slate-600 flex items-center justify-center text-slate-400 shrink-0">
                <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                </svg>
              </div>
            </template>
            <span class="text-sm text-slate-300" x-text="rel.nome"></span>
          </div>
          <div class="text-right">
            <span class="text-xs text-blue-400 font-medium" x-text="rel.frequencia + 'x juntos'"></span>
            <p x-show="rel.ultima_vez" class="text-[10px] text-slate-500"
               x-text="'Última: ' + new Date(rel.ultima_vez).toLocaleDateString('pt-BR')"></p>
          </div>
        </div>
      </template>
    </div>
  </div>

  <!-- Separador (só quando ambas as seções têm itens) -->
  <div x-show="pessoa.relacionamentos?.length > 0 && vinculosManuais.length > 0"
       class="border-t border-slate-700/50"></div>

  <!-- Seção 2: Vínculos Manuais -->
  <div x-show="vinculosManuais.length > 0" class="space-y-1">
    <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
      Vínculos Manuais (<span x-text="vinculosManuais.length"></span>)
    </p>
    <div class="space-y-2">
      <template x-for="vm in vinculosManuais" :key="vm.id">
        <div @click="viewPessoa(vm.pessoa_vinculada_id)"
             class="flex items-start justify-between border border-slate-700/40 border-l-4 border-l-purple-500 rounded-lg p-3 cursor-pointer hover:bg-slate-800/50">
          <div class="flex items-start gap-2">
            <template x-if="vm.foto_principal_url">
              <img :src="vm.foto_principal_url"
                   class="w-8 h-8 rounded-full object-cover border-2 border-slate-600 shrink-0 mt-0.5"
                   loading="lazy">
            </template>
            <template x-if="!vm.foto_principal_url">
              <div class="w-8 h-8 rounded-full bg-slate-700 border-2 border-slate-600 flex items-center justify-center text-slate-400 shrink-0 mt-0.5">
                <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                </svg>
              </div>
            </template>
            <div>
              <span class="text-sm text-slate-300" x-text="vm.nome"></span>
              <p class="text-xs text-purple-400 font-semibold mt-0.5" x-text="vm.tipo"></p>
              <p x-show="vm.descricao"
                 class="text-xs text-slate-400 italic mt-0.5"
                 x-text="'&quot;' + vm.descricao + '&quot;'"></p>
            </div>
          </div>
          <span x-show="vm.criado_em" class="text-[10px] text-slate-500 shrink-0 ml-2"
                x-text="new Date(vm.criado_em).toLocaleDateString('pt-BR')"></span>
        </div>
      </template>
    </div>
  </div>

  <!-- Mensagem quando não há vínculos -->
  <div x-show="!pessoa.relacionamentos?.length && !vinculosManuais.length"
       class="text-xs text-slate-500 text-center py-2">
    Nenhum vínculo cadastrado
  </div>
</div>
```

- [ ] **Step 6.5: Adicionar modal de cadastro no HTML**

Em `renderPessoaDetalhe`, após o modal de `pessoaPreview` (linha ~138), adicionar:

```html
<!-- Modal de cadastro de vínculo manual -->
<div x-show="modalVinculo" x-cloak
     @click.self="fecharModalVinculo()"
     class="fixed inset-0 bg-black/60 z-50 flex items-end justify-center sm:items-center p-4">
  <div class="bg-slate-800 border border-slate-600 rounded-2xl p-5 w-full max-w-sm space-y-4"
       @click.stop>
    <div class="flex items-center justify-between">
      <h3 class="text-base font-semibold text-slate-100">Cadastrar Vínculo Manual</h3>
      <button @click="fecharModalVinculo()" class="text-slate-400 hover:text-slate-200 text-lg leading-none">&times;</button>
    </div>

    <!-- Busca de pessoa -->
    <div x-show="!pessoaSelecionada && !subFormNovaPessoa">
      <label class="text-xs text-slate-400 font-medium block mb-1">Buscar pessoa</label>
      <input type="text"
             x-model="buscaVinculo"
             @input="onBuscaVinculo()"
             placeholder="Nome, apelido ou CPF..."
             class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">

      <!-- Loading -->
      <div x-show="buscandoPessoa" class="flex justify-center py-2">
        <span class="spinner"></span>
      </div>

      <!-- Resultados -->
      <div x-show="resultadosBusca.length > 0 || (buscaVinculo.trim().length >= 2 && !buscandoPessoa)"
           class="mt-1 bg-slate-700 border border-slate-600 rounded-lg overflow-hidden">
        <template x-for="p in resultadosBusca" :key="p.id">
          <div @click="selecionarPessoa(p)"
               class="flex items-center gap-2 px-3 py-2 border-b border-slate-600 last:border-0 cursor-pointer hover:bg-slate-600 transition-colors">
            <template x-if="p.foto_principal_url">
              <img :src="p.foto_principal_url" class="w-7 h-7 rounded-full object-cover">
            </template>
            <template x-if="!p.foto_principal_url">
              <div class="w-7 h-7 rounded-full bg-slate-500 flex items-center justify-center text-slate-300 text-xs" x-text="p.nome[0]"></div>
            </template>
            <div>
              <div class="text-sm text-slate-100" x-text="p.nome"></div>
              <div x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="p.cpf_masked"></div>
            </div>
          </div>
        </template>
        <!-- Cadastrar novo -->
        <div x-show="buscaVinculo.trim().length >= 2 && !buscandoPessoa"
             @click="iniciarCadastroNovo()"
             class="flex items-center gap-2 px-3 py-2 bg-blue-900/30 cursor-pointer hover:bg-blue-900/50 transition-colors">
          <div class="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">+</div>
          <div>
            <div class="text-sm text-blue-400 font-medium">Cadastrar novo</div>
            <div class="text-xs text-slate-400">Pessoa não encontrada — clique para cadastrar</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pessoa selecionada -->
    <div x-show="pessoaSelecionada" class="flex items-center gap-2 bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2">
      <div class="w-7 h-7 rounded-full bg-slate-500 flex items-center justify-center text-slate-300 text-xs"
           x-text="pessoaSelecionada?.nome?.[0] || ''"></div>
      <div class="flex-1">
        <div class="text-sm text-slate-100" x-text="pessoaSelecionada?.nome"></div>
      </div>
      <button @click="pessoaSelecionada = null; buscaVinculo = ''"
              class="text-slate-400 hover:text-slate-200 text-xs">trocar</button>
    </div>

    <!-- Sub-formulário: cadastrar nova pessoa -->
    <div x-show="subFormNovaPessoa" class="space-y-2">
      <p class="text-xs text-blue-400 font-medium">Nova pessoa</p>
      <input type="text" x-model="novaPessoaForm.nome" placeholder="Nome *"
             class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
      <input type="text" x-model="novaPessoaForm.apelido" placeholder="Apelido (opcional)"
             class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
      <input type="text" x-model="novaPessoaForm.cpf" placeholder="CPF (opcional)"
             class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
      <input type="date" x-model="novaPessoaForm.data_nascimento"
             class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-blue-500">
      <div class="flex gap-2">
        <button @click="subFormNovaPessoa = false"
                class="flex-1 bg-slate-600 text-slate-300 rounded-lg py-2 text-sm">Cancelar</button>
        <button @click="cadastrarNovaPessoa()"
                :disabled="!novaPessoaForm.nome.trim()"
                class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg py-2 text-sm font-medium transition-colors">Cadastrar</button>
      </div>
    </div>

    <!-- Tipo e descrição (só aparece quando pessoa selecionada) -->
    <div x-show="pessoaSelecionada" class="space-y-3">
      <div>
        <label class="text-xs text-slate-400 font-medium block mb-1">
          Tipo do vínculo <span class="text-red-400">*</span>
        </label>
        <input type="text"
               x-model="novoVinculo.tipo"
               placeholder="Ex: Irmão, Pai, Amigo, Sócio..."
               class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500">
        <p class="text-xs text-slate-500 mt-1">Palavra curta que define a relação</p>
      </div>
      <div>
        <label class="text-xs text-slate-400 font-medium block mb-1">
          Descrição <span class="text-slate-500">(opcional)</span>
        </label>
        <textarea x-model="novoVinculo.descricao"
                  placeholder="Ex: Traficando junto na casa ao lado..."
                  rows="2"
                  class="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"></textarea>
      </div>
      <div class="flex gap-2">
        <button @click="fecharModalVinculo()"
                class="flex-1 bg-slate-600 text-slate-300 rounded-lg py-2.5 text-sm">Cancelar</button>
        <button @click="salvarVinculo()"
                :disabled="!novoVinculo.tipo.trim()"
                class="flex-2 flex-grow bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white rounded-lg py-2.5 text-sm font-medium transition-colors">Salvar Vínculo</button>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 6.6: Verificar lint**

```bash
make lint
```

Esperado: sem erros de ruff. Corrigir qualquer problema reportado.

- [ ] **Step 6.7: Testar manualmente no navegador**

1. `make dev`
2. Abrir app, ir para ficha de qualquer pessoa
3. Verificar que card "Vínculos" aparece com botão "+ Adicionar"
4. Clicar "+ Adicionar" → modal abre
5. Digitar nome → resultados aparecem após 400ms
6. Selecionar pessoa → campos tipo/descrição aparecem
7. Preencher tipo + descrição → "Salvar Vínculo"
8. Vínculo aparece na seção "Vínculos Manuais" com tipo em roxo e descrição em itálico
9. Recarregar página → vínculo persiste

- [ ] **Step 6.8: Commit final**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): container de vínculos dividido + cadastro de vínculos manuais"
```

---

## Verificação Final

- [ ] Rodar suite completa:

```bash
pytest tests/ -v --tb=short
```

Esperado: todos passando.

- [ ] Rodar lint:

```bash
make lint
```

Esperado: sem erros.
