# Consulta: Busca por Foto, Layout e Resultado por Veículo — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar busca por foto na página de consulta, reformular o layout dos cards de endereço e veículo, e fazer a busca por veículo retornar fichas de pessoas (não cards de carro).

**Architecture:** 1 novo endpoint de backend (`GET /consultas/pessoas-por-veiculo`), ajuste no `BuscaRostoItem` para incluir dados da pessoa, nova query de repositório via join `AbordagemVeiculo → AbordagemPessoa → Pessoa`, e reescrita do `consulta.js`.

**Tech Stack:** Python/FastAPI/SQLAlchemy async, Alpine.js, Tailwind CSS.

---

## Task 1: Atualizar schema `BuscaRostoItem`

**Files:**
- Modify: `app/schemas/foto.py:76-91`

### Step 1: Adicionar campos opcionais de pessoa ao `BuscaRostoItem`

Abrir `app/schemas/foto.py`. Substituir a classe `BuscaRostoItem`:

```python
class BuscaRostoItem(BaseModel):
    """Item de resultado da busca por similaridade facial.

    Attributes:
        foto_id: ID da foto encontrada no banco.
        arquivo_url: URL da imagem no storage (R2/S3).
        pessoa_id: ID da pessoa associada à foto.
        similaridade: Grau de similaridade (0 a 1, cosseno).
        nome: Nome completo da pessoa (preenchido quando disponível).
        cpf_masked: CPF mascarado da pessoa (preenchido quando disponível).
        apelido: Apelido da pessoa (preenchido quando disponível).
        foto_principal_url: URL da foto de perfil da pessoa.
    """

    foto_id: int
    arquivo_url: str
    pessoa_id: int | None = None
    similaridade: float
    nome: str | None = None
    cpf_masked: str | None = None
    apelido: str | None = None
    foto_principal_url: str | None = None

    model_config = {"from_attributes": True}
```

### Step 2: Commit

```bash
git add app/schemas/foto.py
git commit -m "feat(schemas): adicionar dados de pessoa ao BuscaRostoItem"
```

---

## Task 2: Adicionar schemas de veículo vinculado à consulta

**Files:**
- Modify: `app/schemas/consulta.py`

### Step 1: Adicionar `VeiculoInfo` e `PessoaComVeiculoRead`

Abrir `app/schemas/consulta.py`. Adicionar ao final do arquivo:

```python
class VeiculoInfo(BaseModel):
    """Dados resumidos do veículo que originou o vínculo.

    Attributes:
        placa: Placa do veículo (uppercase normalizado).
        modelo: Modelo do veículo (opcional).
        cor: Cor do veículo (opcional).
        ano: Ano do veículo (opcional).
    """

    placa: str
    modelo: str | None = None
    cor: str | None = None
    ano: int | None = None

    model_config = {"from_attributes": True}


class PessoaComVeiculoRead(PessoaRead):
    """Pessoa retornada por busca de veículo com dados do vínculo.

    Estende PessoaRead com o veículo que gerou o match na busca,
    para exibir "Vinculado via: ABC·1234 · Gol Branco 2020" na ficha.

    Attributes:
        veiculo_info: Dados do veículo vinculado que originou o resultado.
    """

    veiculo_info: VeiculoInfo | None = None
```

### Step 2: Commit

```bash
git add app/schemas/consulta.py
git commit -m "feat(schemas): adicionar VeiculoInfo e PessoaComVeiculoRead"
```

---

## Task 3: Atualizar `FotoService.buscar_por_rosto` para incluir dados de pessoa

**Files:**
- Modify: `app/services/foto_service.py`

### Step 1: Atualizar imports no topo do arquivo

No topo de `app/services/foto_service.py`, adicionar import de `Pessoa` e `PessoaService` (para mask_cpf):

```python
from sqlalchemy import select

from app.models.pessoa import Pessoa
from app.services.pessoa_service import PessoaService
```

