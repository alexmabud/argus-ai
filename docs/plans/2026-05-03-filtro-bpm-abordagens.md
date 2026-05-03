# Filtro de Abordagens por BPM — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar um segundo filtro de visibilidade de abordagens no nível BPM. Quando ativo, usuários veem apenas abordagens do seu BPM. Filtro de equipe prevalece se ambos ativos. Usuário sem BPM com filtro BPM ativo vê zero abordagens.

**Architecture:** Adiciona `isolamento_abordagens` (Boolean) na tabela `bpms`. O helper `_filtro_abordagem(user)` retorna `(guarnicao_id | None, bpm_id | None)` e substitui os helpers `_isolamento()` / `_guarnicao_filter()` nos três routers afetados. O repo ganha variantes `*_by_bpm()` com JOIN em `guarnicoes.bpm_id`. Analytics usa subquery IN para filtrar por BPM sem conflito com JOINs existentes.

**Tech Stack:** FastAPI · SQLAlchemy 2.0 async · Alembic · Pydantic v2 · Alpine.js

---

### Task 1: Migration + campo no model `Bpm`

**Files:**
- Create: `alembic/versions/<hash>_add_isolamento_abordagens_em_bpms.py`
- Modify: `app/models/bpm.py`

**Step 1: Gerar migration via make**

```bash
make migrate msg="add_isolamento_abordagens_em_bpms"
```

**Step 2: Editar o arquivo de migration gerado**

Abra o arquivo gerado em `alembic/versions/` e substitua o conteúdo de `upgrade()` e `downgrade()`:

```python
def upgrade() -> None:
    op.add_column(
        "bpm",
        sa.Column(
            "isolamento_abordagens",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

def downgrade() -> None:
    op.drop_column("bpm", "isolamento_abordagens")
```

**Step 3: Adicionar campo no model `Bpm`**

Arquivo: `app/models/bpm.py`

Adicione o import `Boolean` no `from sqlalchemy import String`:
```python
from sqlalchemy import Boolean, String
```

Adicione o campo após `nome`:
```python
isolamento_abordagens: Mapped[bool] = mapped_column(
    Boolean, nullable=False, default=False, server_default="false"
)
```

Atualize a docstring da classe, adicionando em `Attributes`:
```
isolamento_abordagens: Se True, usuários do BPM veem apenas abordagens
    do próprio BPM. Se False (padrão), veem todas.
```

**Step 4: Aplicar migration localmente**

```bash
docker compose up -d db
make migrate msg=""  # apenas para confirmar que não há pendências — não gera arquivo novo
```

Ou aplicar diretamente:
```bash
docker compose run --rm api alembic upgrade head
```

Esperado: `Running upgrade ... -> <hash>, add_isolamento_abordagens_em_bpms`

**Step 5: Commit**

```bash
git add alembic/versions/ app/models/bpm.py
git commit -m "feat(bpm): campo isolamento_abordagens no model e migration"
```

---

### Task 2: Schemas `BpmRead` e `BpmIsolamentoUpdate`

**Files:**
- Modify: `app/schemas/bpm.py`
- Create: `tests/unit/test_schemas_bpm.py`

**Step 1: Escrever o teste**

```python
# tests/unit/test_schemas_bpm.py
"""Testes dos schemas de BPM."""

import pytest
from app.schemas.bpm import BpmIsolamentoUpdate, BpmRead


def test_bpm_read_inclui_isolamento_abordagens():
    """BpmRead deve incluir o campo isolamento_abordagens."""
    data = BpmRead(id=1, nome="14º BPM", isolamento_abordagens=True)
    assert data.isolamento_abordagens is True


def test_bpm_read_isolamento_padrao_false():
    """BpmRead com isolamento_abordagens omitido deve usar False."""
    data = BpmRead(id=1, nome="14º BPM", isolamento_abordagens=False)
    assert data.isolamento_abordagens is False


def test_bpm_isolamento_update_aceita_bool():
    """BpmIsolamentoUpdate deve aceitar True e False."""
    assert BpmIsolamentoUpdate(isolamento_abordagens=True).isolamento_abordagens is True
    assert BpmIsolamentoUpdate(isolamento_abordagens=False).isolamento_abordagens is False
```

**Step 2: Rodar e verificar que falha**

```bash
make test -- tests/unit/test_schemas_bpm.py -v
```

Esperado: `ImportError: cannot import name 'BpmIsolamentoUpdate'`

**Step 3: Implementar em `app/schemas/bpm.py`**

Adicione `isolamento_abordagens` em `BpmRead`:
```python
class BpmRead(BaseModel):
    """Dados de leitura de um BPM.

    Attributes:
        id: Identificador único do BPM.
        nome: Nome do batalhão (ex: "14º BPM").
        isolamento_abordagens: Se True, usuários do BPM veem apenas abordagens
            do próprio BPM.
    """

    id: int
    nome: str
    isolamento_abordagens: bool = False

    model_config = {"from_attributes": True}
```

Adicione o novo schema no final do arquivo:
```python
class BpmIsolamentoUpdate(BaseModel):
    """Dados para alternar isolamento de abordagens de um BPM.

    Attributes:
        isolamento_abordagens: True ativa isolamento por BPM, False desativa.
    """

    isolamento_abordagens: bool
```

**Step 4: Rodar e verificar que passa**

```bash
make test -- tests/unit/test_schemas_bpm.py -v
```

Esperado: `3 passed`

**Step 5: Commit**

```bash
git add app/schemas/bpm.py tests/unit/test_schemas_bpm.py
git commit -m "feat(bpm): schemas BpmRead com isolamento_abordagens + BpmIsolamentoUpdate"
```

---

### Task 3: `BpmService.toggle_isolamento()`

**Files:**
- Modify: `app/services/bpm_service.py`
- Modify: `tests/unit/test_bpm_service.py`

**Step 1: Ler o arquivo de teste existente**

```bash
cat tests/unit/test_bpm_service.py
```

**Step 2: Adicionar teste ao arquivo existente**

