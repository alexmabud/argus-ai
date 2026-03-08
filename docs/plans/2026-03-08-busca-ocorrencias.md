# Busca de Ocorrências por Nome, RAP e Data

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar endpoint `GET /ocorrencias/buscar` e seção de busca na página de upload para encontrar RAPs por nome do abordado, número RAP ou data.

**Architecture:** Novo método `buscar()` no repositório usando ILIKE (beneficia pg_trgm GIN index) sobre `texto_extraido` e `numero_ocorrencia`, com filtro de data em `criado_em`. Service delega ao repo. Endpoint GET com query params opcionais. Frontend adiciona seção de busca abaixo do formulário existente na mesma página.

**Tech Stack:** SQLAlchemy async, FastAPI Query params, Alpine.js, pg_trgm (ILIKE), Tailwind CSS

---

### Task 1: Fixture de Ocorrência no conftest + método `buscar()` no Repo

**Files:**
- Modify: `tests/conftest.py`
- Modify: `app/repositories/ocorrencia_repo.py`
- Create: `tests/integration/test_api_ocorrencias.py`

**Step 1: Adicionar fixture `ocorrencia` no conftest**

Abrir `tests/conftest.py` e adicionar ao final:

```python
@pytest.fixture
async def ocorrencia(db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario, abordagem: Abordagem) -> "Ocorrencia":
    """Fixture que cria uma ocorrência de teste com texto extraído.

    Insere uma ocorrência já processada com texto extraído simulado,
    útil para testes de busca por nome e conteúdo de PDF.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição.
        usuario: Fixture de usuário que cadastrou.
        abordagem: Fixture de abordagem vinculada.

    Returns:
        Ocorrencia: Objeto com texto extraído e processada=True.
    """
    from app.models.ocorrencia import Ocorrencia
    o = Ocorrencia(
        numero_ocorrencia="RAP 2026/000001",
        abordagem_id=abordagem.id,
        arquivo_pdf_url="https://r2.example.com/pdfs/test.pdf",
        texto_extraido="Abordado: Carlos Eduardo Souza, CPF 123.456.789-00. Conduzido à delegacia.",
        processada=True,
        usuario_id=usuario.id,
        guarnicao_id=guarnicao.id,
    )
    db_session.add(o)
    await db_session.flush()
    return o
```

Adicionar o import necessário no topo do conftest (se não tiver):
```python
from app.models.abordagem import Abordagem
```

**Step 2: Escrever testes de integração para o endpoint de busca**

Criar `tests/integration/test_api_ocorrencias.py`:

```python
"""Testes de integração da API de Ocorrências.

Testa endpoints de busca de ocorrências por nome, número RAP e data.
"""

import pytest
from httpx import AsyncClient

from app.models.ocorrencia import Ocorrencia


class TestBuscarOcorrencias:
    """Testes do endpoint GET /api/v1/ocorrencias/buscar."""

    async def test_busca_por_nome_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por nome encontra ocorrência com esse nome no texto.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência com texto contendo "Carlos Eduardo".
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=Carlos Eduardo",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000001"

    async def test_busca_por_rap_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por número RAP parcial retorna a ocorrência correta.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência com número "RAP 2026/000001".
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?rap=2026/000001",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["numero_ocorrencia"] == "RAP 2026/000001"

    async def test_busca_por_data_retorna_ocorrencia(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por data de criação retorna ocorrência correta.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência criada hoje.
        """
        from datetime import date
        hoje = date.today().isoformat()
        response = await client.get(
            f"/api/v1/ocorrencias/buscar?data={hoje}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_busca_sem_filtros_retorna_lista_vazia(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Testa que busca sem filtros e sem dados retorna lista vazia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_busca_nome_inexistente_retorna_vazio(
        self, client: AsyncClient, auth_headers: dict, ocorrencia: Ocorrencia
    ):
        """Testa que busca por nome que não existe retorna lista vazia.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            ocorrencia: Fixture de ocorrência (garante dado no banco).
        """
        response = await client.get(
            "/api/v1/ocorrencias/buscar?nome=NomeQueNaoExiste",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_busca_sem_auth_retorna_403(self, client: AsyncClient):
        """Testa que busca sem autenticação retorna 403.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.get("/api/v1/ocorrencias/buscar?nome=Carlos")
        assert response.status_code == 403
```

**Step 3: Rodar os testes e confirmar que falham**

```bash
pytest tests/integration/test_api_ocorrencias.py -v
```

Esperado: FAIL com `404` ou `AttributeError` (endpoint não existe ainda).

**Step 4: Adicionar método `buscar()` no repositório**

Em `app/repositories/ocorrencia_repo.py`, adicionar após `get_by_numero()`:

