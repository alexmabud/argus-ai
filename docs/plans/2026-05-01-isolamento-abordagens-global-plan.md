# Isolamento de Abordagens — Cobertura Global: Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fazer o toggle `isolamento_abordagens` funcionar em todos os endpoints: analytics e consulta devem respeitar o toggle da equipe (OFF = global, ON = só a equipe).

**Architecture:** A API converte o toggle para `guarnicao_filter: int | None` antes de chamar o service. Services e repos já aceitam `None` como "sem filtro" (ou serão ajustados). Pessoas são sempre globais (guarnicao_id=None sempre).

**Tech Stack:** FastAPI, SQLAlchemy async, pytest-asyncio, httpx

---

### Task 1: Testes falhando — analytics respeita o toggle

**Files:**
- Modify: `tests/integration/test_api_analytics.py`

**Step 1: Adicionar fixtures de segunda equipe ao final do arquivo**

```python
# Adicionar no topo do arquivo (após os imports existentes):
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario
from app.core.security import criar_access_token, hash_senha
```

```python
# Adicionar as fixtures e testes ao final do arquivo:

@pytest.fixture
async def equipe_b(db_session: AsyncSession) -> Guarnicao:
    """Segunda equipe sem isolamento."""
    g = Guarnicao(nome="GU Bravo", unidade="2o BPM", codigo="2BPM-GUB")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_b(db_session: AsyncSession, equipe_b: Guarnicao) -> Usuario:
    """Usuário da equipe B."""
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
async def abordagem_equipe_a(db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario) -> Abordagem:
    """Abordagem da equipe A."""
    from datetime import UTC, datetime
    a = Abordagem(
        guarnicao_id=guarnicao.id,
        usuario_id=usuario.id,
        data_hora=datetime.now(UTC),
        endereco_texto="Rua A 100",
    )
    db_session.add(a)
    await db_session.flush()
    return a


class TestAnalyticsToggleIsolamento:
    """Toggle de isolamento deve afetar analytics."""

    async def test_resumo_total_toggle_off_ve_global(
        self,
        client: AsyncClient,
        auth_headers: dict,
        headers_b: dict,
        abordagem_equipe_a: Abordagem,
        guarnicao: Guarnicao,
        equipe_b: Guarnicao,
    ):
        """Usuário da equipe B com toggle OFF vê abordagens da equipe A no total."""
        assert equipe_b.isolamento_abordagens is False
        response = await client.get("/api/v1/analytics/resumo-total", headers=headers_b)
        assert response.status_code == 200
        data = response.json()
        # equipe B tem 0 abordagens próprias, mas toggle OFF = global → vê a da equipe A
        assert data["abordagens"] >= 1

    async def test_resumo_total_toggle_on_ve_apenas_propria_equipe(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        headers_b: dict,
        abordagem_equipe_a: Abordagem,
        equipe_b: Guarnicao,
    ):
        """Usuário da equipe B com toggle ON não vê abordagens da equipe A."""
        equipe_b.isolamento_abordagens = True
        await db_session.flush()
        response = await client.get("/api/v1/analytics/resumo-total", headers=headers_b)
        assert response.status_code == 200
        data = response.json()
        assert data["abordagens"] == 0

    async def test_dias_com_abordagem_toggle_off_ve_global(
        self,
        client: AsyncClient,
        headers_b: dict,
        abordagem_equipe_a: Abordagem,
        equipe_b: Guarnicao,
    ):
        """dias_com_abordagem com toggle OFF inclui dias de outras equipes."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        mes_atual = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m")
        assert equipe_b.isolamento_abordagens is False
        response = await client.get(
            f"/api/v1/analytics/dias-com-abordagem?mes={mes_atual}",
            headers=headers_b,
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1
```

**Step 2: Rodar os testes para confirmar que falham**

```bash
make test -- tests/integration/test_api_analytics.py::TestAnalyticsToggleIsolamento -v
```