```python
@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_ativa(db_session, bpm):
    """toggle_isolamento(True) ativa isolamento_abordagens no BPM."""
    service = BpmService(db_session)
    result = await service.toggle_isolamento(bpm_id=bpm.id, valor=True, admin_id=1)
    assert result.isolamento_abordagens is True


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_desativa(db_session, bpm):
    """toggle_isolamento(False) desativa isolamento_abordagens no BPM."""
    bpm.isolamento_abordagens = True
    await db_session.flush()
    service = BpmService(db_session)
    result = await service.toggle_isolamento(bpm_id=bpm.id, valor=False, admin_id=1)
    assert result.isolamento_abordagens is False


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_nao_encontrado(db_session):
    """toggle_isolamento com ID inexistente lança NaoEncontradoError."""
    from app.core.exceptions import NaoEncontradoError
    service = BpmService(db_session)
    with pytest.raises(NaoEncontradoError):
        await service.toggle_isolamento(bpm_id=9999, valor=True, admin_id=1)
```

**Step 3: Rodar e verificar que falha**

```bash
make test -- tests/unit/test_bpm_service.py -v -k toggle
```

Esperado: `AttributeError: 'BpmService' object has no attribute 'toggle_isolamento'`

**Step 4: Implementar em `app/services/bpm_service.py`**

Adicione import no topo:
```python
from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
```

Adicione o método após `criar_bpm()`:
```python
async def toggle_isolamento(self, bpm_id: int, valor: bool, admin_id: int) -> Bpm:
    """Define o valor de isolamento_abordagens do BPM.

    Quando ativo, usuários do BPM veem apenas abordagens do próprio BPM.

    Args:
        bpm_id: ID do BPM a atualizar.
        valor: True ativa o isolamento, False desativa.
        admin_id: ID do admin que executou a ação (auditoria).

    Returns:
        BPM atualizado com o novo valor.

    Raises:
        NaoEncontradoError: Se o BPM não existe ou está inativo.
    """
    result = await self.db.execute(
        select(Bpm).where(
            Bpm.id == bpm_id,
            Bpm.ativo == True,  # noqa: E712
        )
    )
    bpm = result.scalar_one_or_none()
    if not bpm:
        raise NaoEncontradoError("BPM não encontrado")

    bpm.isolamento_abordagens = valor
    await self.db.flush()

    await self.audit.log(
        usuario_id=admin_id,
        acao="UPDATE",
        recurso="bpm",
        recurso_id=bpm.id,
        detalhes={"acao": "toggle_isolamento", "valor": valor},
    )
    return bpm
```

**Step 5: Rodar e verificar que passa**

```bash
make test -- tests/unit/test_bpm_service.py -v
```

Esperado: todos os testes passam.

**Step 6: Commit**

```bash
git add app/services/bpm_service.py tests/unit/test_bpm_service.py
git commit -m "feat(bpm): BpmService.toggle_isolamento()"
```

---

### Task 4: Endpoint `PATCH /admin/bpms/{id}/toggle-isolamento`

**Files:**
- Modify: `app/api/v1/admin.py`
- Modify: `tests/integration/test_api_bpms.py`

**Step 1: Escrever os testes**

Adicione ao final de `tests/integration/test_api_bpms.py`:

```python
@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_ativa_200(client: AsyncClient, admin_bpm_headers, bpm):
    """PATCH /admin/bpms/{id}/toggle-isolamento com True retorna 200 e campo atualizado."""
    response = await client.patch(
        f"/api/v1/admin/bpms/{bpm.id}/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 200
    assert response.json()["isolamento_abordagens"] is True


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_desativa_200(client: AsyncClient, admin_bpm_headers, bpm, db_session):
    """PATCH /admin/bpms/{id}/toggle-isolamento com False retorna 200 e desativa."""
    bpm.isolamento_abordagens = True
    await db_session.flush()
    response = await client.patch(
        f"/api/v1/admin/bpms/{bpm.id}/toggle-isolamento",
        json={"isolamento_abordagens": False},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 200
    assert response.json()["isolamento_abordagens"] is False


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_sem_admin_403(client: AsyncClient, auth_headers, bpm):
    """Usuário comum recebe 403 ao tentar alterar isolamento de BPM."""
    response = await client.patch(
        f"/api/v1/admin/bpms/{bpm.id}/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_toggle_isolamento_bpm_nao_encontrado_404(client: AsyncClient, admin_bpm_headers):
    """PATCH com BPM inexistente retorna 404."""
    response = await client.patch(
        "/api/v1/admin/bpms/9999/toggle-isolamento",
        json={"isolamento_abordagens": True},
        headers=admin_bpm_headers,
    )
    assert response.status_code == 404
```

**Step 2: Rodar e verificar que falha**

```bash
make test -- tests/integration/test_api_bpms.py -v -k toggle
```

Esperado: `404 Not Found` (rota não existe ainda)

**Step 3: Adicionar imports em `app/api/v1/admin.py`**

Adicione `BpmIsolamentoUpdate` nos imports de schemas (linha 24):
```python
from app.schemas.bpm import BpmCreate, BpmIsolamentoUpdate, BpmRead
```

**Step 4: Adicionar endpoint em `app/api/v1/admin.py`**

Adicione após `criar_bpm()` (após linha 336):

```python
@router.patch("/bpms/{bpm_id}/toggle-isolamento", response_model=BpmRead)
@limiter.limit("10/minute")
async def toggle_isolamento_bpm(
    request: Request,
    bpm_id: int,
    data: BpmIsolamentoUpdate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BpmRead:
    """Liga ou desliga o isolamento de abordagens para o BPM.

    Quando ativo, usuários do BPM veem apenas abordagens registradas
    por equipes do próprio BPM. O isolamento de equipe prevalece sobre
    o de BPM quando ambos estiverem ativos.

    Args:
        request: Requisição HTTP.
        bpm_id: ID do BPM a atualizar.
        data: Novo valor do toggle.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        BpmRead com o novo valor de isolamento_abordagens.

    Raises:
        HTTPException: 404 se o BPM não existe ou está inativo.

    Status Code:
        200: Toggle atualizado com sucesso.
        403: Não é administrador.
        404: BPM não encontrado.
    """
    service = BpmService(db)
    try:
        bpm = await service.toggle_isolamento(
            bpm_id=bpm_id,
            valor=data.isolamento_abordagens,
            admin_id=admin.id,
        )
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    await db.commit()
    return BpmRead.model_validate(bpm)
```

**Step 5: Rodar e verificar que passa**

```bash
make test -- tests/integration/test_api_bpms.py -v
```

Esperado: todos passam.

**Step 6: Commit**

