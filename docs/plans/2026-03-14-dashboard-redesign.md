# Dashboard Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesenhar o dashboard com cards de resumo (hoje/mês/total), gráficos de linha ApexCharts (por dia e por mês), calendário interativo com lista de pessoas do dia, e top 10 recorrentes com foto e CPF.

**Architecture:** 7 novos métodos no `AnalyticsService`, 7 novos endpoints no router `analytics.py`, e reescrita completa de `frontend/js/pages/dashboard.js`. ApexCharts carregado via CDN. CPF descriptografado no backend com `decrypt()` de `app.core.crypto`.

**Tech Stack:** FastAPI, SQLAlchemy async, Alpine.js, ApexCharts CDN, pytest async.

---

## Task 1: Backend — Resumo Hoje, Mês e Total

**Files:**
- Modify: `app/services/analytics_service.py`
- Test: `tests/unit/test_analytics_service.py`

**Step 1: Escrever testes que vão falhar**

Adicionar ao final de `tests/unit/test_analytics_service.py`:

```python
class TestResumoHoje:
    """Testes para AnalyticsService.resumo_hoje()."""

    async def test_resumo_hoje_retorna_campos_corretos(self):
        """Deve retornar abordagens e pessoas do dia atual."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_hoje(guarnicao_id=1)

        assert "abordagens" in result
        assert "pessoas" in result
        assert result["abordagens"] == 5

    async def test_resumo_hoje_sem_dados_retorna_zeros(self):
        """Deve retornar zeros quando não há abordagens hoje."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_hoje(guarnicao_id=1)

        assert result["abordagens"] == 0
        assert result["pessoas"] == 0


class TestResumoMes:
    """Testes para AnalyticsService.resumo_mes()."""

    async def test_resumo_mes_retorna_campos_corretos(self):
        """Deve retornar abordagens e pessoas do mês atual."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 20
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_mes(guarnicao_id=1)

        assert "abordagens" in result
        assert "pessoas" in result
        assert result["abordagens"] == 20


class TestResumoTotal:
    """Testes para AnalyticsService.resumo_total()."""

    async def test_resumo_total_retorna_campos_corretos(self):
        """Deve retornar totais sem filtro de data."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.resumo_total(guarnicao_id=1)

        assert "abordagens" in result
        assert "pessoas" in result
        assert result["abordagens"] == 100
```

**Step 2: Rodar para confirmar que falham**

```bash
pytest tests/unit/test_analytics_service.py::TestResumoHoje tests/unit/test_analytics_service.py::TestResumoMes tests/unit/test_analytics_service.py::TestResumoTotal -v
```

Esperado: `AttributeError: 'AnalyticsService' object has no attribute 'resumo_hoje'`

**Step 3: Implementar os três métodos em `app/services/analytics_service.py`**

Adicionar após o método `resumo()` existente (linha ~74):

```python
async def resumo_hoje(self, guarnicao_id: int) -> dict:
    """Retorna total de abordagens e pessoas abordadas hoje.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.

    Returns:
        Dicionário com abordagens e pessoas do dia atual.
    """
    hoje = datetime.now(UTC).date()

    total_q = select(func.count(Abordagem.id)).where(
        Abordagem.guarnicao_id == guarnicao_id,
        Abordagem.ativo,
        func.date(Abordagem.data_hora) == hoje,
    )
    total = (await self.db.execute(total_q)).scalar() or 0

    pessoas_q = (
        select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
        .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
            func.date(Abordagem.data_hora) == hoje,
        )
    )
    pessoas = (await self.db.execute(pessoas_q)).scalar() or 0

    return {"abordagens": total, "pessoas": pessoas}

async def resumo_mes(self, guarnicao_id: int) -> dict:
    """Retorna total de abordagens e pessoas abordadas no mês atual.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.

    Returns:
        Dicionário com abordagens e pessoas do mês corrente.
    """
    agora = datetime.now(UTC)
    ano = agora.year
    mes = agora.month

    total_q = select(func.count(Abordagem.id)).where(
        Abordagem.guarnicao_id == guarnicao_id,
        Abordagem.ativo,
        extract("year", Abordagem.data_hora) == ano,
        extract("month", Abordagem.data_hora) == mes,
    )
    total = (await self.db.execute(total_q)).scalar() or 0

    pessoas_q = (
        select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
        .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
            extract("year", Abordagem.data_hora) == ano,
            extract("month", Abordagem.data_hora) == mes,
        )
    )
    pessoas = (await self.db.execute(pessoas_q)).scalar() or 0

    return {"abordagens": total, "pessoas": pessoas}

async def resumo_total(self, guarnicao_id: int) -> dict:
    """Retorna totais históricos de abordagens e pessoas.

    Sem filtro de data — agrega todos os registros ativos da guarnição.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.

    Returns:
        Dicionário com abordagens e pessoas totais.
    """
    total_q = select(func.count(Abordagem.id)).where(
        Abordagem.guarnicao_id == guarnicao_id,
        Abordagem.ativo,
    )
    total = (await self.db.execute(total_q)).scalar() or 0

    pessoas_q = (
        select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
        .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
        )
    )
    pessoas = (await self.db.execute(pessoas_q)).scalar() or 0

    return {"abordagens": total, "pessoas": pessoas}
```