Esperado: FAIL — `test_resumo_total_toggle_off_ve_global` retorna 0 em vez de >= 1

**Step 3: Commit dos testes falhando**

```bash
git add tests/integration/test_api_analytics.py
git commit -m "test(analytics): testes falhando para toggle de isolamento global"
```

---

### Task 2: Fix analytics_service — guarnicao_id: int | None

**Files:**
- Modify: `app/services/analytics_service.py`

**Step 1: Atualizar docstring da classe e todos os métodos**

Mudar a assinatura de TODOS os 13 métodos de `guarnicao_id: int` para `guarnicao_id: int | None`.

Padrão de refactor — ANTES (exemplo em `resumo_hoje`):
```python
async def resumo_hoje(self, guarnicao_id: int) -> dict:
    ...
    total_q = select(func.count(Abordagem.id)).where(
        Abordagem.guarnicao_id == guarnicao_id,
        Abordagem.ativo,
        Abordagem.data_hora >= inicio,
        Abordagem.data_hora < fim,
    )
```

DEPOIS (padrão a aplicar em todos os métodos):
```python
async def resumo_hoje(self, guarnicao_id: int | None) -> dict:
    ...
    base = [Abordagem.ativo, Abordagem.data_hora >= inicio, Abordagem.data_hora < fim]
    if guarnicao_id is not None:
        base.append(Abordagem.guarnicao_id == guarnicao_id)

    total_q = select(func.count(Abordagem.id)).where(*base)
    total = (await self.db.execute(total_q)).scalar() or 0

    pessoas_q = (
        select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
        .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
        .where(*base)
    )
```

**Aplicar o mesmo padrão em cada método:**

`resumo(guarnicao_id, dias)` — filtros de `Abordagem.guarnicao_id` nos dois selects

`mapa_calor(guarnicao_id, dias)` — filtro no único select

`horarios_pico(guarnicao_id, dias)` — filtro no único select

`pessoas_recorrentes(guarnicao_id, limit)` — filtro no `.where()` do select

`resumo_hoje(guarnicao_id)` — filtros nos dois selects (ver padrão acima)

`resumo_mes(guarnicao_id)` — filtros nos dois selects (mesmo padrão)

`resumo_total(guarnicao_id)` — três selects: abordagens, pessoas_abordadas, pessoas_cadastradas:
```python
# Pessoas cadastradas — também condicional:
pessoas_cadastradas_q = select(func.count(Pessoa.id)).where(Pessoa.ativo)
if guarnicao_id is not None:
    pessoas_cadastradas_q = pessoas_cadastradas_q.where(Pessoa.guarnicao_id == guarnicao_id)
```

`por_dia(guarnicao_id, dias)` — filtro no `.where()`

`por_mes(guarnicao_id, meses)` — filtro no `.where()`

`dias_com_abordagem(guarnicao_id, mes)` — filtro no `.where()`

`pessoas_do_dia(guarnicao_id, data)` — filtro no `.where()`

`abordagens_do_dia(guarnicao_id, data)` — filtro no `.where()`

`metricas_rag(guarnicao_id)` — usa raw SQL, ajustar assim:
```python
async def metricas_rag(self, guarnicao_id: int | None) -> dict:
    from sqlalchemy import text as sql_text

    if guarnicao_id is not None:
        result_total = await self.db.execute(
            sql_text("SELECT COUNT(*) FROM ocorrencias WHERE guarnicao_id = :gid AND ativo = true"),
            {"gid": guarnicao_id},
        )
        result_indexadas = await self.db.execute(
            sql_text(
                "SELECT COUNT(*) FROM ocorrencias"
                " WHERE guarnicao_id = :gid AND ativo = true AND embedding IS NOT NULL"
            ),
            {"gid": guarnicao_id},
        )
    else:
        result_total = await self.db.execute(
            sql_text("SELECT COUNT(*) FROM ocorrencias WHERE ativo = true")
        )
        result_indexadas = await self.db.execute(
            sql_text(
                "SELECT COUNT(*) FROM ocorrencias WHERE ativo = true AND embedding IS NOT NULL"
            )
        )
    return {
        "total_ocorrencias": result_total.scalar() or 0,
        "ocorrencias_indexadas": result_indexadas.scalar() or 0,
    }
```