```bash
git add app/api/v1/admin.py tests/integration/test_api_bpms.py
git commit -m "feat(admin): endpoint PATCH /admin/bpms/{id}/toggle-isolamento"
```

---

### Task 5: `AbordagemRepo` — métodos `*_by_bpm()`

**Files:**
- Modify: `app/repositories/abordagem_repo.py`
- Create: `tests/unit/test_abordagem_repo_bpm.py`

**Step 1: Adicionar import de `Guarnicao` no repo**

Em `app/repositories/abordagem_repo.py`, adicione após os imports existentes de models:
```python
from app.models.guarnicao import Guarnicao
```

**Step 2: Escrever os testes**

```python
# tests/unit/test_abordagem_repo_bpm.py
"""Testes dos métodos *_by_bpm() do AbordagemRepository."""

from datetime import UTC, datetime, date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem
from app.repositories.abordagem_repo import AbordagemRepository


@pytest.fixture
async def bpm2(db_session, bpm):
    """Segundo BPM para testes de isolamento."""
    from app.models.bpm import Bpm
    b = Bpm(nome="Outro BPM")
    db_session.add(b)
    await db_session.flush()
    return b


@pytest.fixture
async def guarnicao_bpm2(db_session, bpm2):
    """Equipe pertencente ao BPM 2."""
    from app.models.guarnicao import Guarnicao
    g = Guarnicao(nome="GU BPM2", bpm_id=bpm2.id, codigo="BPM2-GU01")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_bpm2(db_session, guarnicao_bpm2):
    """Usuário pertencente ao BPM 2."""
    from app.core.security import hash_senha
    from app.models.usuario import Usuario
    u = Usuario(
        nome="Agente BPM2",
        matricula="BPM2001",
        senha_hash=hash_senha("s3nha!A"),
        guarnicao_id=guarnicao_bpm2.id,
        session_id="session-bpm2",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def abordagem_bpm2(db_session, guarnicao_bpm2, usuario_bpm2):
    """Abordagem registrada por equipe do BPM 2."""
    a = Abordagem(
        guarnicao_id=guarnicao_bpm2.id,
        usuario_id=usuario_bpm2.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av BPM2 200",
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.mark.asyncio
async def test_list_by_bpm_retorna_apenas_do_bpm(
    db_session, bpm, guarnicao, usuario, abordagem, abordagem_bpm2
):
    """list_by_bpm retorna abordagens apenas do BPM especificado."""
    repo = AbordagemRepository(db_session)
    result = await repo.list_by_bpm(bpm_id=bpm.id)
    ids = [a.id for a in result]
    assert abordagem.id in ids
    assert abordagem_bpm2.id not in ids


@pytest.mark.asyncio
async def test_list_by_bpm_nao_retorna_de_outro_bpm(
    db_session, bpm2, abordagem, abordagem_bpm2
):
    """list_by_bpm com bpm2 não retorna abordagem do bpm1."""
    repo = AbordagemRepository(db_session)
    result = await repo.list_by_bpm(bpm_id=bpm2.id)
    ids = [a.id for a in result]
    assert abordagem_bpm2.id in ids
    assert abordagem.id not in ids


@pytest.mark.asyncio
async def test_get_detail_by_bpm_retorna_abordagem_correta(
    db_session, bpm, abordagem
):
    """get_detail_by_bpm retorna abordagem se pertence ao BPM."""
    repo = AbordagemRepository(db_session)
    result = await repo.get_detail_by_bpm(abordagem.id, bpm.id)
    assert result is not None
    assert result.id == abordagem.id


@pytest.mark.asyncio
async def test_get_detail_by_bpm_retorna_none_para_outro_bpm(
    db_session, bpm2, abordagem
):
    """get_detail_by_bpm retorna None se abordagem pertence a BPM diferente."""
    repo = AbordagemRepository(db_session)
    result = await repo.get_detail_by_bpm(abordagem.id, bpm2.id)
    assert result is None
```

**Step 3: Rodar e verificar que falha**

```bash
make test -- tests/unit/test_abordagem_repo_bpm.py -v
```

Esperado: `AttributeError: 'AbordagemRepository' object has no attribute 'list_by_bpm'`

**Step 4: Implementar os 4 métodos em `app/repositories/abordagem_repo.py`**

Adicione após o método `list_global()` (após linha 350):