**Step 4: Rodar testes para confirmar que passam**

```bash
pytest tests/unit/test_analytics_service.py -v
```

Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/services/analytics_service.py tests/unit/test_analytics_service.py
git commit -m "feat(analytics): adicionar resumo_hoje, resumo_mes e resumo_total"
```

---

## Task 2: Backend — Série Temporal Por Dia e Por Mês

**Files:**
- Modify: `app/services/analytics_service.py`
- Test: `tests/unit/test_analytics_service.py`

**Step 1: Escrever testes que vão falhar**

Adicionar ao final de `tests/unit/test_analytics_service.py`:

```python
class TestPorDia:
    """Testes para AnalyticsService.por_dia()."""

    async def test_por_dia_retorna_lista_de_dicts(self):
        """Deve retornar lista com data, abordagens e pessoas por dia."""
        from datetime import date as date_type
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (date_type(2026, 3, 14), 3, 5),
            (date_type(2026, 3, 15), 1, 2),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.por_dia(guarnicao_id=1, dias=30)

        assert len(result) == 2
        assert result[0]["data"] == "2026-03-14"
        assert result[0]["abordagens"] == 3
        assert result[0]["pessoas"] == 5

    async def test_por_dia_sem_dados_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há abordagens."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.por_dia(guarnicao_id=1, dias=30)

        assert result == []


class TestPorMes:
    """Testes para AnalyticsService.por_mes()."""

    async def test_por_mes_retorna_lista_de_dicts(self):
        """Deve retornar lista com mes, abordagens e pessoas por mês."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (2026, 2, 40, 65),
            (2026, 3, 15, 22),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.por_mes(guarnicao_id=1, meses=12)

        assert len(result) == 2
        assert result[0]["mes"] == "2026-02"
        assert result[0]["abordagens"] == 40
        assert result[0]["pessoas"] == 65
```

**Step 2: Rodar para confirmar que falham**

```bash
pytest tests/unit/test_analytics_service.py::TestPorDia tests/unit/test_analytics_service.py::TestPorMes -v
```

Esperado: `AttributeError: 'AnalyticsService' object has no attribute 'por_dia'`

**Step 3: Implementar em `app/services/analytics_service.py`**

Adicionar `date` ao import do topo do arquivo (já existe `datetime`):

```python
from datetime import UTC, date, datetime, timedelta
```

Adicionar os métodos após `resumo_total`:

```python
async def por_dia(self, guarnicao_id: int, dias: int = 30) -> list[dict]:
    """Retorna série temporal diária de abordagens e pessoas.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        dias: Número de dias retroativos (padrão 30).

    Returns:
        Lista de dicionários com data (YYYY-MM-DD), abordagens e pessoas.
    """
    desde = datetime.now(UTC) - timedelta(days=dias)
    data_label = func.date(Abordagem.data_hora).label("data")

    query = (
        select(
            data_label,
            func.count(func.distinct(Abordagem.id)).label("abordagens"),
            func.count(func.distinct(AbordagemPessoa.pessoa_id)).label("pessoas"),
        )
        .outerjoin(AbordagemPessoa, AbordagemPessoa.abordagem_id == Abordagem.id)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
            Abordagem.data_hora >= desde,
        )
        .group_by(data_label)
        .order_by(data_label)
    )
    result = await self.db.execute(query)
    return [
        {
            "data": row[0].strftime("%Y-%m-%d") if hasattr(row[0], "strftime") else str(row[0]),
            "abordagens": int(row[1]),
            "pessoas": int(row[2]),
        }
        for row in result.all()
    ]

async def por_mes(self, guarnicao_id: int, meses: int = 12) -> list[dict]:
    """Retorna série temporal mensal de abordagens e pessoas.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        meses: Número de meses retroativos (padrão 12).

    Returns:
        Lista de dicionários com mes (YYYY-MM), abordagens e pessoas.
    """
    desde = datetime.now(UTC) - timedelta(days=meses * 30)
    ano_label = extract("year", Abordagem.data_hora).label("ano")
    mes_label = extract("month", Abordagem.data_hora).label("mes")

    query = (
        select(
            ano_label,
            mes_label,
            func.count(func.distinct(Abordagem.id)).label("abordagens"),
            func.count(func.distinct(AbordagemPessoa.pessoa_id)).label("pessoas"),
        )
        .outerjoin(AbordagemPessoa, AbordagemPessoa.abordagem_id == Abordagem.id)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
            Abordagem.data_hora >= desde,
        )
        .group_by(ano_label, mes_label)
        .order_by(ano_label, mes_label)
    )
    result = await self.db.execute(query)
    return [
        {
            "mes": f"{int(row[0])}-{int(row[1]):02d}",
            "abordagens": int(row[2]),
            "pessoas": int(row[3]),
        }
        for row in result.all()
    ]
```

**Step 4: Rodar testes**

```bash
pytest tests/unit/test_analytics_service.py -v
```

Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/services/analytics_service.py tests/unit/test_analytics_service.py
git commit -m "feat(analytics): adicionar series temporais por_dia e por_mes"
```

---

## Task 3: Backend — Dias com Abordagem e Pessoas do Dia

**Files:**
- Modify: `app/services/analytics_service.py`
- Test: `tests/unit/test_analytics_service.py`

**Step 1: Escrever testes que vão falhar**

Adicionar ao final de `tests/unit/test_analytics_service.py`. Adicionar o import no topo do arquivo:
`from datetime import date as date_type` (dentro do teste).

```python
class TestDiasComAbordagem:
    """Testes para AnalyticsService.dias_com_abordagem()."""

    async def test_retorna_lista_de_inteiros(self):
        """Deve retornar lista de dias do mês com abordagem."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [(14,), (15,), (20,)]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.dias_com_abordagem(guarnicao_id=1, mes="2026-03")

        assert result == [14, 15, 20]

    async def test_sem_abordagens_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há abordagens no mês."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.dias_com_abordagem(guarnicao_id=1, mes="2026-03")

        assert result == []


