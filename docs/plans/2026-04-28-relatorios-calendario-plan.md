# Calendário na Página de Relatórios — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Substituir a lista plana de abordagens por um calendário interativo na página de Relatórios, onde clicar num dia exibe os cards de abordagens daquele dia.

**Architecture:** Adicionar parâmetro opcional `?data=YYYY-MM-DD` ao endpoint `GET /abordagens/` (backend), depois reescrever o componente Alpine.js de `ocorrencias.js` com estado de calendário copiado de `dashboard.js`, reutilizando os endpoints de analytics existentes para os dots do calendário.

**Tech Stack:** FastAPI / SQLAlchemy async / pytest-asyncio / Alpine.js / CSS já existente (`cal-day`, `cal-led`)

---

### Task 1: Repositório — método `list_by_data`

**Files:**
- Modify: `app/repositories/abordagem_repo.py` (após o método `list_by_guarnicao`, linha ~98)
- Test: `tests/unit/test_abordagem_service.py`

**Step 1: Escrever o teste falhando**

Adicionar ao final de `tests/unit/test_abordagem_service.py`:

```python
class TestListarPorData:
    """Testes de listagem de abordagens filtradas por data."""

    async def test_listar_abordagens_com_filtro_data(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Retorna apenas abordagens do dia informado.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        from datetime import date
        from app.models.abordagem import Abordagem

        hoje = datetime.now(UTC)
        ontem = datetime(hoje.year, hoje.month, hoje.day, 10, 0, tzinfo=UTC) - __import__('datetime').timedelta(days=1)

        a_hoje = Abordagem(
            data_hora=datetime(hoje.year, hoje.month, hoje.day, 10, 0, tzinfo=UTC),
            endereco_texto="Rua Hoje, 1",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        a_ontem = Abordagem(
            data_hora=ontem,
            endereco_texto="Rua Ontem, 2",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add_all([a_hoje, a_ontem])
        await db_session.flush()

        service = AbordagemService(db_session)
        result = await service.listar_por_data(
            guarnicao_id=guarnicao.id,
            data=date.today(),
        )
        assert len(result) == 1
        assert result[0].endereco_texto == "Rua Hoje, 1"

    async def test_listar_abordagens_data_sem_resultados(
        self, db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario
    ):
        """Retorna lista vazia para dia sem abordagens.

        Args:
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        from datetime import date, timedelta
        service = AbordagemService(db_session)
        data_futura = date.today() + timedelta(days=365)
        result = await service.listar_por_data(
            guarnicao_id=guarnicao.id,
            data=data_futura,
        )
        assert result == []
```

**Step 2: Rodar e verificar que falha**

```bash
pytest tests/unit/test_abordagem_service.py::TestListarPorData -v
```

Esperado: `FAILED` — `AttributeError: 'AbordagemService' object has no attribute 'listar_por_data'`

**Step 3: Implementar o método no repositório**

Em `app/repositories/abordagem_repo.py`, adicionar imports no topo:

```python
from datetime import date

from sqlalchemy import cast, Date
```

Adicionar método após `list_by_guarnicao` (linha ~98):

```python
async def list_by_data(
    self,
    guarnicao_id: int,
    data: date,
) -> Sequence[Abordagem]:
    """Lista abordagens de uma guarnição em uma data específica.

    Filtra pela data de data_hora (cast para Date, sem hora),
    com eager loading completo de relacionamentos.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        data: Data de referência (YYYY-MM-DD).

    Returns:
        Sequência de Abordagens do dia ordenadas por data_hora decrescente.
    """
    query = (
        select(Abordagem)
        .options(
            selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
            selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
            selectinload(Abordagem.fotos),
            selectinload(Abordagem.ocorrencias),
        )
        .where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.ativo == True,  # noqa: E712
            cast(Abordagem.data_hora, Date) == data,
        )
        .order_by(Abordagem.data_hora.desc())
    )
    result = await self.db.execute(query)
    return result.scalars().all()
```

**Step 4: Implementar o método no service**

Em `app/services/abordagem_service.py`, adicionar import no topo:

```python
from datetime import date
```

Adicionar método após `listar` (linha ~243):