```python
async def list_by_bpm(self, bpm_id: int, skip: int = 0, limit: int = 20) -> Sequence[Abordagem]:
    """Lista abordagens de todas as equipes de um BPM.

    Filtra via JOIN em guarnicoes.bpm_id. Retorna apenas abordagens ativas,
    ordenadas por data_hora decrescente.

    Args:
        bpm_id: ID do BPM para filtro.
        skip: Número de registros a pular.
        limit: Número máximo de resultados.

    Returns:
        Sequência de Abordagens do BPM ordenadas por data_hora decrescente.
    """
    query = (
        select(Abordagem)
        .join(Guarnicao, Guarnicao.id == Abordagem.guarnicao_id)
        .where(
            Guarnicao.bpm_id == bpm_id,
            Guarnicao.ativo == True,  # noqa: E712
            Abordagem.ativo == True,  # noqa: E712
        )
        .order_by(Abordagem.data_hora.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await self.db.execute(query)
    return result.scalars().all()

async def list_by_data_by_bpm(self, bpm_id: int, data: date) -> Sequence[Abordagem]:
    """Lista abordagens de todas as equipes de um BPM em uma data específica.

    Filtra pela data em fuso BRT (America/Sao_Paulo) via JOIN em guarnicoes.bpm_id.
    Carrega relacionamentos via selectin (pessoas, veículos, fotos, ocorrências).

    Args:
        bpm_id: ID do BPM para filtro.
        data: Data de referência (YYYY-MM-DD).

    Returns:
        Sequência de Abordagens do dia no BPM ordenadas por data_hora decrescente.
    """
    query = (
        select(Abordagem)
        .join(Guarnicao, Guarnicao.id == Abordagem.guarnicao_id)
        .options(
            selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
            selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
            selectinload(Abordagem.fotos),
            selectinload(Abordagem.ocorrencias),
        )
        .where(
            Guarnicao.bpm_id == bpm_id,
            Guarnicao.ativo == True,  # noqa: E712
            Abordagem.ativo == True,  # noqa: E712
            cast(func.timezone("America/Sao_Paulo", Abordagem.data_hora), Date) == data,
        )
        .order_by(Abordagem.data_hora.desc())
    )
    result = await self.db.execute(query)
    return result.scalars().all()

async def search_by_texto_by_bpm(self, bpm_id: int, q: str, limit: int = 100) -> Sequence[Abordagem]:
    """Busca abordagens por texto dentro de um BPM.

    Pesquisa por nome de pessoa, placa ou endereço. Filtra por bpm_id via
    subquery para evitar conflito com JOINs de pessoa e veículo.

    Args:
        bpm_id: ID do BPM para filtro.
        q: Termo de busca.
        limit: Número máximo de resultados.

    Returns:
        Sequência de Abordagens com correspondência no BPM.
    """
    termo = f"%{q}%"
    guarnicao_ids_bpm = select(Guarnicao.id).where(
        Guarnicao.bpm_id == bpm_id,
        Guarnicao.ativo == True,  # noqa: E712
    )
    query = (
        select(Abordagem)
        .options(
            selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
            selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
            selectinload(Abordagem.fotos),
            selectinload(Abordagem.ocorrencias),
        )
        .outerjoin(
            AbordagemPessoa,
            (AbordagemPessoa.abordagem_id == Abordagem.id) & (AbordagemPessoa.ativo == True),  # noqa: E712
        )
        .outerjoin(Pessoa, Pessoa.id == AbordagemPessoa.pessoa_id)
        .outerjoin(
            AbordagemVeiculo,
            (AbordagemVeiculo.abordagem_id == Abordagem.id) & (AbordagemVeiculo.ativo == True),  # noqa: E712
        )
        .outerjoin(Veiculo, Veiculo.id == AbordagemVeiculo.veiculo_id)
        .where(
            Abordagem.ativo == True,  # noqa: E712
            Abordagem.guarnicao_id.in_(guarnicao_ids_bpm),
            or_(
                Pessoa.nome.ilike(termo),
                Veiculo.placa.ilike(termo),
                Abordagem.endereco_texto.ilike(termo),
            ),
        )
        .distinct()
        .order_by(Abordagem.data_hora.desc())
        .limit(limit)
    )
    result = await self.db.execute(query)
    return result.scalars().unique().all()

async def get_detail_by_bpm(self, abordagem_id: int, bpm_id: int) -> Abordagem | None:
    """Busca abordagem por ID dentro de um BPM com eager loading.

    Verifica se a abordagem pertence a uma equipe do BPM antes de retornar.

    Args:
        abordagem_id: ID da abordagem.
        bpm_id: ID do BPM para validação de acesso.

    Returns:
        Abordagem com relacionamentos carregados, ou None se não pertence ao BPM.
    """
    guarnicao_ids_bpm = select(Guarnicao.id).where(
        Guarnicao.bpm_id == bpm_id,
        Guarnicao.ativo == True,  # noqa: E712
    )
    query = (
        select(Abordagem)
        .options(
            selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
            selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
            selectinload(Abordagem.fotos),
            selectinload(Abordagem.ocorrencias),
        )
        .where(
            Abordagem.id == abordagem_id,
            Abordagem.ativo == True,  # noqa: E712
            Abordagem.guarnicao_id.in_(guarnicao_ids_bpm),
        )
    )
    result = await self.db.execute(query)
    return result.scalar_one_or_none()
```

**Step 5: Rodar e verificar que passa**

```bash
make test -- tests/unit/test_abordagem_repo_bpm.py -v
```

Esperado: todos os testes passam.

**Step 6: Commit**

```bash
git add app/repositories/abordagem_repo.py tests/unit/test_abordagem_repo_bpm.py
git commit -m "feat(repo): métodos list/detail/busca *_by_bpm() no AbordagemRepository"
```

---

### Task 6: `AbordagemService` — suporte a `bpm_id`

**Files:**
- Modify: `app/services/abordagem_service.py`
- Modify: `tests/unit/test_abordagem_service.py`

**Step 1: Escrever testes para o novo comportamento**

Adicione ao final de `tests/unit/test_abordagem_service.py`:

```python
@pytest.mark.asyncio
async def test_listar_com_bpm_id_chama_repo_by_bpm(mocker):
    """listar() com guarnicao_id=None e bpm_id definido usa repo.list_by_bpm."""
    repo_mock = mocker.AsyncMock()
    repo_mock.list_by_bpm = mocker.AsyncMock(return_value=[])
    service = AbordagemService.__new__(AbordagemService)
    service.repo = repo_mock
    await service.listar(guarnicao_id=None, bpm_id=5)
    repo_mock.list_by_bpm.assert_awaited_once_with(5, 0, 20)


@pytest.mark.asyncio
async def test_listar_sem_filtro_chama_global(mocker):
    """listar() com guarnicao_id=None e bpm_id=None usa repo.list_global."""
    repo_mock = mocker.AsyncMock()
    repo_mock.list_global = mocker.AsyncMock(return_value=[])
    service = AbordagemService.__new__(AbordagemService)
    service.repo = repo_mock
    await service.listar(guarnicao_id=None, bpm_id=None)
    repo_mock.list_global.assert_awaited_once()
```

**Step 2: Rodar e verificar que falha**

```bash
make test -- tests/unit/test_abordagem_service.py -v -k bpm_id
```

Esperado: `TypeError: listar() got an unexpected keyword argument 'bpm_id'`

**Step 3: Atualizar os 4 métodos em `app/services/abordagem_service.py`**

**`buscar_detalhe()`** — substitua a assinatura e corpo:
```python
async def buscar_detalhe(
    self,
    abordagem_id: int,
    guarnicao_id: int | None,
    bpm_id: int | None = None,
) -> Abordagem:
    """Busca abordagem com todos os relacionamentos carregados.

    Prioridade: guarnicao_id > bpm_id > global.

    Args:
        abordagem_id: Identificador da abordagem.
        guarnicao_id: ID da guarnição para filtro por equipe (prevalece).
        bpm_id: ID do BPM para filtro por BPM (usado se guarnicao_id=None).

    Returns:
        Abordagem com todos os relacionamentos carregados.

    Raises:
        NaoEncontradoError: Se abordagem não existe ou não está no escopo.
    """
    if guarnicao_id is not None:
        abordagem = await self.repo.get_detail(abordagem_id, guarnicao_id)
    elif bpm_id is not None:
        abordagem = await self.repo.get_detail_by_bpm(abordagem_id, bpm_id)
    else:
        abordagem = await self.repo.get_detail_global(abordagem_id)
    if not abordagem:
        raise NaoEncontradoError("Abordagem")
    return abordagem
```