**Step 2: Rodar testes unitários para garantir que não quebrou nada**

```bash
make test -- tests/unit/ -v
```

Esperado: todos passam

**Step 3: Commit**

```bash
git add app/services/analytics_service.py
git commit -m "feat(analytics): guarnicao_id: int | None — suporte a consulta global"
```

---

### Task 3: Fix analytics router — calcular guarnicao_filter

**Files:**
- Modify: `app/api/v1/analytics.py`

**Step 1: Adicionar helper no topo do router (após os imports existentes)**

```python
def _guarnicao_filter(user: Usuario) -> int | None:
    """Retorna guarnicao_id se isolamento ativo, None para acesso global."""
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return user.guarnicao_id
    return None
```

**Step 2: Substituir `user.guarnicao_id` por `_guarnicao_filter(user)` em TODOS os endpoints**

Cada endpoint passa de:
```python
return await service.pessoas_recorrentes(user.guarnicao_id, limit)
```
Para:
```python
return await service.pessoas_recorrentes(_guarnicao_filter(user), limit)
```

Endpoints a ajustar (todas as chamadas ao service):
- `pessoas_recorrentes` → `_guarnicao_filter(user)`
- `resumo_hoje` → `_guarnicao_filter(user)`
- `resumo_mes` → `_guarnicao_filter(user)`
- `resumo_total` → `_guarnicao_filter(user)`
- `por_dia` → `_guarnicao_filter(user)`
- `por_mes` → `_guarnicao_filter(user)`
- `dias_com_abordagem` → `_guarnicao_filter(user)`
- `abordagens_do_dia` → `_guarnicao_filter(user)`
- `pessoas_do_dia` → `_guarnicao_filter(user)`

**Step 3: Rodar os testes de analytics**

```bash
make test -- tests/integration/test_api_analytics.py -v
```

Esperado: todos passam, incluindo os novos da Task 1

**Step 4: Commit**

```bash
git add app/api/v1/analytics.py
git commit -m "feat(analytics): aplicar toggle de isolamento nos endpoints de analytics"
```

---

### Task 4: Testes falhando — consulta: pessoas global, abordagens respeitam toggle

**Files:**
- Modify: `tests/integration/test_api_consulta.py`

**Step 1: Adicionar testes ao final do arquivo**