Atenção: esses imports devem ficar junto aos imports existentes, não duplicar os que já existem.

### Step 2: Substituir o método `buscar_por_rosto`

Localizar o método `buscar_por_rosto` (linha ~160) e substituir por:

```python
async def buscar_por_rosto(
    self,
    image_bytes: bytes,
    face_service: "FaceService",
    top_k: int = 5,
) -> list[dict]:
    """Busca pessoas por similaridade facial via pgvector.

    Extrai embedding facial da imagem enviada e busca fotos com
    rostos similares no banco via distância cosseno (512-dim).
    Enriquece cada resultado com dados básicos da pessoa vinculada
    (nome, cpf_masked, apelido, foto_principal_url).

    Args:
        image_bytes: Imagem com rosto para busca em bytes.
        face_service: Serviço InsightFace para extração de embedding.
        top_k: Número máximo de resultados.

    Returns:
        Lista de dicionários com foto, pessoa, pessoa_id e similaridade.
        Lista vazia se nenhum rosto detectado na imagem.
    """
    embedding = face_service.extrair_embedding(image_bytes)
    if embedding is None:
        return []

    results = await self.repo.buscar_por_similaridade_facial(embedding, top_k=top_k)

    # Carregar pessoas vinculadas às fotos em um único SELECT
    pessoa_ids = [row[0].pessoa_id for row in results if row[0].pessoa_id]
    pessoas_map: dict[int, Pessoa] = {}
    if pessoa_ids:
        stmt = select(Pessoa).where(Pessoa.id.in_(pessoa_ids))
        res = await self.db.execute(stmt)
        for p in res.scalars().all():
            pessoas_map[p.id] = p

    return [
        {
            "foto": row[0],
            "similaridade": round(float(row[1]), 4),
            "pessoa": pessoas_map.get(row[0].pessoa_id) if row[0].pessoa_id else None,
        }
        for row in results
    ]
```

### Step 3: Atualizar o router `fotos.py` para usar os novos campos

Em `app/api/v1/fotos.py`, localizar o bloco de montagem de `items` (linha ~202) e substituir por:

```python
items = [
    BuscaRostoItem(
        foto_id=r["foto"].id,
        arquivo_url=r["foto"].arquivo_url,
        pessoa_id=r["foto"].pessoa_id,
        similaridade=r["similaridade"],
        nome=r["pessoa"].nome if r["pessoa"] else None,
        cpf_masked=PessoaService.mask_cpf(r["pessoa"]) if r["pessoa"] and r["pessoa"].cpf_encrypted else None,
        apelido=r["pessoa"].apelido if r["pessoa"] else None,
        foto_principal_url=r["pessoa"].foto_principal_url if r["pessoa"] else None,
    )
    for r in results
]
```

Também é necessário importar `PessoaService` no topo de `app/api/v1/fotos.py`:

```python
from app.services.pessoa_service import PessoaService
```

### Step 4: Commit

```bash
git add app/services/foto_service.py app/api/v1/fotos.py
git commit -m "feat(fotos): enriquecer BuscaRostoItem com dados da pessoa vinculada"
```

---

## Task 4: Novo método de repositório — pessoas por veículo

**Files:**
- Modify: `app/repositories/veiculo_repo.py`

### Step 1: Adicionar imports necessários

No topo de `app/repositories/veiculo_repo.py`, adicionar:

```python
from app.models.abordagem import AbordagemPessoa, AbordagemVeiculo
from app.models.pessoa import Pessoa
```

### Step 2: Adicionar método `get_pessoas_por_veiculo`

Ao final da classe `VeiculoRepository`, adicionar:

```python
async def get_pessoas_por_veiculo(
    self,
    placa: str | None,
    modelo: str | None,
    cor: str | None,
    guarnicao_id: int | None,
    skip: int = 0,
    limit: int = 20,
) -> list[tuple]:
    """Busca pessoas vinculadas a veículos via abordagens.

    Resolve a cadeia Veiculo → AbordagemVeiculo → AbordagemPessoa → Pessoa
    para encontrar todos os abordados que tiveram relação com o veículo
    buscado. Deduplicação é feita via DISTINCT na query.

    Args:
        placa: Placa parcial para busca ILIKE (opcional).
        modelo: Modelo parcial para busca ILIKE (opcional).
        cor: Cor parcial para busca ILIKE (opcional).
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        skip: Número de registros a pular.
        limit: Número máximo de resultados.

    Returns:
        Lista de tuplas (Pessoa, Veiculo) sem duplicatas.
    """
    query = (
        select(Pessoa, Veiculo)
        .join(AbordagemPessoa, AbordagemPessoa.pessoa_id == Pessoa.id)
        .join(AbordagemVeiculo, AbordagemVeiculo.abordagem_id == AbordagemPessoa.abordagem_id)
        .join(Veiculo, Veiculo.id == AbordagemVeiculo.veiculo_id)
        .where(
            Pessoa.ativo == True,  # noqa: E712
            Veiculo.ativo == True,  # noqa: E712
        )
    )

    if placa:
        normalized = placa.upper().replace("-", "").replace(" ", "")
        query = query.where(Veiculo.placa.ilike(f"%{normalized}%"))
    if modelo:
        query = query.where(Veiculo.modelo.ilike(f"%{modelo}%"))
    if cor:
        query = query.where(Veiculo.cor.ilike(f"%{cor}%"))
    if guarnicao_id is not None:
        query = query.where(Pessoa.guarnicao_id == guarnicao_id)

    query = query.distinct().offset(skip).limit(limit)
    result = await self.db.execute(query)
    return list(result.all())
```

### Step 3: Commit

```bash
git add app/repositories/veiculo_repo.py
git commit -m "feat(repo): adicionar get_pessoas_por_veiculo com join via abordagens"
```

---

## Task 5: Novo método de serviço — `pessoas_por_veiculo`

**Files:**
- Modify: `app/services/consulta_service.py`

### Step 1: Adicionar método ao `ConsultaService`

Ao final da classe `ConsultaService`, adicionar:

```python
async def pessoas_por_veiculo(
    self,
    placa: str | None,
    modelo: str | None,
    cor: str | None,
    skip: int,
    limit: int,
    user: Usuario | None,
) -> list[dict]:
    """Busca pessoas vinculadas a veículos por placa, modelo ou cor.

    Delega para o repositório e retorna dicionários com pessoa e veiculo_info
    para o router montar o schema de resposta.

    Args:
        placa: Placa parcial (opcional).
        modelo: Modelo do veículo (opcional).
        cor: Cor do veículo (opcional, usada junto com modelo).
        skip: Registros a pular (paginação).
        limit: Máximo de resultados.
        user: Usuário autenticado para filtro multi-tenant.

    Returns:
        Lista de dicionários com "pessoa" (Pessoa) e "veiculo" (Veiculo).
    """
    guarnicao_id = user.guarnicao_id if user else None
    rows = await self.veiculo_repo.get_pessoas_por_veiculo(
        placa=placa,
        modelo=modelo,
        cor=cor,
        guarnicao_id=guarnicao_id,
        skip=skip,
        limit=limit,
    )
    return [{"pessoa": row[0], "veiculo": row[1]} for row in rows]
```

### Step 2: Commit

```bash
git add app/services/consulta_service.py
git commit -m "feat(service): adicionar pessoas_por_veiculo ao ConsultaService"
```

---

## Task 6: Novo endpoint `GET /consultas/pessoas-por-veiculo`

**Files:**
- Modify: `app/api/v1/consultas.py`

### Step 1: Adicionar imports necessários

No topo de `app/api/v1/consultas.py`, adicionar ao bloco de imports de schemas:

```python
from app.schemas.consulta import (
    ConsultaUnificadaResponse,
    PessoaComEnderecoRead,
    PessoaComVeiculoRead,
    VeiculoInfo,
)
```