**`listar()`** — substitua assinatura e corpo:
```python
async def listar(
    self,
    guarnicao_id: int | None,
    bpm_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Abordagem]:
    """Lista abordagens com paginação.

    Prioridade: guarnicao_id > bpm_id > global.

    Args:
        guarnicao_id: ID da guarnição (filtro por equipe, prevalece).
        bpm_id: ID do BPM (filtro por BPM, usado se guarnicao_id=None).
        skip: Número de registros a pular.
        limit: Número máximo de resultados.

    Returns:
        Sequência de Abordagens ordenadas por data_hora decrescente.
    """
    if guarnicao_id is not None:
        return await self.repo.list_by_guarnicao(guarnicao_id, skip, limit)
    if bpm_id is not None:
        return await self.repo.list_by_bpm(bpm_id, skip, limit)
    return await self.repo.list_global(skip, limit)
```

**`listar_por_data()`** — substitua assinatura e corpo:
```python
async def listar_por_data(
    self,
    guarnicao_id: int | None,
    data: date,
    bpm_id: int | None = None,
) -> Sequence[Abordagem]:
    """Lista abordagens em uma data específica.

    Prioridade: guarnicao_id > bpm_id > global.

    Args:
        guarnicao_id: ID da guarnição (filtro por equipe, prevalece).
        data: Data de referência (YYYY-MM-DD).
        bpm_id: ID do BPM (filtro por BPM, usado se guarnicao_id=None).

    Returns:
        Sequência de Abordagens do dia ordenadas por data_hora decrescente.
    """
    if guarnicao_id is not None:
        return await self.repo.list_by_data(guarnicao_id, data)
    if bpm_id is not None:
        return await self.repo.list_by_data_by_bpm(bpm_id, data)
    return await self.repo.list_by_data_global(data)
```

**`buscar_por_texto()`** — substitua assinatura e corpo:
```python
async def buscar_por_texto(
    self,
    q: str,
    guarnicao_id: int | None,
    bpm_id: int | None = None,
    limit: int = 100,
) -> Sequence[Abordagem]:
    """Busca abordagens por texto em todas as datas.

    Prioridade: guarnicao_id > bpm_id > global.

    Args:
        q: Termo de busca.
        guarnicao_id: ID da guarnição (filtro por equipe, prevalece).
        bpm_id: ID do BPM (filtro por BPM, usado se guarnicao_id=None).
        limit: Número máximo de resultados.

    Returns:
        Sequência de Abordagens com correspondência.
    """
    if guarnicao_id is not None:
        return await self.repo.search_by_texto(guarnicao_id, q, limit)
    if bpm_id is not None:
        return await self.repo.search_by_texto_by_bpm(bpm_id, q, limit)
    return await self.repo.search_by_texto_global(q, limit)
```

**Step 4: Rodar e verificar que passa**

```bash
make test -- tests/unit/test_abordagem_service.py -v
```

Esperado: todos os testes passam.

**Step 5: Commit**

```bash
git add app/services/abordagem_service.py tests/unit/test_abordagem_service.py
git commit -m "feat(service): AbordagemService suporta filtro por bpm_id em cascata"
```

---

### Task 7: `AnalyticsService` — suporte a `bpm_id`

**Files:**
- Modify: `app/services/analytics_service.py`
- Modify: `tests/unit/test_analytics_service.py`

**Step 1: Adicionar import de `Guarnicao` e `select` no analytics_service**

Em `app/services/analytics_service.py`, adicione após os imports existentes:
```python
from app.models.guarnicao import Guarnicao
```

**Step 2: Criar helper privado de filtro no `AnalyticsService`**

Adicione método privado após `__init__`:

```python
def _filtro_base(
    self,
    guarnicao_id: int | None,
    bpm_id: int | None = None,
) -> list:
    """Retorna condições base de filtro para queries de analytics.

    Prioridade: guarnicao_id > bpm_id > global (sem filtro de escopo).

    Args:
        guarnicao_id: ID da guarnição para filtro por equipe.
        bpm_id: ID do BPM para filtro por BPM (subquery IN).

    Returns:
        Lista de condições SQLAlchemy para uso em .where(*conditions).
    """
    conditions: list = [Abordagem.ativo == True]  # noqa: E712
    if guarnicao_id is not None:
        conditions.append(Abordagem.guarnicao_id == guarnicao_id)
    elif bpm_id is not None:
        guarnicao_ids = select(Guarnicao.id).where(
            Guarnicao.bpm_id == bpm_id,
            Guarnicao.ativo == True,  # noqa: E712
        )
        conditions.append(Abordagem.guarnicao_id.in_(guarnicao_ids))
    return conditions
```

**Step 3: Atualizar todas as assinaturas dos métodos públicos**

Em cada um dos métodos a seguir, adicione `bpm_id: int | None = None` como parâmetro e substitua a construção manual de `base` pela chamada `self._filtro_base(guarnicao_id, bpm_id)`.

Métodos a atualizar (todos em `app/services/analytics_service.py`):
- `resumo(guarnicao_id, dias=30)` → `resumo(guarnicao_id, dias=30, bpm_id=None)`
- `mapa_calor(guarnicao_id, dias=30)` → adicionar `bpm_id=None`
- `horarios_pico(guarnicao_id, dias=30)` → adicionar `bpm_id=None`
- `pessoas_recorrentes(guarnicao_id, limit=20)` → adicionar `bpm_id=None`
- `resumo_hoje(guarnicao_id)` → adicionar `bpm_id=None`
- `resumo_mes(guarnicao_id)` → adicionar `bpm_id=None`
- `resumo_total(guarnicao_id)` → adicionar `bpm_id=None`
- `por_dia(guarnicao_id, dias=30)` → adicionar `bpm_id=None`
- `por_mes(guarnicao_id, meses=12)` → adicionar `bpm_id=None`
- `dias_com_abordagem(guarnicao_id, mes)` → adicionar `bpm_id=None`
- `pessoas_do_dia(guarnicao_id, data)` → adicionar `bpm_id=None`
- `abordagens_do_dia(guarnicao_id, data)` → adicionar `bpm_id=None`
- `metricas_rag(guarnicao_id)` → adicionar `bpm_id=None`