```python
# Adicionar imports necessários se não existirem:
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario
from app.models.abordagem import Abordagem
from app.models.pessoa import Pessoa
from app.core.security import criar_access_token, hash_senha
from datetime import UTC, datetime


@pytest.fixture
async def equipe_c(db_session: AsyncSession) -> Guarnicao:
    """Equipe C — sem isolamento (toggle OFF)."""
    g = Guarnicao(nome="GU Charlie", unidade="3o BPM", codigo="3BPM-GUC")
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario_c(db_session: AsyncSession, equipe_c: Guarnicao) -> Usuario:
    """Usuário da equipe C."""
    u = Usuario(
        nome="Agente C",
        matricula="CCC001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=equipe_c.id,
        session_id="session-c",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def headers_c(usuario_c: Usuario) -> dict:
    """Headers do usuário C."""
    token = criar_access_token({
        "sub": str(usuario_c.id),
        "guarnicao_id": usuario_c.guarnicao_id,
        "sid": usuario_c.session_id,
    })
    return {"Authorization": f"Bearer {token}"}


class TestConsultaIsolamento:
    """Consulta deve tratar pessoas como global e abordagens conforme toggle."""

    async def test_pessoas_sempre_visiveis_para_outra_equipe(
        self,
        client: AsyncClient,
        headers_c: dict,
        guarnicao: Guarnicao,
        db_session: AsyncSession,
        usuario: Usuario,
    ):
        """Busca de pessoa retorna resultado de outra equipe (pessoas são globais)."""
        # Cria pessoa na equipe A (guarnicao padrão do conftest)
        p = Pessoa(
            nome="Joao Testador Global",
            guarnicao_id=guarnicao.id,
        )
        db_session.add(p)
        await db_session.flush()

        # Usuário C (equipe diferente) busca "Joao"
        response = await client.get(
            "/api/v1/consultas/?q=Joao&tipo=pessoa",
            headers=headers_c,
        )
        assert response.status_code == 200
        data = response.json()
        nomes = [p["nome"] for p in data["pessoas"]]
        assert "Joao Testador Global" in nomes

    async def test_abordagens_toggle_off_ve_global(
        self,
        client: AsyncClient,
        headers_c: dict,
        guarnicao: Guarnicao,
        db_session: AsyncSession,
        usuario: Usuario,
        equipe_c: Guarnicao,
    ):
        """Com toggle OFF, busca de abordagem retorna resultados de outra equipe."""
        a = Abordagem(
            guarnicao_id=guarnicao.id,
            usuario_id=usuario.id,
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Global Teste",
        )
        db_session.add(a)
        await db_session.flush()

        assert equipe_c.isolamento_abordagens is False
        response = await client.get(
            "/api/v1/consultas/?q=Global+Teste&tipo=abordagem",
            headers=headers_c,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["abordagens"]) >= 1

    async def test_abordagens_toggle_on_nao_ve_outra_equipe(
        self,
        client: AsyncClient,
        headers_c: dict,
        guarnicao: Guarnicao,
        db_session: AsyncSession,
        usuario: Usuario,
        equipe_c: Guarnicao,
    ):
        """Com toggle ON, busca de abordagem não retorna resultados de outra equipe."""
        a = Abordagem(
            guarnicao_id=guarnicao.id,
            usuario_id=usuario.id,
            data_hora=datetime.now(UTC),
            endereco_texto="Rua Isolada Teste",
        )
        db_session.add(a)
        await db_session.flush()

        equipe_c.isolamento_abordagens = True
        await db_session.flush()

        response = await client.get(
            "/api/v1/consultas/?q=Isolada+Teste&tipo=abordagem",
            headers=headers_c,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["abordagens"]) == 0
```

**Step 2: Rodar os testes para confirmar que falham**

```bash
make test -- tests/integration/test_api_consulta.py::TestConsultaIsolamento -v
```

Esperado: FAIL — pessoas retorna vazio, abordagens retorna vazio com toggle OFF

**Step 3: Commit dos testes falhando**

```bash
git add tests/integration/test_api_consulta.py
git commit -m "test(consulta): testes falhando para pessoas globais e toggle de abordagens"
```

---

### Task 5: Fix consulta_service e router

**Files:**
- Modify: `app/services/consulta_service.py`
- Modify: `app/api/v1/consultas.py`

**Step 1: Alterar `busca_unificada` no consulta_service**

Mudar a assinatura para receber `isolamento: bool` e separar os filtros:

```python
async def busca_unificada(
    self,
    q: str = "",
    tipo: str | None = None,
    bairro: str | None = None,
    cidade: str | None = None,
    estado: str | None = None,
    skip: int = 0,
    limit: int = 20,
    user: Usuario | None = None,
    isolamento: bool = False,          # <-- novo parâmetro
) -> dict:
```

Dentro do método, substituir a linha:
```python
guarnicao_id = user.guarnicao_id if user else None
```

Por:
```python
# Pessoas são sempre globais (spec do projeto)
guarnicao_id_pessoa = None
# Abordagens e veículos respeitam o toggle de isolamento
guarnicao_id_abordagem = (user.guarnicao_id if user else None) if isolamento else None
```