```python
async def buscar(
    self,
    guarnicao_id: int,
    nome: str | None = None,
    rap: str | None = None,
    data: "date | None" = None,
    limit: int = 20,
) -> list[Ocorrencia]:
    """Busca ocorrências por nome no texto extraído, número RAP ou data.

    Aplica filtros opcionais combinados com AND. Usa ILIKE para buscas
    parciais case-insensitive, beneficiando índice pg_trgm GIN se existir.
    Busca por nome requer processada=True (texto disponível).

    Args:
        guarnicao_id: ID da guarnição para isolamento multi-tenant.
        nome: Trecho do nome a buscar no texto extraído do PDF.
        rap: Trecho do número RAP para busca parcial.
        data: Data exata de criação da ocorrência.
        limit: Número máximo de resultados (padrão: 20).

    Returns:
        Lista de ocorrências ordenadas por data de criação decrescente.
    """
    from sqlalchemy import func
    query = (
        select(Ocorrencia)
        .where(
            Ocorrencia.guarnicao_id == guarnicao_id,
            Ocorrencia.ativo == True,  # noqa: E712
        )
    )
    if nome:
        query = query.where(
            Ocorrencia.processada == True,  # noqa: E712
            Ocorrencia.texto_extraido.ilike(f"%{nome}%"),
        )
    if rap:
        query = query.where(Ocorrencia.numero_ocorrencia.ilike(f"%{rap}%"))
    if data:
        query = query.where(func.date(Ocorrencia.criado_em) == data)

    query = query.order_by(Ocorrencia.criado_em.desc()).limit(limit)
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

Adicionar o import de `date` no topo do arquivo:
```python
from datetime import date
```

**Step 5: Adicionar método `buscar()` no service**

Em `app/services/ocorrencia_service.py`, adicionar após `listar()`:

```python
async def buscar(
    self,
    guarnicao_id: int,
    nome: str | None = None,
    rap: str | None = None,
    data: "date | None" = None,
) -> list[Ocorrencia]:
    """Busca ocorrências por nome, número RAP ou data de criação.

    Delega ao repositório combinando filtros opcionais com AND.
    Busca por nome opera apenas em ocorrências já processadas pelo worker.

    Args:
        guarnicao_id: ID da guarnição (filtro multi-tenant).
        nome: Trecho do nome a buscar no texto extraído do PDF.
        rap: Trecho do número RAP para busca parcial.
        data: Data exata de criação da ocorrência.

    Returns:
        Lista de ocorrências ordenadas por data de criação decrescente.
    """
    from datetime import date as date_type
    return await self.repo.buscar(
        guarnicao_id=guarnicao_id,
        nome=nome,
        rap=rap,
        data=data,
    )