```python
async def listar_por_data(
    self,
    guarnicao_id: int,
    data: date,
) -> Sequence[Abordagem]:
    """Lista abordagens da guarnição em uma data específica.

    Retorna todos os registros do dia sem paginação, com eager
    loading completo de pessoas, veículos, fotos e ocorrências.

    Args:
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        data: Data de referência (YYYY-MM-DD).

    Returns:
        Sequência de Abordagens do dia ordenadas por data_hora decrescente.
    """
    return await self.repo.list_by_data(guarnicao_id, data)
```

**Step 5: Rodar e verificar que passa**

```bash
pytest tests/unit/test_abordagem_service.py::TestListarPorData -v
```

Esperado: `PASSED` (2 testes)

**Step 6: Commit**

```bash
git add app/repositories/abordagem_repo.py app/services/abordagem_service.py tests/unit/test_abordagem_service.py
git commit -m "feat(abordagens): adicionar filtro por data no repositório e service"
```

---

### Task 2: Router — parâmetro `data` no endpoint `GET /abordagens/`

**Files:**
- Modify: `app/api/v1/abordagens.py` (função `listar_abordagens`, linha 83)
- Test: `tests/unit/test_abordagem_service.py` (adicionar teste de rota)

**Step 1: Escrever teste de rota falhando**

Criar `tests/integration/test_abordagens_api.py`:

```python
"""Testes de integração do endpoint GET /abordagens/.

Cobre o filtro por data e o comportamento padrão paginado.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario


class TestListarAbordagensAPI:
    """Testes do endpoint GET /abordagens/."""

    async def test_listar_sem_filtro_data_retorna_paginado(
        self,
        client: AsyncClient,
        auth_headers: dict,
        abordagem: Abordagem,
    ):
        """Sem ?data, retorna lista paginada normal.

        Args:
            client: Cliente HTTP de testes.
            auth_headers: Headers com JWT do usuário de teste.
            abordagem: Fixture de abordagem.
        """
        resp = await client.get("/api/v1/abordagens/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_listar_com_filtro_data_retorna_do_dia(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        guarnicao: Guarnicao,
        usuario: Usuario,
    ):
        """Com ?data=HOJE, retorna abordagens do dia.

        Args:
            client: Cliente HTTP de testes.
            auth_headers: Headers com JWT do usuário de teste.
            db_session: Sessão do banco de testes.
            guarnicao: Fixture de guarnição.
            usuario: Fixture de usuário.
        """
        hoje = datetime.now(UTC)
        a = Abordagem(
            data_hora=datetime(hoje.year, hoje.month, hoje.day, 9, 0, tzinfo=UTC),
            endereco_texto="Rua do Dia, 10",
            usuario_id=usuario.id,
            guarnicao_id=guarnicao.id,
        )
        db_session.add(a)
        await db_session.commit()

        data_str = hoje.strftime("%Y-%m-%d")
        resp = await client.get(
            f"/api/v1/abordagens/?data={data_str}", headers=auth_headers
        )
        assert resp.status_code == 200
        result = resp.json()
        assert isinstance(result, list)
        assert any(r["endereco_texto"] == "Rua do Dia, 10" for r in result)

    async def test_listar_com_data_invalida_retorna_422(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """?data com formato inválido retorna 422.

        Args:
            client: Cliente HTTP de testes.
            auth_headers: Headers com JWT do usuário de teste.
        """
        resp = await client.get(
            "/api/v1/abordagens/?data=nao-e-data", headers=auth_headers
        )
        assert resp.status_code == 422
```

**Step 2: Rodar e verificar que falha**

```bash
pytest tests/integration/test_abordagens_api.py -v
```

Esperado: `FAILED` — `422` no teste `test_listar_com_filtro_data_retorna_do_dia` (parâmetro `data` não existe ainda)

**Step 3: Implementar no router**

Em `app/api/v1/abordagens.py`, adicionar imports:

```python
from datetime import date
```

Modificar a função `listar_abordagens` (linha 83), adicionando o parâmetro `data` e o branch condicional:

```python
@router.get("/", response_model=list[AbordagemDetail])
@limiter.limit("30/minute")
async def listar_abordagens(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    data: date | None = Query(None, description="Filtrar por data (YYYY-MM-DD). Ignora skip/limit."),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[AbordagemDetail]:
    """Lista abordagens da guarnição com paginação ou filtro por data.

    Quando `data` é informado, retorna todas as abordagens do dia sem
    paginação. Sem `data`, retorna lista paginada (comportamento padrão).

    Args:
        request: Objeto Request do FastAPI.
        skip: Registros a pular (ignorado se `data` informado).
        limit: Máximo de resultados (ignorado se `data` informado).
        data: Data para filtrar abordagens (YYYY-MM-DD), opcional.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de AbordagemDetail ordenada por data/hora decrescente.

    Status Code:
        200: Lista retornada.
        403: Usuário sem guarnição.
        422: Formato de data inválido.
        429: Rate limit (30/min).
    """
    if user.guarnicao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem guarnição atribuída",
        )
    service = AbordagemService(db)
    if data is not None:
        abordagens = await service.listar_por_data(
            guarnicao_id=user.guarnicao_id,
            data=data,
        )
    else:
        abordagens = await service.listar(
            guarnicao_id=user.guarnicao_id,
            skip=skip,
            limit=limit,
        )
    return [_serializar_detalhe(a) for a in abordagens]
```

**Step 4: Rodar e verificar que passa**

```bash
pytest tests/integration/test_abordagens_api.py -v
```

Esperado: `PASSED` (3 testes)

**Step 5: Rodar todos os testes para garantir sem regressão**

```bash
pytest tests/ -v --tb=short
```

Esperado: todos passando.

**Step 6: Commit**

```bash
git add app/api/v1/abordagens.py tests/integration/test_abordagens_api.py
git commit -m "feat(abordagens): adicionar parâmetro ?data no endpoint GET /abordagens/"
```

---

### Task 3: Frontend — calendário em `ocorrencias.js`

**Files:**
- Modify: `frontend/js/pages/ocorrencias.js`

**Step 1: Substituir `renderOcorrencias()` — adicionar calendário no HTML**

Substituir o conteúdo HTML da função `renderOcorrencias()` pelo bloco abaixo.
O calendário é idêntico ao de `dashboard.js` (linhas 166–215). A busca permanece no topo. Os cards de abordagem ficam abaixo do calendário.