E ajustar as chamadas internas:
```python
if tipo is None or tipo == "pessoa":
    if filtro_local:
        pessoas = await self.pessoa_repo.search_by_bairro_cidade_com_endereco(
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            guarnicao_id=guarnicao_id_pessoa,   # sempre None
            skip=skip,
            limit=limit,
        )
    else:
        pessoas = await self._buscar_pessoas(q, guarnicao_id_pessoa, skip, limit)  # sempre None

if tipo is None or tipo == "veiculo":
    if not filtro_local:
        veiculos = await self._buscar_veiculos(q, guarnicao_id_abordagem, skip, limit)

if tipo is None or tipo == "abordagem":
    if not filtro_local:
        abordagens = await self._buscar_abordagens(q, guarnicao_id_abordagem, skip, limit)
```

**Step 2: Ajustar `listar_localidades` — também global (pessoas são globais)**

```python
async def listar_localidades(self, guarnicao_id: int | None) -> dict:
```
No router, passar `None` em vez de `user.guarnicao_id`.

**Step 3: Ajustar o consulta router (`app/api/v1/consultas.py`)**

Adicionar helper:
```python
def _isolamento(user: Usuario) -> bool:
    """Retorna True se o toggle de isolamento da equipe está ativado."""
    return bool(user.guarnicao and user.guarnicao.isolamento_abordagens)
```

No endpoint de busca unificada (GET `/`), adicionar `isolamento=_isolamento(user)`:
```python
resultados = await service.busca_unificada(
    q=q,
    tipo=tipo,
    bairro=bairro,
    cidade=cidade,
    estado=estado,
    skip=skip,
    limit=limit,
    user=user,
    isolamento=_isolamento(user),   # <-- novo
)
```

No endpoint de localidades:
```python
return await service.listar_localidades(guarnicao_id=None)  # sempre global
```

**Step 4: Rodar os testes**

```bash
make test -- tests/integration/test_api_consulta.py -v
```

Esperado: todos passam, incluindo os novos da Task 4

**Step 5: Rodar todos os testes para checar regressões**

```bash
make test
```

Esperado: todos passam

**Step 6: Commit**

```bash
git add app/services/consulta_service.py app/api/v1/consultas.py
git commit -m "feat(consulta): pessoas sempre globais, abordagens respeitam toggle de isolamento"
```

---

### Task 6: Mover usuário admin para 3º Pelotão em produção

**Step 1: Rodar no banco de produção via SSH**

```bash
ssh -i ~/.ssh/ssh-key-2026-03-21.key ubuntu@arguseye.duckdns.org
```

```bash
cd ~/argus-ai
docker compose -f docker-compose.prod.yml exec -T db psql -U argus argus_db \
  -c "UPDATE usuarios SET guarnicao_id = 2 WHERE matricula = '7356226' RETURNING id, nome, guarnicao_id;"
```

Esperado:
```
 id |        nome        | guarnicao_id
----+--------------------+--------------
  2 | Alex Monteiro Abud |            2
```

**Step 2: Confirmar toggle do 3º Pelotão está desativado**

```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U argus argus_db \
  -c "SELECT id, nome, isolamento_abordagens FROM guarnicoes WHERE id = 2;"
```

Esperado: `isolamento_abordagens = f` (false)

---

### Task 7: Push e deploy

**Step 1: Push**

```bash
git push
```

**Step 2: Aguardar deploy automático**

O GitHub Actions vai:
1. Rodar CI (testes)
2. Fazer deploy na VM
3. Rodar `alembic upgrade head` (nenhuma migration nova neste PR)
4. Health check

**Step 3: Verificar no browser**

- Acesse `arguseye.duckdns.org` como usuário do 3º Pelotão
- Dashboard deve mostrar contagem global de abordagens
- Busca de "João" deve retornar João de qualquer equipe
- Toggle ON na equipe filtra; Toggle OFF mostra tudo