(substituir a linha de import existente de `app.schemas.consulta`)

### Step 2: Adicionar endpoint ao final do arquivo

```python
@router.get("/pessoas-por-veiculo", response_model=list[PessoaComVeiculoRead])
async def pessoas_por_veiculo(
    placa: str | None = Query(None, max_length=20, description="Placa parcial (ILIKE)"),
    modelo: str | None = Query(None, max_length=100, description="Modelo do veículo"),
    cor: str | None = Query(None, max_length=50, description="Cor do veículo (opcional)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[PessoaComVeiculoRead]:
    """Retorna fichas de abordados vinculados a um veículo.

    Resolve Veiculo → AbordagemVeiculo → AbordagemPessoa → Pessoa
    para encontrar todos os abordados que tiveram relação com o veículo
    buscado. Pelo menos um parâmetro (placa ou modelo) deve ser informado.

    Args:
        placa: Placa parcial para busca (opcional).
        modelo: Modelo do veículo para busca (opcional).
        cor: Cor do veículo — usada como filtro adicional ao modelo (opcional).
        skip: Registros a pular (paginação).
        limit: Máximo de resultados por página (1-100, padrão 20).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de PessoaComVeiculoRead com dados do abordado e do veículo vinculado.

    Raises:
        HTTPException 400: Se nenhum parâmetro de busca for informado.
    """
    from fastapi import HTTPException as _HTTPException

    if not placa and not modelo:
        raise _HTTPException(status_code=400, detail="Informe placa ou modelo para buscar.")

    service = ConsultaService(db)
    rows = await service.pessoas_por_veiculo(
        placa=placa,
        modelo=modelo,
        cor=cor,
        skip=skip,
        limit=limit,
        user=user,
    )

    return [
        PessoaComVeiculoRead(
            id=row["pessoa"].id,
            nome=row["pessoa"].nome,
            cpf_masked=PessoaService.mask_cpf(row["pessoa"]) if row["pessoa"].cpf_encrypted else None,
            data_nascimento=row["pessoa"].data_nascimento,
            apelido=row["pessoa"].apelido,
            foto_principal_url=row["pessoa"].foto_principal_url,
            observacoes=row["pessoa"].observacoes,
            guarnicao_id=row["pessoa"].guarnicao_id,
            criado_em=row["pessoa"].criado_em,
            atualizado_em=row["pessoa"].atualizado_em,
            veiculo_info=VeiculoInfo(
                placa=row["veiculo"].placa,
                modelo=row["veiculo"].modelo,
                cor=row["veiculo"].cor,
                ano=row["veiculo"].ano,
            ),
        )
        for row in rows
    ]
```

Também importar `HTTPException` e `PessoaService` no topo se ainda não estiverem:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.pessoa_service import PessoaService
```

### Step 3: Commit

```bash
git add app/api/v1/consultas.py
git commit -m "feat(api): endpoint GET /consultas/pessoas-por-veiculo"
```

---

## Task 7: Reescrever `consulta.js` — layout + foto + veiculo→pessoa

**Files:**
- Modify: `frontend/js/pages/consulta.js`

Esta é a maior tarefa. Substituir completamente o conteúdo do arquivo.

### Step 1: Substituir `renderConsulta()`

```javascript
/**
 * Página de consulta unificada — Argus AI.
 *
 * Seções independentes: busca de pessoa (nome/CPF ou foto),
 * filtros por endereço e busca por veículo. Cada seção retorna
 * a ficha do abordado como resultado.
 */