Para cada método que hoje constrói `base` manualmente assim:
```python
base = [Abordagem.ativo, Abordagem.data_hora >= desde]
if guarnicao_id is not None:
    base.append(Abordagem.guarnicao_id == guarnicao_id)
```

Substitua por:
```python
base = self._filtro_base(guarnicao_id, bpm_id)
base.append(Abordagem.data_hora >= desde)  # se havia condição adicional de data
```

> **Nota:** `Abordagem.ativo` (sem comparação explícita) e `Abordagem.ativo == True` são equivalentes em SQLAlchemy — o `_filtro_base` usa `== True`. Remova a duplicata do `base` original onde `Abordagem.ativo` já aparecia.

**Step 4: Escrever testes no arquivo existente**

Adicione ao final de `tests/unit/test_analytics_service.py`:

```python
@pytest.mark.asyncio
async def test_resumo_com_bpm_id_filtra_por_bpm(db_session, bpm, guarnicao, usuario, abordagem):
    """resumo() com bpm_id retorna dados apenas do BPM especificado."""
    service = AnalyticsService(db_session)
    result = await service.resumo(guarnicao_id=None, bpm_id=bpm.id)
    assert result["total_abordagens"] >= 1


@pytest.mark.asyncio
async def test_resumo_com_bpm_errado_retorna_zero(db_session, abordagem):
    """resumo() com bpm_id de BPM sem abordagens retorna zero."""
    from app.models.bpm import Bpm
    bpm_vazio = Bpm(nome="BPM Vazio")
    db_session.add(bpm_vazio)
    await db_session.flush()
    service = AnalyticsService(db_session)
    result = await service.resumo(guarnicao_id=None, bpm_id=bpm_vazio.id)
    assert result["total_abordagens"] == 0
```

**Step 5: Rodar e verificar que passa**

```bash
make test -- tests/unit/test_analytics_service.py -v
```

Esperado: todos os testes passam.

**Step 6: Commit**

```bash
git add app/services/analytics_service.py tests/unit/test_analytics_service.py
git commit -m "feat(analytics): AnalyticsService suporta filtro por bpm_id em cascata"
```

---

### Task 8: `ConsultaService` — suporte a `bpm_id`

**Files:**
- Modify: `app/services/consulta_service.py`
- Modify: `tests/unit/test_consulta_service.py`

**Step 1: Adicionar import de `Guarnicao` e `select` no consulta_service**

Em `app/services/consulta_service.py`, adicione:
```python
from app.models.guarnicao import Guarnicao
from sqlalchemy import select
```

**Step 2: Atualizar `busca_unificada()`**

Substitua o parâmetro `isolamento: bool = False` por `guarnicao_id_filtro: int | None = None, bpm_id_filtro: int | None = None`:

```python
async def busca_unificada(
    self,
    q: str,
    tipo: str | None = None,
    bairro: str | None = None,
    cidade: str | None = None,
    estado: str | None = None,
    skip: int = 0,
    limit: int = 20,
    user: Usuario | None = None,
    guarnicao_id_filtro: int | None = None,
    bpm_id_filtro: int | None = None,
) -> dict:
```

Na construção de `guarnicao_id_abordagem`, substitua:
```python
# Antes:
guarnicao_id_abordagem = (user.guarnicao_id if user else None) if isolamento else None

# Depois:
guarnicao_id_abordagem = guarnicao_id_filtro
```

Para o filtro BPM em `_buscar_abordagens` e `_buscar_veiculos`, atualize as chamadas passando `bpm_id_filtro` como parâmetro adicional:
```python
abordagens = await self._buscar_abordagens(q, guarnicao_id_abordagem, skip, limit, bpm_id=bpm_id_filtro)
veiculos = await self._buscar_veiculos(q, guarnicao_id_abordagem, skip, limit, bpm_id=bpm_id_filtro)
```

Atualize os métodos `_buscar_abordagens` e `_buscar_veiculos` para aceitar `bpm_id: int | None = None`:

Em `_buscar_abordagens`, adicione após `if guarnicao_id is not None:`:
```python
elif bpm_id is not None:
    guarnicao_ids = select(Guarnicao.id).where(
        Guarnicao.bpm_id == bpm_id,
        Guarnicao.ativo == True,  # noqa: E712
    )
    query = query.where(Abordagem.guarnicao_id.in_(guarnicao_ids))
```

Em `_buscar_veiculos`, o filtro de `guarnicao_id` é feito via `AbordagemVeiculo`. Adicione filtro equivalente via subquery se `bpm_id` for informado. Verifique a implementação existente para aplicar o mesmo padrão.

**Step 3: Rodar e verificar que passa**

```bash
make test -- tests/unit/test_consulta_service.py tests/integration/test_api_consulta.py -v
```

Esperado: todos os testes passam.

**Step 4: Commit**

```bash
git add app/services/consulta_service.py tests/unit/test_consulta_service.py
git commit -m "feat(consulta): ConsultaService suporta filtro por bpm_id"
```

---

### Task 9: API routers — helper `_filtro_abordagem()` e atualização das chamadas

**Files:**
- Modify: `app/api/v1/abordagens.py`
- Modify: `app/api/v1/analytics.py`
- Modify: `app/api/v1/consultas.py`
- Create: `tests/integration/test_abordagens_toggle_bpm.py`

**Step 1: Escrever os testes de integração do filtro BPM**