```

Adicionar o import de `date` no topo do arquivo:
```python
from datetime import date
```

**Step 6: Adicionar endpoint `GET /ocorrencias/buscar` no router**

Em `app/api/v1/ocorrencias.py`, adicionar ANTES do endpoint `/{ocorrencia_id}` (importante: rota estática antes de rota dinâmica):

```python
@router.get("/buscar", response_model=list[OcorrenciaRead])
async def buscar_ocorrencias(
    request: Request,
    nome: str | None = Query(None, description="Nome do abordado no texto do PDF"),
    rap: str | None = Query(None, description="Número RAP (busca parcial)"),
    data: date | None = Query(None, description="Data de criação (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[OcorrenciaRead]:
    """Busca ocorrências por nome no texto extraído, RAP ou data.

    Todos os filtros são opcionais e combinados com AND. Sem filtros,
    retorna lista vazia. Busca por nome opera apenas em ocorrências
    já processadas pelo worker (processada=True).

    Args:
        request: Objeto Request do FastAPI.
        nome: Trecho do nome a buscar no texto extraído do PDF.
        rap: Trecho do número RAP para busca parcial.
        data: Data exata de criação da ocorrência (formato YYYY-MM-DD).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de OcorrenciaRead ordenada por data decrescente.
    """
    if not nome and not rap and not data:
        return []
    service = OcorrenciaService(db)
    ocorrencias = await service.buscar(
        guarnicao_id=user.guarnicao_id,
        nome=nome,
        rap=rap,
        data=data,
    )
    return [OcorrenciaRead.model_validate(o) for o in ocorrencias]
```

Adicionar `date` e `date` no import do topo do arquivo:
```python
from datetime import date
```

**Step 7: Rodar os testes**

```bash
pytest tests/integration/test_api_ocorrencias.py -v
```

Esperado: todos os testes PASS.

**Step 8: Commit**

```bash
git add tests/conftest.py tests/integration/test_api_ocorrencias.py \
        app/repositories/ocorrencia_repo.py \
        app/services/ocorrencia_service.py \
        app/api/v1/ocorrencias.py
git commit -m "feat(ocorrencias): adicionar busca por nome, RAP e data"
```

---

### Task 2: Seção de busca no frontend

**Files:**
- Modify: `frontend/js/pages/ocorrencia-upload.js`

**Step 1: Adicionar seção de busca no template HTML**

Em `frontend/js/pages/ocorrencia-upload.js`, substituir o bloco `<!-- Lista de ocorrências recentes -->` pelo seguinte (manter a lista, adicionar a seção de busca antes dela):

Localizar a linha:
```html
      <!-- Lista de ocorrências recentes -->
```

Adicionar a seção de busca logo antes dessa linha:

```html
      <!-- Busca de ocorrências -->
      <div class="mt-6 card space-y-3">
        <h3 class="text-sm font-semibold text-slate-300">Buscar Ocorrência</h3>

        <div>
          <label class="block text-xs text-slate-400 mb-1">Nome do abordado</label>
          <input type="text" x-model="buscaNome" placeholder="Ex: Carlos Eduardo Souza"
                 class="w-full">
        </div>

        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Número RAP</label>
            <input type="text" x-model="buscaRap" placeholder="Ex: 2026/000123">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Data</label>
            <input type="date" x-model="buscaData">
          </div>
        </div>

        <button @click="buscar()" class="btn btn-primary w-full" :disabled="buscando">
          <span x-show="!buscando">Buscar</span>
          <span x-show="buscando" class="flex items-center justify-center gap-2">
            <span class="spinner"></span> Buscando...
          </span>
        </button>

        <div x-show="resultadosBusca !== null">
          <p x-show="resultadosBusca !== null && resultadosBusca.length === 0"
             class="text-xs text-slate-500 text-center py-2">Nenhuma ocorrência encontrada.</p>
          <div class="space-y-2">
            <template x-for="oc in (resultadosBusca || [])" :key="oc.id">
              <div class="card flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="oc.numero_ocorrencia"></p>
                  <p class="text-xs text-slate-500"
                     x-text="new Date(oc.criado_em).toLocaleDateString('pt-BR')"></p>
                </div>
                <a :href="oc.arquivo_pdf_url" target="_blank" rel="noopener"
                   class="btn btn-secondary text-xs px-3 py-1">Abrir PDF</a>
              </div>
            </template>
          </div>
        </div>
      </div>

```

**Step 2: Adicionar estado e método `buscar()` no Alpine.js**

No objeto retornado por `ocorrenciaUploadPage()`, adicionar as novas propriedades e o método:

Localizar:
```js
    numero: "",
    abordagemId: null,
    file: null,
    submitting: false,
    sucesso: null,
    erro: null,
    ocorrencias: [],
    loadingList: true,
```

Substituir por:
```js
    numero: "",
    abordagemId: null,
    file: null,
    submitting: false,
    sucesso: null,
    erro: null,
    ocorrencias: [],
    loadingList: true,
    buscaNome: "",
    buscaRap: "",
    buscaData: "",
    buscando: false,
    resultadosBusca: null,
```

Adicionar o método `buscar()` após `loadList()`:

```js
    async buscar() {
      if (!this.buscaNome && !this.buscaRap && !this.buscaData) return;
      this.buscando = true;
      try {
        const params = new URLSearchParams();
        if (this.buscaNome) params.append("nome", this.buscaNome);
        if (this.buscaRap) params.append("rap", this.buscaRap);
        if (this.buscaData) params.append("data", this.buscaData);
        this.resultadosBusca = await api.get(`/ocorrencias/buscar?${params}`);
      } catch {
        this.resultadosBusca = [];
      } finally {
        this.buscando = false;
      }
    },
```

**Step 3: Verificar manualmente no browser**

1. Subir o ambiente: `make dev`
2. Navegar até a página de ocorrências
3. Fazer upload de um PDF de teste com texto contendo um nome
4. Aguardar processamento (ou setar `processada=True` diretamente no banco)
5. Buscar pelo nome → deve aparecer o card com botão "Abrir PDF"
6. Testar busca por RAP parcial e por data

**Step 4: Commit**

```bash
git add frontend/js/pages/ocorrencia-upload.js
git commit -m "feat(frontend): adicionar busca de ocorrências por nome, RAP e data"
```

---

## Resumo das alterações

| Arquivo | Tipo | O que muda |
|---|---|---|
| `tests/conftest.py` | Modify | Fixture `ocorrencia` |
| `tests/integration/test_api_ocorrencias.py` | Create | 6 testes de integração |
| `app/repositories/ocorrencia_repo.py` | Modify | Método `buscar()` |
| `app/services/ocorrencia_service.py` | Modify | Método `buscar()` |
| `app/api/v1/ocorrencias.py` | Modify | Endpoint `GET /buscar` |
| `frontend/js/pages/ocorrencia-upload.js` | Modify | Seção de busca + estado Alpine |