class TestPessoasDoDia:
    """Testes para AnalyticsService.pessoas_do_dia()."""

    async def test_retorna_lista_com_campos_corretos(self):
        """Deve retornar id, nome, cpf e foto_url das pessoas do dia."""
        from unittest.mock import patch
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (1, "João Silva", b"cpf_enc", "https://r2.example.com/foto.jpg"),
        ]
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        with patch("app.services.analytics_service.decrypt", return_value="123.456.789-00"):
            result = await service.pessoas_do_dia(guarnicao_id=1, data="2026-03-14")

        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["nome"] == "João Silva"
        assert result[0]["cpf"] == "123.456.789-00"
        assert result[0]["foto_url"] == "https://r2.example.com/foto.jpg"

    async def test_sem_pessoas_retorna_lista_vazia(self):
        """Deve retornar lista vazia quando não há abordagens no dia."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        service = AnalyticsService(db)

        result = await service.pessoas_do_dia(guarnicao_id=1, data="2026-03-14")

        assert result == []
```

**Step 2: Rodar para confirmar que falham**

```bash
pytest tests/unit/test_analytics_service.py::TestDiasComAbordagem tests/unit/test_analytics_service.py::TestPessoasDoDia -v
```

**Step 3: Implementar em `app/services/analytics_service.py`**

Adicionar import no topo do arquivo:
```python
from app.core.crypto import decrypt
from app.models.pessoa import Pessoa
```

Adicionar métodos após `por_mes`:

```python
async def dias_com_abordagem(self, guarnicao_id: int, mes: str) -> list[int]:
    """Retorna lista de dias do mês que tiveram abordagem.

    Usado pelo calendário mini para exibir pontos indicativos.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        mes: Mês no formato "YYYY-MM" (ex: "2026-03").

    Returns:
        Lista de inteiros representando os dias com abordagem.
    """
    ano, mes_num = int(mes.split("-")[0]), int(mes.split("-")[1])
    dia_label = extract("day", Abordagem.data_hora).label("dia")

    query = (
        select(dia_label)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
            extract("year", Abordagem.data_hora) == ano,
            extract("month", Abordagem.data_hora) == mes_num,
        )
        .distinct()
        .order_by(dia_label)
    )
    result = await self.db.execute(query)
    return [int(row[0]) for row in result.all()]

async def pessoas_do_dia(self, guarnicao_id: int, data: str) -> list[dict]:
    """Retorna pessoas abordadas em um dia específico.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        data: Data no formato "YYYY-MM-DD" (ex: "2026-03-14").

    Returns:
        Lista de dicionários com id, nome, cpf e foto_url.
    """
    from datetime import date as date_type
    data_obj = date_type.fromisoformat(data)

    query = (
        select(
            Pessoa.id,
            Pessoa.nome,
            Pessoa.cpf_encrypted,
            Pessoa.foto_principal_url,
        )
        .join(AbordagemPessoa, AbordagemPessoa.pessoa_id == Pessoa.id)
        .join(Abordagem, Abordagem.id == AbordagemPessoa.abordagem_id)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
            Pessoa.ativo,
            func.date(Abordagem.data_hora) == data_obj,
        )
        .distinct()
    )
    result = await self.db.execute(query)
    rows = result.all()

    pessoas = []
    for row in rows:
        cpf = decrypt(row[2]) if row[2] else None
        pessoas.append({
            "id": row[0],
            "nome": row[1],
            "cpf": cpf,
            "foto_url": row[3],
        })
    return pessoas
```

**Step 4: Rodar testes**

```bash
pytest tests/unit/test_analytics_service.py -v
```

Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/services/analytics_service.py tests/unit/test_analytics_service.py
git commit -m "feat(analytics): adicionar dias_com_abordagem e pessoas_do_dia"
```

---

## Task 4: Backend — Atualizar pessoas_recorrentes com foto e CPF

**Files:**
- Modify: `app/services/analytics_service.py`
- Test: `tests/unit/test_analytics_service.py`

**Step 1: Atualizar o teste existente `TestPessoasRecorrentes`**

Encontrar o teste `test_pessoas_retorna_formato_correto` e atualizar o `mock_result.all.return_value` para incluir `cpf_encrypted` e `foto_principal_url` nos dados mockados:

```python
async def test_pessoas_retorna_formato_correto(self):
    """Deve retornar lista com id, nome, apelido, total, ultima, cpf e foto."""
    from unittest.mock import patch
    db = AsyncMock()
    now = datetime.now(UTC)
    mock_result = MagicMock()
    mock_result.all.return_value = [
        (1, "João", "Joãozinho", 5, now, b"cpf_enc", "https://r2.example.com/foto.jpg"),
    ]
    db.execute = AsyncMock(return_value=mock_result)
    service = AnalyticsService(db)

    with patch("app.services.analytics_service.decrypt", return_value="123.456.789-00"):
        result = await service.pessoas_recorrentes(guarnicao_id=1)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["nome"] == "João"
    assert result[0]["total_abordagens"] == 5
    assert result[0]["cpf"] == "123.456.789-00"
    assert result[0]["foto_url"] == "https://r2.example.com/foto.jpg"
```

**Step 2: Rodar para confirmar que falha**

```bash
pytest tests/unit/test_analytics_service.py::TestPessoasRecorrentes::test_pessoas_retorna_formato_correto -v
```

**Step 3: Atualizar `pessoas_recorrentes` em `app/services/analytics_service.py`**

Adicionar `Pessoa.cpf_encrypted` e `Pessoa.foto_principal_url` ao select e ao retorno:

```python
async def pessoas_recorrentes(self, guarnicao_id: int, limit: int = 20) -> list[dict]:
    """Retorna pessoas mais abordadas.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        limit: Número máximo de resultados (padrão 20, máximo 100).

    Returns:
        Lista de dicionários com id, nome, apelido, total_abordagens,
        ultima_abordagem, cpf e foto_url.
    """
    limit = min(limit, 100)

    query = (
        select(
            Pessoa.id,
            Pessoa.nome,
            Pessoa.apelido,
            func.count(AbordagemPessoa.abordagem_id).label("total"),
            func.max(Abordagem.data_hora).label("ultima"),
            Pessoa.cpf_encrypted,
            Pessoa.foto_principal_url,
        )
        .join(AbordagemPessoa, Pessoa.id == AbordagemPessoa.pessoa_id)
        .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo,
            Pessoa.ativo,
        )
        .group_by(Pessoa.id, Pessoa.nome, Pessoa.apelido, Pessoa.cpf_encrypted, Pessoa.foto_principal_url)
        .order_by(func.count(AbordagemPessoa.abordagem_id).desc())
        .limit(limit)
    )
    result = await self.db.execute(query)
    return [
        {
            "id": row[0],
            "nome": row[1],
            "apelido": row[2],
            "total_abordagens": int(row[3]),
            "ultima_abordagem": row[4].isoformat() if row[4] else None,
            "cpf": decrypt(row[5]) if row[5] else None,
            "foto_url": row[6],
        }
        for row in result.all()
    ]
```

**Step 4: Rodar testes**

```bash
pytest tests/unit/test_analytics_service.py -v
```

Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/services/analytics_service.py tests/unit/test_analytics_service.py
git commit -m "feat(analytics): adicionar cpf e foto_url em pessoas_recorrentes"
```

---

## Task 5: Backend — Novos endpoints no router

**Files:**
- Modify: `app/api/v1/analytics.py`
- Test: `tests/integration/test_api_analytics.py`

**Step 1: Escrever testes de integração que vão falhar**

Adicionar ao final de `tests/integration/test_api_analytics.py`:

```python
class TestResumoHoje:
    """Testes do endpoint GET /api/v1/analytics/resumo-hoje."""

    async def test_resumo_hoje_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar abordagens e pessoas do dia."""
        response = await client.get("/api/v1/analytics/resumo-hoje", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data

    async def test_resumo_hoje_sem_auth_retorna_403(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação."""
        response = await client.get("/api/v1/analytics/resumo-hoje")
        assert response.status_code == 403


class TestResumoMesEndpoint:
    """Testes do endpoint GET /api/v1/analytics/resumo-mes."""

    async def test_resumo_mes_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar abordagens e pessoas do mês."""
        response = await client.get("/api/v1/analytics/resumo-mes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data


class TestResumoTotalEndpoint:
    """Testes do endpoint GET /api/v1/analytics/resumo-total."""

    async def test_resumo_total_retorna_200(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar totais históricos."""
        response = await client.get("/api/v1/analytics/resumo-total", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "abordagens" in data
        assert "pessoas" in data


class TestPorDiaEndpoint:
    """Testes do endpoint GET /api/v1/analytics/por-dia."""

    async def test_por_dia_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de abordagens por dia."""
        response = await client.get("/api/v1/analytics/por-dia", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_por_dia_aceita_parametro_dias(self, client: AsyncClient, auth_headers: dict):
        """Deve aceitar parâmetro dias."""
        response = await client.get("/api/v1/analytics/por-dia?dias=7", headers=auth_headers)
        assert response.status_code == 200


class TestPorMesEndpoint:
    """Testes do endpoint GET /api/v1/analytics/por-mes."""

    async def test_por_mes_retorna_lista(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de abordagens por mês."""
        response = await client.get("/api/v1/analytics/por-mes", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDiasComAbordagemEndpoint:
    """Testes do endpoint GET /api/v1/analytics/dias-com-abordagem."""

    async def test_retorna_lista_de_dias(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de dias com abordagem no mês."""
        response = await client.get(
            "/api/v1/analytics/dias-com-abordagem?mes=2026-03",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_mes_invalido_retorna_422(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar 422 para formato de mês inválido."""
        response = await client.get(
            "/api/v1/analytics/dias-com-abordagem?mes=invalido",
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestPessoasDoDiaEndpoint:
    """Testes do endpoint GET /api/v1/analytics/pessoas-do-dia."""

    async def test_retorna_lista_de_pessoas(self, client: AsyncClient, auth_headers: dict):
        """Deve retornar lista de pessoas abordadas no dia."""
        response = await client.get(
            "/api/v1/analytics/pessoas-do-dia?data=2026-03-14",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

**Step 2: Rodar para confirmar que falham**

```bash
pytest tests/integration/test_api_analytics.py::TestResumoHoje -v
```

Esperado: `404 Not Found`

**Step 3: Adicionar endpoints em `app/api/v1/analytics.py`**

Adicionar no topo: `from datetime import date` e `import re`.

Adicionar após o endpoint existente `pessoas_recorrentes`:

```python
@router.get("/resumo-hoje")
async def resumo_hoje(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna total de abordagens e pessoas abordadas hoje.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com abordagens e pessoas do dia atual.
    """
    service = AnalyticsService(db)
    return await service.resumo_hoje(user.guarnicao_id)


@router.get("/resumo-mes")
async def resumo_mes(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna total de abordagens e pessoas abordadas no mês atual.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com abordagens e pessoas do mês corrente.
    """
    service = AnalyticsService(db)
    return await service.resumo_mes(user.guarnicao_id)


@router.get("/resumo-total")
async def resumo_total(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna totais históricos de abordagens e pessoas.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com abordagens e pessoas totais.
    """
    service = AnalyticsService(db)
    return await service.resumo_total(user.guarnicao_id)


@router.get("/por-dia")
async def por_dia(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna série temporal diária de abordagens e pessoas.

    Args:
        dias: Número de dias retroativos (1-365, padrão 30).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com data, abordagens e pessoas por dia.
    """
    service = AnalyticsService(db)
    return await service.por_dia(user.guarnicao_id, dias)


@router.get("/por-mes")
async def por_mes(
    meses: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna série temporal mensal de abordagens e pessoas.

    Args:
        meses: Número de meses retroativos (1-36, padrão 12).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com mes, abordagens e pessoas por mês.
    """
    service = AnalyticsService(db)
    return await service.por_mes(user.guarnicao_id, meses)


@router.get("/dias-com-abordagem")
async def dias_com_abordagem(
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[int]:
    """Retorna dias do mês que tiveram abordagem registrada.

    Usado pelo calendário mini para exibir indicadores nos dias com atividade.

    Args:
        mes: Mês no formato YYYY-MM (ex: "2026-03").
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de inteiros representando os dias com abordagem.
    """
    service = AnalyticsService(db)
    return await service.dias_com_abordagem(user.guarnicao_id, mes)


@router.get("/pessoas-do-dia")
async def pessoas_do_dia(
    data: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna pessoas abordadas em um dia específico.

    Args:
        data: Data no formato YYYY-MM-DD.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com id, nome, cpf e foto_url das pessoas abordadas.
    """
    service = AnalyticsService(db)
    return await service.pessoas_do_dia(user.guarnicao_id, str(data))
```

**Step 4: Rodar testes de integração**

```bash
pytest tests/integration/test_api_analytics.py -v
```

Esperado: todos passando.

**Step 5: Commit**

```bash
git add app/api/v1/analytics.py tests/integration/test_api_analytics.py
git commit -m "feat(api): adicionar endpoints de resumo, series temporais e calendario"
```

---

## Task 6: Frontend — Adicionar ApexCharts ao index.html

**Files:**
- Modify: `frontend/index.html`

**Step 1: Adicionar script CDN do ApexCharts**

No arquivo `frontend/index.html`, encontrar a linha com o script do Alpine.js:
```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
```

Adicionar **antes** dessa linha (ApexCharts não pode ser defer — Alpine.js pode precisar dele já carregado):

```html
<script src="https://cdn.jsdelivr.net/npm/apexcharts@3"></script>
```

**Step 2: Verificar no browser**

Abrir o app localmente e verificar no console do browser que `ApexCharts` está disponível como variável global:
```javascript
typeof ApexCharts // deve retornar "function"
```

**Step 3: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): adicionar ApexCharts via CDN"
```

---

## Task 7: Frontend — Reescrever dashboard.js

**Files:**
- Modify: `frontend/js/pages/dashboard.js`

Este é o arquivo central do redesign. Substituir todo o conteúdo por:

**Step 1: Escrever a nova `renderDashboard()`**

```javascript
/**
 * Página de dashboard analítico — Argus AI.
 *
 * Cards de resumo por período (hoje/mês/total), gráficos de linha ApexCharts
 * (por dia e por mês), calendário interativo com pessoas do dia escolhido,
 * e top 10 pessoas recorrentes.
 */
function renderDashboard() {
  return `
    <div x-data="dashboardPage()" x-init="load()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Dashboard</h2>

      <!-- Loading -->
      <div x-show="loading" class="flex justify-center py-12">
        <span class="spinner"></span>
      </div>

      <template x-if="!loading">
        <div class="space-y-5">

          <!-- === SEÇÃO 1: Cards de Resumo === -->
          <!-- Card: Hoje -->
          <div class="card">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Hoje</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="text-center">
                <p class="text-2xl font-bold text-blue-400" x-text="hoje.abordagens ?? 0"></p>
                <p class="text-xs text-slate-400">Abordagens</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-green-400" x-text="hoje.pessoas ?? 0"></p>
                <p class="text-xs text-slate-400">Pessoas</p>
              </div>
            </div>
          </div>

          <!-- Card: Este Mês -->
          <div class="card">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Este Mês</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="text-center">
                <p class="text-2xl font-bold text-blue-400" x-text="mes.abordagens ?? 0"></p>
                <p class="text-xs text-slate-400">Abordagens</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-green-400" x-text="mes.pessoas ?? 0"></p>
                <p class="text-xs text-slate-400">Pessoas</p>
              </div>
            </div>
          </div>

          <!-- Card: Total -->
          <div class="card">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Total</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="text-center">
                <p class="text-2xl font-bold text-blue-400" x-text="total.abordagens ?? 0"></p>
                <p class="text-xs text-slate-400">Abordagens</p>
              </div>
              <div class="text-center">
                <p class="text-2xl font-bold text-green-400" x-text="total.pessoas ?? 0"></p>
                <p class="text-xs text-slate-400">Pessoas</p>
              </div>
            </div>
          </div>

          <!-- === SEÇÃO 2: Gráficos === -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Abordagens por Dia (últimos 30 dias)</h3>
            <div id="chart-por-dia"></div>
          </div>

          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Abordagens por Mês (últimos 12 meses)</h3>
            <div id="chart-por-mes"></div>
          </div>

          <!-- === SEÇÃO 3: Calendário + Pessoas do Dia === -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Pessoas Abordadas por Dia</h3>

            <!-- Navegação do calendário -->
            <div class="flex items-center justify-between mb-3">
              <button @click="mesMenos()" class="text-slate-400 hover:text-slate-200 px-2 py-1 text-lg">‹</button>
              <span class="text-sm font-medium text-slate-200" x-text="mesAtualLabel"></span>
              <button @click="mesMais()" class="text-slate-400 hover:text-slate-200 px-2 py-1 text-lg">›</button>
            </div>

            <!-- Grid do calendário -->
            <div class="grid grid-cols-7 gap-1 text-center mb-1">
              <template x-for="d in ['D','S','T','Q','Q','S','S']" :key="d + Math.random()">
                <span class="text-[10px] text-slate-500 font-medium" x-text="d"></span>
              </template>
            </div>
            <div class="grid grid-cols-7 gap-1 text-center mb-4">
              <!-- Células vazias do começo do mês -->
              <template x-for="_ in primeiroDiaSemana" :key="'vazio-' + _">
                <div></div>
              </template>
              <!-- Dias do mês -->
              <template x-for="dia in diasDoMes" :key="dia">
                <button
                  class="relative text-xs py-1 rounded"
                  :class="{
                    'bg-blue-600 text-white font-bold': diaSelecionado === dia && mesCalendarioAtual === mesHoje && anoCalendarioAtual === anoHoje,
                    'bg-blue-600 text-white font-bold': diaSelecionado === dia,
                    'text-slate-300 hover:bg-slate-700': diaSelecionado !== dia,
                  }"
                  @click="selecionarDia(dia)"
                  x-text="dia">
                </button>
              </template>
            </div>
            <!-- Pontos de dias com abordagem (renderizados em overlay pelo Alpine via x-effect) -->
            <!-- A lógica de pontinhos é controlada via diasComAbordagem no JS -->

            <!-- Loading pessoas do dia -->
            <div x-show="loadingPessoas" class="flex justify-center py-4">
              <span class="spinner"></span>
            </div>

            <!-- Lista de pessoas do dia -->
            <div x-show="!loadingPessoas">
              <div x-show="pessoasDoDia.length === 0" class="text-xs text-slate-500 text-center py-4">
                Nenhuma abordagem neste dia.
              </div>
              <div class="space-y-2">
                <template x-for="p in pessoasDoDia" :key="p.id">
                  <div
                    class="flex items-center gap-3 cursor-pointer hover:bg-slate-700 rounded p-1 -mx-1"
                    @click="navigate('pessoa-detalhe', { id: p.id })">
                    <!-- Foto -->
                    <img
                      :src="p.foto_url || '/icons/icon-192.png'"
                      class="w-8 h-8 rounded-full object-cover flex-shrink-0 bg-slate-700"
                      :alt="p.nome">
                    <!-- Info -->
                    <div class="min-w-0">
                      <p class="text-sm text-slate-200 truncate" x-text="p.nome"></p>
                      <p class="text-xs text-slate-400" x-text="p.cpf || '—'"></p>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- === SEÇÃO 4: Pessoas Recorrentes === -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Pessoas Recorrentes</h3>
            <div x-show="recorrentes.length === 0" class="text-xs text-slate-500 text-center py-4">
              Nenhum dado disponível.
            </div>
            <div class="space-y-2">
              <template x-for="(p, i) in recorrentes" :key="p.id">
                <div
                  class="flex items-center gap-3 cursor-pointer hover:bg-slate-700 rounded p-1 -mx-1"
                  @click="navigate('pessoa-detalhe', { id: p.id })">
                  <span class="text-xs text-slate-500 w-5 flex-shrink-0" x-text="(i+1) + '.'"></span>
                  <img
                    :src="p.foto_url || '/icons/icon-192.png'"
                    class="w-8 h-8 rounded-full object-cover flex-shrink-0 bg-slate-700"
                    :alt="p.nome">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm text-slate-200 truncate" x-text="p.nome"></p>
                    <p class="text-xs text-slate-400" x-text="p.cpf || '—'"></p>
                  </div>
                  <span class="text-blue-400 font-bold text-sm flex-shrink-0" x-text="p.total_abordagens + 'x'"></span>
                </div>
              </template>
            </div>
          </div>

        </div>
      </template>
    </div>
  `;
}
```

**Step 2: Escrever a função `dashboardPage()`**

```javascript
function dashboardPage() {
  const hoje = new Date();
  return {
    loading: true,
    loadingPessoas: false,

    // Resumos
    hoje: {},
    mes: {},
    total: {},

    // Gráficos (dados brutos)
    porDia: [],
    porMes: [],

    // Calendário
    anoCalendarioAtual: hoje.getFullYear(),
    mesCalendarioAtual: hoje.getMonth() + 1, // 1-12
    anoHoje: hoje.getFullYear(),
    mesHoje: hoje.getMonth() + 1,
    diaHoje: hoje.getDate(),
    diaSelecionado: hoje.getDate(),
    diasComAbordagem: [],
    pessoasDoDia: [],

    // Recorrentes
    recorrentes: [],

    get mesAtualLabel() {
      const meses = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                     'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
      return `${meses[this.mesCalendarioAtual - 1]} ${this.anoCalendarioAtual}`;
    },

    get primeiroDiaSemana() {
      // Retorna array para iterar (células vazias antes do dia 1)
      const d = new Date(this.anoCalendarioAtual, this.mesCalendarioAtual - 1, 1);
      return Array.from({ length: d.getDay() });
    },

    get diasDoMes() {
      const total = new Date(this.anoCalendarioAtual, this.mesCalendarioAtual, 0).getDate();
      return Array.from({ length: total }, (_, i) => i + 1);
    },

    diaTemAbordagem(dia) {
      return this.diasComAbordagem.includes(dia);
    },

    isDiaSelecionado(dia) {
      return this.diaSelecionado === dia
        && this.mesCalendarioAtual === this._mesSelec
        && this.anoCalendarioAtual === this._anoSelec;
    },

    async mesMenos() {
      if (this.mesCalendarioAtual === 1) {
        this.mesCalendarioAtual = 12;
        this.anoCalendarioAtual--;
      } else {
        this.mesCalendarioAtual--;
      }
      this.diaSelecionado = null;
      await this.carregarDiasComAbordagem();
    },

    async mesMais() {
      if (this.mesCalendarioAtual === 12) {
        this.mesCalendarioAtual = 1;
        this.anoCalendarioAtual++;
      } else {
        this.mesCalendarioAtual++;
      }
      this.diaSelecionado = null;
      await this.carregarDiasComAbordagem();
    },

    async selecionarDia(dia) {
      this.diaSelecionado = dia;
      this._mesSelec = this.mesCalendarioAtual;
      this._anoSelec = this.anoCalendarioAtual;
      const dataStr = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
      await this.carregarPessoasDoDia(dataStr);
    },

    async carregarDiasComAbordagem() {
      const mes = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}`;
      this.diasComAbordagem = await api.get(`/analytics/dias-com-abordagem?mes=${mes}`).catch(() => []);
    },

    async carregarPessoasDoDia(data) {
      this.loadingPessoas = true;
      try {
        this.pessoasDoDia = await api.get(`/analytics/pessoas-do-dia?data=${data}`).catch(() => []);
      } finally {
        this.loadingPessoas = false;
      }
    },

    renderizarGraficoPorDia() {
      const categorias = this.porDia.map(d => {
        const [, m, dia] = d.data.split('-');
        return `${dia}/${m}`;
      });
      const serieAbordagens = this.porDia.map(d => d.abordagens);
      const seriePessoas = this.porDia.map(d => d.pessoas);

      new ApexCharts(document.querySelector('#chart-por-dia'), {
        chart: { type: 'line', height: 180, background: 'transparent', toolbar: { show: false } },
        theme: { mode: 'dark' },
        series: [
          { name: 'Abordagens', data: serieAbordagens, color: '#60a5fa' },
          { name: 'Pessoas', data: seriePessoas, color: '#4ade80' },
        ],
        xaxis: { categories: categorias, labels: { style: { fontSize: '9px' }, rotate: -45 } },
        yaxis: { labels: { style: { fontSize: '10px' } } },
        stroke: { curve: 'smooth', width: 2 },
        legend: { labels: { colors: '#94a3b8' } },
        grid: { borderColor: '#334155' },
        tooltip: { theme: 'dark' },
      }).render();
    },

    renderizarGraficoPorMes() {
      const categorias = this.porMes.map(d => {
        const [ano, m] = d.mes.split('-');
        const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
        return `${meses[parseInt(m) - 1]}/${ano.slice(2)}`;
      });
      const serieAbordagens = this.porMes.map(d => d.abordagens);
      const seriePessoas = this.porMes.map(d => d.pessoas);

      new ApexCharts(document.querySelector('#chart-por-mes'), {
        chart: { type: 'line', height: 180, background: 'transparent', toolbar: { show: false } },
        theme: { mode: 'dark' },
        series: [
          { name: 'Abordagens', data: serieAbordagens, color: '#60a5fa' },
          { name: 'Pessoas', data: seriePessoas, color: '#4ade80' },
        ],
        xaxis: { categories: categorias, labels: { style: { fontSize: '10px' } } },
        yaxis: { labels: { style: { fontSize: '10px' } } },
        stroke: { curve: 'smooth', width: 2 },
        legend: { labels: { colors: '#94a3b8' } },
        grid: { borderColor: '#334155' },
        tooltip: { theme: 'dark' },
      }).render();
    },

    async load() {
      try {
        const dataHoje = `${this.anoHoje}-${String(this.mesHoje).padStart(2,'0')}-${String(this.diaHoje).padStart(2,'0')}`;
        const mesAtual = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}`;

        const [resumoHoje, resumoMes, resumoTotal, porDia, porMes, diasAbordagem, pessoasHoje, recorrentes] =
          await Promise.all([
            api.get('/analytics/resumo-hoje').catch(() => ({})),
            api.get('/analytics/resumo-mes').catch(() => ({})),
            api.get('/analytics/resumo-total').catch(() => ({})),
            api.get('/analytics/por-dia?dias=30').catch(() => []),
            api.get('/analytics/por-mes?meses=12').catch(() => []),
            api.get(`/analytics/dias-com-abordagem?mes=${mesAtual}`).catch(() => []),
            api.get(`/analytics/pessoas-do-dia?data=${dataHoje}`).catch(() => []),
            api.get('/analytics/pessoas-recorrentes?limit=10').catch(() => []),
          ]);

        this.hoje = resumoHoje;
        this.mes = resumoMes;
        this.total = resumoTotal;
        this.porDia = porDia;
        this.porMes = porMes;
        this.diasComAbordagem = diasAbordagem;
        this.pessoasDoDia = pessoasHoje;
        this._mesSelec = this.mesCalendarioAtual;
        this._anoSelec = this.anoCalendarioAtual;
        this.recorrentes = recorrentes;
      } catch {
        showToast('Erro ao carregar dashboard', 'error');
      } finally {
        this.loading = false;
        // Aguardar Alpine renderizar os elementos de gráfico
        await this.$nextTick();
        if (this.porDia.length > 0) this.renderizarGraficoPorDia();
        if (this.porMes.length > 0) this.renderizarGraficoPorMes();
      }
    },
  };
}
```

**Step 3: Adicionar pontinhos ao calendário via CSS em Alpine**

No HTML do calendário, a linha do botão de dia precisa mostrar o ponto quando `diaTemAbordagem(dia)`. Substituir o template do botão de dia pelo seguinte (dentro de `renderDashboard`, no template `x-for="dia in diasDoMes"`):

```html
<button
  class="relative text-xs py-1 rounded flex flex-col items-center"
  :class="diaSelecionado === dia && _mesSelec === mesCalendarioAtual && _anoSelec === anoCalendarioAtual
    ? 'bg-blue-600 text-white font-bold'
    : 'text-slate-300 hover:bg-slate-700'"
  @click="selecionarDia(dia)">
  <span x-text="dia"></span>
  <span
    x-show="diaTemAbordagem(dia)"
    class="w-1 h-1 rounded-full bg-blue-400 mt-0.5">
  </span>
</button>
```

**Step 4: Verificar no browser**

Com `make dev` rodando, abrir o app, navegar para o Dashboard e confirmar:
- 3 cards de resumo aparecem (Hoje / Este Mês / Total)
- 2 gráficos de linha ApexCharts aparecem
- Calendário com navegação de mês funciona
- Clicar em um dia carrega a lista de pessoas
- Top 10 recorrentes aparecem com foto
- Clicar em pessoa navega para a ficha

**Step 5: Commit**

```bash
git add frontend/js/pages/dashboard.js
git commit -m "feat(frontend): redesign completo do dashboard com graficos, calendario e recorrentes"
```

---

## Checklist Final

Antes de fechar, confirmar:
- [ ] `pytest tests/unit/test_analytics_service.py -v` → todos passando
- [ ] `pytest tests/integration/test_api_analytics.py -v` → todos passando
- [ ] `make lint` → sem erros de ruff/mypy nos arquivos modificados
- [ ] Dashboard funcional no browser com dados reais ou banco vazio