```python
# tests/integration/test_abordagens_toggle_bpm.py
"""Testes do toggle de isolamento de abordagens por BPM."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_access_token, hash_senha
from app.models.abordagem import Abordagem
from app.models.bpm import Bpm
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


@pytest.fixture
async def bpm_b(db_session: AsyncSession) -> Bpm:
    """Segundo BPM para testes de isolamento."""
    b = Bpm(nome="BPM B")
    db_session.add(b)
    await db_session.flush()
    return b


@pytest.fixture
async def equipe_bpm_b(db_session: AsyncSession, bpm_b: Bpm) -> Guarnicao:
    """Equipe pertencente ao BPM B."""
    g = Guarnicao(nome="GU BPM-B", bpm_id=bpm_b.id, codigo="BPMB-GU01")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_bpm_b(db_session: AsyncSession, equipe_bpm_b: Guarnicao) -> Usuario:
    """Usuário pertencente ao BPM B."""
    u = Usuario(
        nome="Agente BPM-B",
        matricula="BPMB001",
        senha_hash=hash_senha("s3nha!A"),
        guarnicao_id=equipe_bpm_b.id,
        session_id="session-bpmb",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def headers_bpm_b(usuario_bpm_b: Usuario) -> dict:
    """Headers do usuário do BPM B."""
    token = criar_access_token({
        "sub": str(usuario_bpm_b.id),
        "guarnicao_id": usuario_bpm_b.guarnicao_id,
        "sid": usuario_bpm_b.session_id,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def abordagem_bpm_b(
    db_session: AsyncSession, equipe_bpm_b: Guarnicao, usuario_bpm_b: Usuario
) -> Abordagem:
    """Abordagem registrada pelo BPM B."""
    a = Abordagem(
        guarnicao_id=equipe_bpm_b.id,
        usuario_id=usuario_bpm_b.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av BPM-B 300",
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.mark.asyncio
async def test_isolamento_bpm_off_usuario_a_ve_abordagem_de_bpm_b(
    client: AsyncClient, auth_headers, abordagem, abordagem_bpm_b, bpm
):
    """Com isolamento BPM OFF, usuário do BPM A vê abordagens do BPM B."""
    assert bpm.isolamento_abordagens is False
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_bpm_b.id in ids


@pytest.mark.asyncio
async def test_isolamento_bpm_on_usuario_a_nao_ve_abordagem_de_bpm_b(
    client: AsyncClient, auth_headers, db_session, bpm, abordagem, abordagem_bpm_b
):
    """Com isolamento BPM ON, usuário do BPM A não vê abordagens do BPM B."""
    bpm.isolamento_abordagens = True
    await db_session.flush()
    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids
    assert abordagem_bpm_b.id not in ids


@pytest.mark.asyncio
async def test_isolamento_equipe_prevalece_sobre_bpm(
    client: AsyncClient, auth_headers, db_session, bpm, guarnicao, abordagem, abordagem_bpm_b
):
    """Quando isolamento de equipe está ON, filtro de BPM é ignorado.
    Usuário vê apenas abordagens da própria equipe, não de todo o BPM.
    """
    bpm.isolamento_abordagens = True
    guarnicao.isolamento_abordagens = True
    await db_session.flush()

    # Criar segunda equipe no mesmo BPM
    equipe_2 = Guarnicao(nome="GU 2 BPM A", bpm_id=bpm.id, codigo="BPMA-GU02")
    db_session.add(equipe_2)
    await db_session.flush()
    usuario_2 = Usuario(
        nome="Agente 2 BPM A",
        matricula="BPMA002",
        senha_hash=hash_senha("s3nha!A"),
        guarnicao_id=equipe_2.id,
        session_id="sess-a2",
    )
    db_session.add(usuario_2)
    await db_session.flush()
    abordagem_equipe_2 = Abordagem(
        guarnicao_id=equipe_2.id,
        usuario_id=usuario_2.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Av GU2 BPM-A",
    )
    db_session.add(abordagem_equipe_2)
    await db_session.flush()

    response = await client.get("/api/v1/abordagens/", headers=auth_headers)
    ids = [a["id"] for a in response.json()]
    assert abordagem.id in ids  # sua equipe
    assert abordagem_equipe_2.id not in ids  # outra equipe do mesmo BPM
    assert abordagem_bpm_b.id not in ids  # outro BPM
```

**Step 2: Rodar e verificar que falha**

```bash
make test -- tests/integration/test_abordagens_toggle_bpm.py -v -k bpm_on
```

Esperado: o teste passa a retornar abordagem_bpm_b (filtro ainda não implementado no router).

**Step 3: Atualizar `app/api/v1/abordagens.py`**

Substitua a função helper `_isolamento` (se existir) ou adicione `_filtro_abordagem`:

```python
def _filtro_abordagem(user: Usuario) -> tuple[int | None, int | None]:
    """Retorna (guarnicao_id, bpm_id) para filtro de abordagens.

    Prioridade: equipe > BPM > global. Apenas um dos dois será não-None.

    Args:
        user: Usuário autenticado com guarnicao e bpm carregados.

    Returns:
        Tupla (guarnicao_id, bpm_id). Ambos None = acesso global.
    """
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return (user.guarnicao_id, None)
    if user.guarnicao and user.guarnicao.bpm and user.guarnicao.bpm.isolamento_abordagens:
        return (None, user.guarnicao.bpm_id)
    return (None, None)
```

No endpoint `GET /abordagens/`, substitua:
```python
# Antes:
isolamento = bool(user.guarnicao and user.guarnicao.isolamento_abordagens)
# ...
abordagens = await service.listar(guarnicao_id=user.guarnicao_id, skip=skip, limit=limit, isolamento=isolamento)

# Depois:
guarnicao_id_filtro, bpm_id_filtro = _filtro_abordagem(user)
# ...
abordagens = await service.listar(guarnicao_id=guarnicao_id_filtro, bpm_id=bpm_id_filtro, skip=skip, limit=limit)
```

Aplique o mesmo padrão para `buscar_por_texto`, `listar_por_data` e `buscar_detalhe`.

No endpoint `GET /abordagens/{id}`, substitua:
```python
# Antes:
isolamento = bool(user.guarnicao and user.guarnicao.isolamento_abordagens)
abordagem = await service.buscar_detalhe(abordagem_id, user.guarnicao_id, isolamento=isolamento)

# Depois:
guarnicao_id_filtro, bpm_id_filtro = _filtro_abordagem(user)
abordagem = await service.buscar_detalhe(abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro)
```

**Step 4: Atualizar `app/api/v1/analytics.py`**

Substitua `_guarnicao_filter()` por `_filtros_analytics()`:

```python
def _filtros_analytics(user: Usuario) -> tuple[int | None, int | None]:
    """Retorna (guarnicao_id, bpm_id) para filtro de analytics.

    Prioridade: equipe > BPM > global.

    Args:
        user: Usuário autenticado com guarnicao e bpm carregados.

    Returns:
        Tupla (guarnicao_id, bpm_id). Ambos None = acesso global.
    """
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return (user.guarnicao_id, None)
    if user.guarnicao and user.guarnicao.bpm and user.guarnicao.bpm.isolamento_abordagens:
        return (None, user.guarnicao.bpm_id)
    return (None, None)
```