```javascript
function renderOcorrencias() {
  return `
    <div x-data="ocorrenciasPage()" x-init="init()" style="display:flex;flex-direction:column;gap:16px;">

      <!-- Header -->
      <div>
        <h2 style="font-family:var(--font-display);font-size:18px;font-weight:700;color:var(--color-text);text-transform:uppercase;letter-spacing:0.1em;margin:0;">
          RELATÓRIO DE ABORDAGENS
        </h2>
        <p style="font-family:var(--font-data);font-size:12px;color:var(--color-text-dim);text-transform:uppercase;letter-spacing:0.15em;margin-top:4px;"
           x-text="loading ? 'CARREGANDO...' : total + ' ABORDAGENS'">
        </p>
      </div>

      <!-- Busca local -->
      <div style="display:flex;align-items:center;gap:8px;background:var(--color-surface);border:1px solid var(--color-border);border-radius:4px;padding:8px 12px;">
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-text-dim);flex-shrink:0;">
          <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
        </svg>
        <input type="search" x-model="filtro" placeholder="Buscar por nome, placa, endereço..."
          style="background:none;border:none;outline:none;color:var(--color-text);font-family:var(--font-data);font-size:13px;width:100%;">
      </div>

      <!-- Calendário -->
      <div class="glass-card" style="padding:16px;border-radius:4px;">
        <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin-bottom:12px;">
          Abordagens por Dia
        </h3>

        <!-- Navegação do mês -->
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <button @click="mesMenos()"
                  style="color:var(--color-text-muted);background:transparent;border:1px solid var(--color-border);border-radius:4px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 150ms;"
                  onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.color='var(--color-primary)'"
                  onmouseout="this.style.borderColor='var(--color-border)';this.style.color='var(--color-text-muted)'"
          >&#8249;</button>
          <span style="font-family:var(--font-data);font-size:14px;font-weight:600;color:var(--color-text);" x-text="mesAtualLabel"></span>
          <button @click="mesMais()"
                  style="color:var(--color-text-muted);background:transparent;border:1px solid var(--color-border);border-radius:4px;width:28px;height:28px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 150ms;"
                  onmouseover="this.style.borderColor='rgba(0,212,255,0.3)';this.style.color='var(--color-primary)'"
                  onmouseout="this.style.borderColor='var(--color-border)';this.style.color='var(--color-text-muted)'"
          >&#8250;</button>
        </div>

        <!-- Header dias da semana -->
        <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;margin-bottom:2px;">
          <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">D</span>
          <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">S</span>
          <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">T</span>
          <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">Q</span>
          <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">Q</span>
          <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">S</span>
          <span style="font-family:var(--font-data);font-size:10px;color:var(--color-text-dim);font-weight:600;text-transform:uppercase;">S</span>
        </div>

        <!-- Grid de dias -->
        <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;text-align:center;">
          <template x-for="v in primeiroDiaSemana" :key="'v' + v">
            <div></div>
          </template>
          <template x-for="dia in diasDoMes" :key="dia">
            <button
              class="cal-day"
              :class="{
                'is-selecionado': isDiaSelecionado(dia),
                'is-hoje': diaEHoje(dia)
              }"
              @click="selecionarDia(dia)">
              <span class="cal-day-num" x-text="dia"></span>
              <span class="cal-led" x-show="diaTemAbordagem(dia)"></span>
            </button>
          </template>
        </div>
      </div>

      <!-- Loading -->
      <div x-show="loading" style="text-align:center;padding:32px 0;">
        <div style="width:24px;height:24px;border:2px solid var(--color-border);border-top-color:var(--color-primary);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto;"></div>
      </div>

      <!-- Erro -->
      <div x-show="!loading && erro" class="glass-card" style="padding:16px;text-align:center;">
        <p style="font-family:var(--font-data);font-size:13px;color:var(--color-danger);" x-text="erro"></p>
        <button @click="selecionarDia(diaSelecionado)" class="btn btn-secondary" style="margin-top:8px;width:auto;padding:6px 16px;">Tentar novamente</button>
      </div>

      <!-- Vazio -->
      <div x-show="!loading && !erro && diaSelecionado && abordagensFiltradas.length === 0"
           style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-align:center;padding:16px 0;text-transform:uppercase;letter-spacing:0.08em;">
        <span x-show="filtro">Nenhum resultado para "<span x-text="filtro"></span>"</span>
        <span x-show="!filtro">Nenhuma abordagem neste dia.</span>
      </div>

      <!-- Lista de abordagens do dia -->
      <template x-for="ab in abordagensFiltradas" :key="ab.id">
        <div class="glass-card" :class="ab.ocorrencias && ab.ocorrencias.length ? 'card-led-blue' : ''"
             style="padding:12px;cursor:pointer;border-radius:4px;"
             @click="abrirDetalhe(ab.id)">

          <!-- Row principal -->
          <div style="display:flex;align-items:center;gap:10px;">
            <!-- Avatares -->
            <div style="display:flex;">
              <template x-for="(p, i) in ab.pessoas.slice(0, 3)" :key="p.id">
                <div :style="'width:36px;height:36px;border-radius:4px;border:1px solid rgba(0,212,255,0.2);background:var(--color-surface-hover);display:flex;align-items:center;justify-content:center;font-family:var(--font-display);font-size:11px;font-weight:700;color:var(--color-primary);flex-shrink:0;' + (i > 0 ? 'margin-left:-8px;' : '') + (p.foto_principal_url ? 'padding:0;overflow:hidden;' : '')">
                  <template x-if="p.foto_principal_url">
                    <img :src="p.foto_principal_url" style="width:100%;height:100%;object-fit:cover;" loading="lazy">
                  </template>
                  <template x-if="!p.foto_principal_url">
                    <span x-text="iniciais(p.nome)"></span>
                  </template>
                </div>
              </template>
              <template x-if="ab.pessoas.length === 0">
                <div style="width:36px;height:36px;border-radius:4px;border:1px dashed var(--color-border);display:flex;align-items:center;justify-content:center;">
                  <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" style="color:var(--color-text-dim);"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                </div>
              </template>
            </div>

            <!-- Info -->
            <div style="flex:1;min-width:0;">
              <div style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);letter-spacing:0.08em;"
                   x-text="formatarDataHora(ab.data_hora)"></div>
              <div style="font-family:var(--font-data);font-size:13px;font-weight:600;color:var(--color-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                   x-text="nomesPessoas(ab.pessoas) || 'Sem abordados registrados'"></div>
              <div style="font-family:var(--font-data);font-size:11px;color:var(--color-text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                   x-text="ab.endereco_texto || 'Endereço não disponível'"></div>
            </div>
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--color-text-dim);flex-shrink:0;"><path d="M9 18l6-6-6-6"/></svg>
          </div>

          <!-- Footer badges -->
          <div style="display:flex;align-items:center;gap:6px;margin-top:8px;flex-wrap:wrap;">
            <span style="font-family:var(--font-data);font-size:9px;padding:2px 6px;border-radius:2px;background:rgba(0,212,255,0.06);color:var(--color-text-dim);border:1px solid var(--color-border);"
                  x-text="'#' + ab.id"></span>
            <template x-if="ab.ocorrencias && ab.ocorrencias.length > 0">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(0,255,136,0.1);color:var(--color-success);border:1px solid rgba(0,255,136,0.25);">RAP vinculada</span>
            </template>
            <template x-if="!ab.ocorrencias || !ab.ocorrencias.length">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(255,107,0,0.1);color:var(--color-danger);border:1px solid rgba(255,107,0,0.25);">Sem RAP</span>
            </template>
            <template x-if="midias(ab.fotos) > 0">
              <span style="font-family:var(--font-display);font-size:9px;padding:2px 8px;border-radius:2px;text-transform:uppercase;letter-spacing:0.08em;background:rgba(0,212,255,0.08);color:var(--color-primary);border:1px solid rgba(0,212,255,0.2);"
                    x-text="midias(ab.fotos) + ' mídia' + (midias(ab.fotos) > 1 ? 's' : '')"></span>
            </template>
            <template x-if="ab.veiculos && ab.veiculos.length > 0">
              <span style="margin-left:auto;font-family:var(--font-display);font-size:9px;color:var(--color-text-dim);background:var(--color-surface);border:1px solid var(--color-border);border-radius:2px;padding:1px 5px;"
                    x-text="ab.veiculos.length + ' veículo' + (ab.veiculos.length > 1 ? 's' : '')"></span>
            </template>
          </div>
        </div>
      </template>

    </div>
  `;
}
```