function renderConsulta() {
  return `
    <div x-data="consultaPage()" x-init="init()" class="space-y-4">
      <h2 class="text-lg font-bold text-slate-100">Consulta</h2>

      <!-- ── Pessoa ─────────────────────────────────────────── -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Pessoa</p>
        <p class="text-xs text-slate-500">Busque por nome, CPF ou envie uma foto para comparação facial.</p>

        <!-- Campo texto + clipe -->
        <div class="relative flex items-center gap-2">
          <div class="relative flex-1">
            <input type="text" x-model="query" @input="onInput()"
                   placeholder="Nome completo ou CPF..."
                   class="w-full pl-12 py-3 text-base">
            <svg class="absolute left-3.5 top-3.5 w-5 h-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
            </svg>
          </div>
          <!-- Botão de foto -->
          <button @click="$refs.fotoInput.click()" title="Buscar por foto"
                  class="p-3 rounded-lg border border-slate-600 hover:border-blue-500 transition-colors"
                  :class="fotoFile ? 'border-blue-500 bg-blue-500/10' : ''">
            <svg class="w-5 h-5 text-slate-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"/>
            </svg>
          </button>
          <input type="file" x-ref="fotoInput" accept="image/jpeg,image/png,image/webp"
                 class="hidden" @change="onFotoSelect($event)">
        </div>

        <!-- Preview da foto -->
        <div x-show="fotoFile" class="flex items-center gap-3 p-2 bg-slate-800/50 rounded-lg border border-slate-700">
          <img :src="fotoPreviewUrl" class="w-12 h-12 rounded object-cover shrink-0">
          <div class="flex-1 min-w-0">
            <p class="text-xs text-slate-300 truncate" x-text="fotoFile?.name"></p>
            <p class="text-xs text-slate-500">Comparando rosto com o banco...</p>
          </div>
          <button @click="removeFoto()" class="p-1 text-slate-500 hover:text-red-400 transition-colors">
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- Resultados: Pessoas por texto -->
        <div x-show="searched && pessoasTexto.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">Resultados por nome/CPF (<span x-text="pessoasTexto.length"></span>)</p>
          <template x-for="p in pessoasTexto" :key="'t-' + p.id">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                  <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
                  <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Resultados: Pessoas por foto -->
        <div x-show="pessoasFoto.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">Resultados por foto (<span x-text="pessoasFoto.length"></span>)</p>
          <template x-for="r in pessoasFoto" :key="'f-' + r.foto_id">
            <div @click="r.pessoa_id && viewPessoa(r.pessoa_id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3 flex-1 min-w-0">
                  <img x-show="r.foto_principal_url || r.arquivo_url" :src="r.foto_principal_url || r.arquivo_url"
                       class="w-10 h-10 rounded-full object-cover shrink-0">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-slate-200" x-text="r.nome || 'Pessoa sem nome'"></p>
                    <p x-show="r.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + r.cpf_masked"></p>
                    <p x-show="r.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + r.apelido"></p>
                    <!-- Barra de confiança -->
                    <div class="mt-1.5 flex items-center gap-2">
                      <div class="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all"
                             :style="'width: ' + Math.round(r.similaridade * 100) + '%'"
                             :class="r.similaridade >= 0.8 ? 'bg-green-500' : r.similaridade >= 0.6 ? 'bg-yellow-500' : 'bg-orange-500'">
                        </div>
                      </div>
                      <span class="text-xs font-mono shrink-0"
                            :class="r.similaridade >= 0.8 ? 'text-green-400' : r.similaridade >= 0.6 ? 'text-yellow-400' : 'text-orange-400'"
                            x-text="Math.round(r.similaridade * 100) + '%'">
                      </span>
                    </div>
                  </div>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0 ml-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados pessoa -->
        <p x-show="searched && !loadingPessoa && buscouPessoa && pessoasTexto.length === 0 && pessoasFoto.length === 0"
           class="text-xs text-slate-500 pt-1">
          Nenhuma pessoa encontrada.
        </p>

        <!-- Spinner pessoa -->
        <div x-show="loadingPessoa" class="flex justify-center py-2">
          <span class="spinner"></span>
        </div>
      </div>

      <!-- ── Separador ───────────────────────────────────────── -->
      <div class="flex items-center gap-3">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">Ou</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <!-- ── Filtros por Endereço ───────────────────────────── -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Filtros por Endereço</p>
        <p class="text-xs text-slate-500">Filtre abordados pelo local de residência cadastrado.</p>

        <div class="space-y-3">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Bairro</label>
            <input type="text" list="lista-bairros-c" x-model="filtroBairro" @input="onInputEndereco()"
                   placeholder="Bairro..." class="w-full py-3">
            <p class="text-xs text-slate-600 mt-1">Lista todos os abordados deste bairro</p>
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Cidade</label>
            <input type="text" list="lista-cidades-c" x-model="filtroCidade" @input="onInputEndereco()"
                   placeholder="Cidade..." class="w-full py-3">
            <p class="text-xs text-slate-600 mt-1">Lista todos os abordados desta cidade</p>
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Estado (UF)</label>
            <input type="text" list="lista-estados-c" x-model="filtroEstado" @input="onInputEndereco()"
                   placeholder="DF" maxlength="2" class="w-full py-3 uppercase">
            <p class="text-xs text-slate-600 mt-1">Lista todos os abordados deste estado</p>
          </div>
        </div>

        <datalist id="lista-bairros-c">
          <template x-for="b in localidades.bairros" :key="b"><option :value="b"></option></template>
        </datalist>
        <datalist id="lista-cidades-c">
          <template x-for="c in localidades.cidades" :key="c"><option :value="c"></option></template>
        </datalist>
        <datalist id="lista-estados-c">
          <template x-for="e in localidades.estados" :key="e"><option :value="e"></option></template>
        </datalist>

        <!-- Resultados por endereço -->
        <div x-show="searchedEndereco && pessoasEndereco.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">
            Pessoas neste endereço (<span x-text="pessoasEndereco.length"></span>)
          </p>
          <template x-for="p in pessoasEndereco" :key="'e-' + p.id">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                  <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
                  <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
                  <p x-show="p.endereco_criado_em" class="text-xs text-slate-500"
                     x-text="'Endereço cadastrado em ' + new Date(p.endereco_criado_em).toLocaleDateString('pt-BR')"></p>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados endereço -->
        <p x-show="searchedEndereco && !loadingEndereco && pessoasEndereco.length === 0"
           class="text-xs text-slate-500 pt-1">
          Nenhuma pessoa encontrada neste endereço.
        </p>

        <!-- Spinner endereço -->
        <div x-show="loadingEndereco" class="flex justify-center py-2">
          <span class="spinner"></span>
        </div>
      </div>

      <!-- ── Separador ───────────────────────────────────────── -->
      <div class="flex items-center gap-3">
        <div class="flex-1 h-px bg-slate-700"></div>
        <span class="text-xs font-semibold text-slate-500 uppercase tracking-widest">Ou</span>
        <div class="flex-1 h-px bg-slate-700"></div>
      </div>

      <!-- ── Buscar por Veículo ─────────────────────────────── -->
      <div class="card space-y-3">
        <p class="text-sm font-semibold text-slate-300">Buscar por Veículo</p>
        <p class="text-xs text-slate-500">Encontre o abordado pelo veículo com que foi visto.</p>

        <div class="space-y-3">
          <div>
            <label class="block text-xs text-slate-400 mb-1">Placa</label>
            <input type="text" x-model="filtroPlaca" @input="onInputVeiculo()"
                   placeholder="ABC1234..." maxlength="10"
                   class="w-full py-3 uppercase" style="text-transform:uppercase">
          </div>
          <div>
            <label class="block text-xs text-slate-400 mb-1">Modelo</label>
            <input type="text" x-model="filtroModelo" @input="onInputVeiculo()"
                   placeholder="Modelo do veículo..." class="w-full py-3">
          </div>
          <div x-show="filtroModelo.length > 0">
            <label class="block text-xs text-slate-400 mb-1">Cor <span class="text-slate-600">(opcional)</span></label>
            <input type="text" x-model="filtroCor" @input="onInputVeiculo()"
                   placeholder="Cor do veículo..." class="w-full py-3">
          </div>
        </div>

        <!-- Resultados: fichas de abordados por veículo -->
        <div x-show="searchedVeiculo && pessoasVeiculo.length > 0" class="space-y-2 pt-1">
          <p class="text-xs font-semibold text-slate-500">
            Abordados vinculados (<span x-text="pessoasVeiculo.length"></span>)
          </p>
          <template x-for="p in pessoasVeiculo" :key="'v-' + p.id + '-' + (p.veiculo_info?.placa || '')">
            <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
                  <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
                  <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
                  <p x-show="p.veiculo_info" class="text-xs text-slate-500 mt-0.5"
                     x-text="'Vinculado via: ' + [p.veiculo_info?.placa, p.veiculo_info?.modelo, p.veiculo_info?.cor, p.veiculo_info?.ano].filter(Boolean).join(' · ')">
                  </p>
                </div>
                <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
                </svg>
              </div>
            </div>
          </template>
        </div>

        <!-- Sem resultados veículo -->
        <p x-show="searchedVeiculo && !loadingVeiculo && pessoasVeiculo.length === 0"
           class="text-xs text-slate-500 pt-1">
          Nenhum abordado vinculado a este veículo.
        </p>

        <!-- Spinner veículo -->
        <div x-show="loadingVeiculo" class="flex justify-center py-2">
          <span class="spinner"></span>
        </div>
      </div>
    </div>
  `;
}
```

### Step 2: Substituir `consultaPage()`

```javascript
function consultaPage() {
  return {
    // Estado — busca pessoa
    query: "",
    pessoasTexto: [],
    pessoasFoto: [],
    loadingPessoa: false,
    searched: false,
    buscouPessoa: false,
    _timerPessoa: null,

    // Estado — foto
    fotoFile: null,
    fotoPreviewUrl: "",

    // Estado — endereço
    filtroBairro: "",
    filtroCidade: "",
    filtroEstado: "",
    pessoasEndereco: [],
    loadingEndereco: false,
    searchedEndereco: false,
    _timerEndereco: null,

    // Estado — veículo
    filtroPlaca: "",
    filtroModelo: "",
    filtroCor: "",
    pessoasVeiculo: [],
    loadingVeiculo: false,
    searchedVeiculo: false,
    _timerVeiculo: null,

    // Dados auxiliares
    localidades: { bairros: [], cidades: [], estados: [] },

    // --- lifecycle ---

    async init() {
      try {
        this.localidades = await api.get("/consultas/localidades");
      } catch {
        /* silencioso */
      }
    },

    // --- handlers de input ---

    onInput() {
      clearTimeout(this._timerPessoa);
      if (this.query.length < 2) {
        this.pessoasTexto = [];
        this.searched = false;
        this.buscouPessoa = false;
        return;
      }
      this._timerPessoa = setTimeout(() => this.searchPorTexto(), 400);
    },

    onFotoSelect(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      this.fotoFile = file;
      this.fotoPreviewUrl = URL.createObjectURL(file);
      this.searchPorFoto();
    },

    removeFoto() {
      if (this.fotoPreviewUrl) URL.revokeObjectURL(this.fotoPreviewUrl);
      this.fotoFile = null;
      this.fotoPreviewUrl = "";
      this.pessoasFoto = [];
      this.$refs.fotoInput.value = "";
    },

    onInputEndereco() {
      clearTimeout(this._timerEndereco);
      const temFiltro = this.filtroBairro.length >= 2 || this.filtroCidade.length >= 2 || this.filtroEstado.length >= 1;
      if (!temFiltro) {
        this.pessoasEndereco = [];
        this.searchedEndereco = false;
        return;
      }
      this._timerEndereco = setTimeout(() => this.searchPorEndereco(), 400);
    },

    onInputVeiculo() {
      clearTimeout(this._timerVeiculo);
      const temFiltro = this.filtroPlaca.length >= 2 || this.filtroModelo.length >= 2;
      if (!temFiltro) {
        this.pessoasVeiculo = [];
        this.searchedVeiculo = false;
        return;
      }
      this._timerVeiculo = setTimeout(() => this.searchPorVeiculo(), 400);
    },

    // --- métodos de busca ---

    async searchPorTexto() {
      this.loadingPessoa = true;
      this.buscouPessoa = true;
      try {
        const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa`;
        const r = await api.get(url);
        this.pessoasTexto = r.pessoas || [];
        this.searched = true;
      } catch {
        showToast("Erro na busca por nome/CPF", "error");
      } finally {
        this.loadingPessoa = false;
      }
    },

    async searchPorFoto() {
      if (!this.fotoFile) return;
      this.loadingPessoa = true;
      try {
        const form = new FormData();
        form.append("file", this.fotoFile);
        form.append("top_k", "5");
        const r = await api.postForm("/fotos/buscar-rosto", form);
        this.pessoasFoto = r.resultados || [];
      } catch {
        showToast("Erro na busca por foto", "error");
      } finally {
        this.loadingPessoa = false;
      }
    },

    async searchPorEndereco() {
      this.loadingEndereco = true;
      try {
        let url = `/consultas/?q=a&tipo=pessoa`;
        if (this.filtroBairro.length >= 2) url += `&bairro=${encodeURIComponent(this.filtroBairro)}`;
        if (this.filtroCidade.length >= 2) url += `&cidade=${encodeURIComponent(this.filtroCidade)}`;
        if (this.filtroEstado.length >= 1) url += `&estado=${encodeURIComponent(this.filtroEstado.toUpperCase())}`;
        const r = await api.get(url);
        this.pessoasEndereco = r.pessoas || [];
        this.searchedEndereco = true;
      } catch {
        showToast("Erro no filtro por endereço", "error");
      } finally {
        this.loadingEndereco = false;
      }
    },

    async searchPorVeiculo() {
      this.loadingVeiculo = true;
      try {
        const params = new URLSearchParams();
        if (this.filtroPlaca.length >= 2) params.append("placa", this.filtroPlaca.toUpperCase());
        if (this.filtroModelo.length >= 2) params.append("modelo", this.filtroModelo);
        if (this.filtroCor.length >= 1) params.append("cor", this.filtroCor);
        const r = await api.get(`/consultas/pessoas-por-veiculo?${params}`);
        this.pessoasVeiculo = Array.isArray(r) ? r : [];
        this.searchedVeiculo = true;
      } catch {
        showToast("Erro na busca por veículo", "error");
      } finally {
        this.loadingVeiculo = false;
      }
    },

    viewPessoa(id) {
      const appEl = document.querySelector("[x-data]");
      if (appEl?._x_dataStack) {
        appEl._x_dataStack[0].currentPage = "pessoa-detalhe";
        appEl._x_dataStack[0]._pessoaId = id;
        appEl._x_dataStack[0].renderPage("pessoa-detalhe");
      }
    },
  };
}
```

### Step 3: Verificar se `api.postForm` existe no helper de API

Checar `frontend/js/api.js` ou equivalente. Se não existir método `postForm`, adicionar:

```javascript
postForm(path, formData) {
  return fetch(BASE_URL + path, {
    method: "POST",
    headers: { Authorization: "Bearer " + getToken() },
    body: formData,
  }).then(handleResponse);
},
```

### Step 4: Commit

```bash
git add frontend/js/pages/consulta.js frontend/js/api.js
git commit -m "feat(frontend): consulta com foto, layout empilhado e resultado por veículo"
```

---

## Verificação final

```bash
# Lint e tipos
make lint

# Testes
make test

# Smoke test manual — verificar endpoints novos
# GET /consultas/pessoas-por-veiculo?placa=ABC
# POST /fotos/buscar-rosto (com imagem)
```