Em cada endpoint de analytics, substitua:
```python
# Antes:
data = await service.resumo(_guarnicao_filter(user), dias=dias)

# Depois:
gid, bid = _filtros_analytics(user)
data = await service.resumo(guarnicao_id=gid, bpm_id=bid, dias=dias)
```

Aplique o mesmo padrão para todos os demais endpoints do router de analytics.

**Step 5: Atualizar `app/api/v1/consultas.py`**

Substitua `_isolamento()` por `_filtros_consulta()`:

```python
def _filtros_consulta(user: Usuario) -> tuple[int | None, int | None]:
    """Retorna (guarnicao_id, bpm_id) para filtro de consultas.

    Args:
        user: Usuário autenticado.

    Returns:
        Tupla (guarnicao_id, bpm_id). Ambos None = acesso global.
    """
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return (user.guarnicao_id, None)
    if user.guarnicao and user.guarnicao.bpm and user.guarnicao.bpm.isolamento_abordagens:
        return (None, user.guarnicao.bpm_id)
    return (None, None)
```

No endpoint `consulta_unificada`, substitua:
```python
# Antes:
resultados = await service.busca_unificada(..., isolamento=_isolamento(user))

# Depois:
gid, bid = _filtros_consulta(user)
resultados = await service.busca_unificada(..., guarnicao_id_filtro=gid, bpm_id_filtro=bid)
```

**Step 6: Rodar e verificar que passa**

```bash
make test -- tests/integration/test_abordagens_toggle_bpm.py tests/integration/test_abordagens_toggle.py tests/integration/test_api_analytics.py tests/integration/test_api_consulta.py -v
```

Esperado: todos os testes passam. Os testes existentes do filtro de equipe devem continuar passando.

**Step 7: Commit**

```bash
git add app/api/v1/abordagens.py app/api/v1/analytics.py app/api/v1/consultas.py tests/integration/test_abordagens_toggle_bpm.py
git commit -m "feat(api): helper _filtro_abordagem() com cascata equipe > BPM > global nos routers"
```

---

### Task 10: Frontend — toggle BPM em `admin-usuarios.js`

**Files:**
- Modify: `frontend/js/pages/admin-usuarios.js`

**Step 1: Adicionar `bpmAtivoObj` como computed**

No objeto Alpine.js, localize onde `bpmAtivo` é declarado (linha ~305). Adicione a computed property logo abaixo das funções `equipesDoBpm()` e `equipeAtivaObj`:

```javascript
get bpmAtivoObj() {
  return this.bpms.find(b => b.id === this.bpmAtivo) || null;
},
```

**Step 2: Adicionar o toggle de BPM no template HTML**

Localize a seção `<!-- BPM selecionado: conteúdo de equipe -->` (linha ~127). Adicione o toggle de BPM ANTES das equipes, dentro de `<template x-if="bpmAtivo !== null">`:

```html
<!-- Toggle de isolamento por BPM -->
<template x-if="bpmAtivoObj">
  <div style="display: flex; align-items: center; justify-content: flex-end; margin-bottom: 0.5rem; padding: 0.5rem 0.75rem; background: rgba(0,0,0,0.15); border-radius: 4px; border: 1px solid var(--color-border);">
    <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
      <span style="color: var(--color-text-muted); font-family: var(--font-data); font-size: 0.75rem;">Ver apenas abordagens do BPM</span>
      <input
        type="checkbox"
        :checked="bpmAtivoObj.isolamento_abordagens"
        @change="alternarIsolamentoBpm(bpmAtivoObj.id, $event.target.checked)"
      />
    </label>
  </div>
</template>
```

**Step 3: Adicionar a função `alternarIsolamentoBpm()`**

Logo após `alternarIsolamento()` (linha ~504), adicione:

```javascript
async alternarIsolamentoBpm(bpmId, valor) {
  try {
    await api.patch(`/admin/bpms/${bpmId}/toggle-isolamento`, {
      isolamento_abordagens: valor,
    });
    showToast(valor ? "Isolamento de BPM ativado" : "Isolamento de BPM desativado", "success");
    await this.carregar();
  } catch (e) {
    showToast(e.message || "Erro ao atualizar BPM", "error");
    await this.carregar();
  }
},
```

**Step 4: Verificar que `BpmRead` inclui `isolamento_abordagens` no `GET /admin/bpms`**

O `GET /admin/bpms` já serializa via `BpmRead.model_validate(b)` — como `BpmRead` foi atualizado na Task 2 para incluir o campo, o frontend receberá `isolamento_abordagens` no objeto de cada BPM. Sem mudanças adicionais no endpoint.

**Step 5: Teste manual**

```bash
make dev
```

1. Acesse `#admin-usuarios`
2. Clique em um BPM
3. Verifique que o toggle "Ver apenas abordagens do BPM" aparece no cabeçalho do BPM
4. Ative o toggle — deve chamar `PATCH /admin/bpms/{id}/toggle-isolamento`
5. Veja o toast de confirmação
6. Faça login com um usuário desse BPM e verifique que abordagens de outros BPMs não aparecem

**Step 6: Commit**

```bash
git add frontend/js/pages/admin-usuarios.js
git commit -m "feat(frontend): toggle 'Ver apenas abordagens do BPM' em admin-usuarios"
```

---

### Task 11: Rodar suite completa e verificar regressões

**Step 1: Rodar todos os testes**

```bash
make test
```

Esperado: todos os testes passam, incluindo:
- `tests/integration/test_abordagens_toggle.py` (filtro equipe continua funcionando)
- `tests/integration/test_abordagens_toggle_bpm.py` (novo filtro BPM)
- `tests/integration/test_api_bpms.py` (endpoint toggle BPM)
- `tests/unit/test_abordagem_service.py`
- `tests/unit/test_analytics_service.py`
- `tests/unit/test_schemas_bpm.py`

**Step 2: Lint**

```bash
make lint
```

Esperado: sem erros de ruff ou mypy.

**Step 3: Commit final se necessário**

```bash
git add -A
git commit -m "test(bpm): suite completa filtro BPM — todos os testes passando"
```