**Step 2: Substituir `ocorrenciasPage()` — novo estado Alpine com calendário**

Substituir a função `ocorrenciasPage()` inteira pelo bloco abaixo:

```javascript
function ocorrenciasPage() {
  const agora = new Date();
  return {
    abordagens: [],
    filtro: '',
    loading: false,
    erro: null,

    // Calendário
    anoCalendarioAtual: agora.getFullYear(),
    mesCalendarioAtual: agora.getMonth() + 1,
    anoHoje: agora.getFullYear(),
    mesHoje: agora.getMonth() + 1,
    diaHoje: agora.getDate(),
    diaSelecionado: agora.getDate(),
    _anoSelec: agora.getFullYear(),
    _mesSelec: agora.getMonth() + 1,
    diasComAbordagem: [],

    get total() {
      return this.abordagens.length;
    },

    get mesAtualLabel() {
      const meses = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                     'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
      return `${meses[this.mesCalendarioAtual - 1]} ${this.anoCalendarioAtual}`;
    },

    get primeiroDiaSemana() {
      const d = new Date(this.anoCalendarioAtual, this.mesCalendarioAtual - 1, 1);
      return Array.from({ length: d.getDay() }, (_, i) => i);
    },

    get diasDoMes() {
      const total = new Date(this.anoCalendarioAtual, this.mesCalendarioAtual, 0).getDate();
      return Array.from({ length: total }, (_, i) => i + 1);
    },

    get abordagensFiltradas() {
      if (!this.filtro.trim()) return this.abordagens;
      const q = this.filtro.toLowerCase();
      return this.abordagens.filter(ab => {
        const nomes = (ab.pessoas || []).map(p => p.nome.toLowerCase()).join(' ');
        const placas = (ab.veiculos || []).map(v => v.placa.toLowerCase()).join(' ');
        const end = (ab.endereco_texto || '').toLowerCase();
        return nomes.includes(q) || placas.includes(q) || end.includes(q);
      });
    },

    diaTemAbordagem(dia) {
      return this.diasComAbordagem.includes(dia);
    },

    isDiaSelecionado(dia) {
      return (
        this.diaSelecionado === dia &&
        this._mesSelec === this.mesCalendarioAtual &&
        this._anoSelec === this.anoCalendarioAtual
      );
    },

    diaEHoje(dia) {
      return (
        dia === this.diaHoje &&
        this.mesCalendarioAtual === this.mesHoje &&
        this.anoCalendarioAtual === this.anoHoje
      );
    },

    async init() {
      const dataHoje = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(this.diaHoje).padStart(2,'0')}`;
      await Promise.all([
        this.carregarDiasComAbordagem(),
        this.carregarAbordagensDoDia(dataHoje),
      ]);
    },

    async mesMenos() {
      if (this.mesCalendarioAtual === 1) {
        this.mesCalendarioAtual = 12;
        this.anoCalendarioAtual--;
      } else {
        this.mesCalendarioAtual--;
      }
      this.diaSelecionado = null;
      this.abordagens = [];
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
      this.abordagens = [];
      await this.carregarDiasComAbordagem();
    },

    async selecionarDia(dia) {
      this.diaSelecionado = dia;
      this._mesSelec = this.mesCalendarioAtual;
      this._anoSelec = this.anoCalendarioAtual;
      const dataStr = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
      await this.carregarAbordagensDoDia(dataStr);
    },

    async carregarDiasComAbordagem() {
      const mes = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}`;
      this.diasComAbordagem = await api.get(`/analytics/dias-com-abordagem?mes=${mes}`).catch(() => []);
    },

    async carregarAbordagensDoDia(dataStr) {
      this.loading = true;
      this.erro = null;
      try {
        this.abordagens = await api.get(`/abordagens/?data=${dataStr}`);
      } catch (e) {
        this.erro = 'Erro ao carregar abordagens. Tente novamente.';
      } finally {
        this.loading = false;
      }
    },

    abrirDetalhe(id) {
      const appEl = document.querySelector('[x-data]');
      if (appEl && appEl._x_dataStack) {
        appEl._x_dataStack[0]._abordagemId = id;
        appEl._x_dataStack[0].navigate('abordagem-detalhe');
      }
    },

    iniciais(nome) {
      return nome.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
    },

    nomesPessoas(pessoas) {
      if (!pessoas || !pessoas.length) return '';
      const nomes = pessoas.slice(0, 2).map(p => p.nome.split(' ')[0].toUpperCase());
      const extra = pessoas.length > 2 ? ` +${pessoas.length - 2}` : '';
      return nomes.join(' · ') + extra;
    },

    midias(fotos) {
      return (fotos || []).filter(f => f.tipo === 'midia_abordagem').length;
    },

    formatarDataHora(dt) {
      const d = new Date(dt);
      return d.toLocaleDateString('pt-BR') + ' · ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    },
  };
}
```

**Step 3: Verificar lint do projeto**

```bash
make lint
```

Esperado: sem erros (mudanças são só JS/frontend, ruff não analisa JS).

**Step 4: Rodar todos os testes**

```bash
make test
```

Esperado: todos passando.

**Step 5: Commit**

```bash
git add frontend/js/pages/ocorrencias.js
git commit -m "feat(frontend): substituir lista plana por calendário na página de relatórios"
```

---

### Task 4: Verificação final

**Step 1: Subir o ambiente**

```bash
make dev
```

**Step 2: Abrir o app no browser e navegar para Relatórios**

- Verificar que o calendário aparece com o mês atual
- Verificar que hoje está selecionado (highlight teal)
- Verificar que dias com abordagem têm o dot azul
- Clicar em dias diferentes e confirmar que a lista atualiza
- Verificar que a busca filtra dentro do dia selecionado
- Trocar de mês com ← → e confirmar que os dots atualizam

**Step 3: Commit final se necessário**

```bash
git add -p
git commit -m "fix(frontend): ajustes visuais relatórios calendário"
```
