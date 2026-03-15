# Avatares na Busca + Upload de Foto — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir avatares nos resultados de busca (pessoa/endereço/veículo) e ajustar o fluxo de captura de foto por contexto operacional.

**Architecture:** Apenas frontend para Feature 1 (o campo `foto_principal_url` já está nos responses de todos os endpoints). Para Feature 1 veículos, é necessária uma pequena extensão de schema + service backend para incluir a foto do veículo. Feature 2 é somente frontend — troca/remoção do atributo `capture` nos inputs e adição de novo botão com preview em pessoa-detalhe.

**Tech Stack:** Alpine.js (frontend), FastAPI + SQLAlchemy async (backend), Pydantic v2 (schemas), Tailwind CSS

---

## Contexto dos arquivos

| Arquivo | Papel |
|---|---|
| `frontend/js/pages/consulta.js` | Página de busca unificada — 3 seções: pessoa, endereço, veículo |
| `frontend/js/pages/pessoa-detalhe.js` | Ficha da pessoa — seção "Fotos" (linhas 69-89) |
| `app/schemas/consulta.py` | `VeiculoInfo` (linha 32) — adicionar `foto_veiculo_url` |
| `app/repositories/veiculo_repo.py` | `get_pessoas_por_veiculo` (linha 120) — retorna `(Pessoa, Veiculo)` |
| `app/services/consulta_service.py` | `pessoas_por_veiculo` (linha 223) — busca fotos de veículo |
| `app/api/v1/consultas.py` | Endpoint `pessoas_por_veiculo` (linha 198) — monta `VeiculoInfo` |

---

## Task 1: Avatar na busca por texto (pessoa)

**Files:**
- Modify: `frontend/js/pages/consulta.js:77-89`

O card atual (linhas 77-89) tem só texto. Adicionar avatar `w-8 h-8` à esquerda.

**Passo 1: Localizar o template x-for de pessoasTexto (linha 76)**

Encontre o bloco:
```html
<template x-for="p in pessoasTexto" :key="'t-' + p.id">
  <div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
        <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
        <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
      </div>
      <svg class="w-4 h-4 text-slate-500 shrink-0" ...>
        <path ... d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
      </svg>
    </div>
  </div>
</template>
```

**Passo 2: Substituir o `<div class="flex items-center justify-between">` interno**

Substituir de:
```html
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
```

Para:
```html
      <div class="flex items-center gap-3">
        <!-- Avatar -->
        <template x-if="p.foto_principal_url">
          <img :src="p.foto_principal_url" class="w-8 h-8 rounded-full object-cover shrink-0">
        </template>
        <template x-if="!p.foto_principal_url">
          <div class="w-8 h-8 rounded-full bg-slate-700 shrink-0 flex items-center justify-center text-slate-500">
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
            </svg>
          </div>
        </template>
        <!-- Texto -->
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
          <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
          <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
        </div>
        <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
        </svg>
      </div>
```

**Passo 3: Testar manualmente**

Abrir o app no browser, fazer uma busca por nome. Verificar que aparece o avatar (ou silhueta) à esquerda de cada resultado.

**Passo 4: Commit**

```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(consulta): exibir avatar nos resultados de busca por texto"
```

---

## Task 2: Avatar na busca por endereço

**Files:**
- Modify: `frontend/js/pages/consulta.js:271-287`

O card de `pessoasEndereco` (dentro de `template x-for="p in pessoasEndereco"`) é idêntico ao de texto, mas inclui também `endereco_criado_em`. Aplicar o mesmo padrão de avatar.

**Passo 1: Localizar o template x-for de pessoasEndereco (linha ~271)**

Encontre:
```html
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
      <svg class="w-4 h-4 text-slate-500 shrink-0" ...>
        <path ... d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
      </svg>
    </div>
  </div>
</template>
```

**Passo 2: Substituir o `<div class="flex items-center justify-between">` interno**

Substituir de:
```html
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
```

Para:
```html
      <div class="flex items-center gap-3">
        <!-- Avatar -->
        <template x-if="p.foto_principal_url">
          <img :src="p.foto_principal_url" class="w-8 h-8 rounded-full object-cover shrink-0">
        </template>
        <template x-if="!p.foto_principal_url">
          <div class="w-8 h-8 rounded-full bg-slate-700 shrink-0 flex items-center justify-center text-slate-500">
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
            </svg>
          </div>
        </template>
        <!-- Texto -->
        <div class="flex-1 min-w-0">
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
```

**Passo 3: Commit**

```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(consulta): exibir avatar nos resultados de busca por endereço"
```

---

## Task 3: Foto de veículo no schema backend

Para exibir o thumbnail do veículo na busca por veículo, é necessário adicionar `foto_veiculo_url` ao schema e ao service.

**Files:**
- Modify: `app/schemas/consulta.py:32-47`
- Modify: `app/services/consulta_service.py` (método `pessoas_por_veiculo`)
- Modify: `app/api/v1/consultas.py:198-220`

**Passo 1: Adicionar `foto_veiculo_url` ao `VeiculoInfo`**

Em `app/schemas/consulta.py`, localizar `class VeiculoInfo` (linha 32) e adicionar o campo:

```python
class VeiculoInfo(BaseModel):
    """Dados resumidos do veículo que originou o vínculo.

    Attributes:
        placa: Placa do veículo (uppercase normalizado).
        modelo: Modelo do veículo (opcional).
        cor: Cor do veículo (opcional).
        ano: Ano do veículo (opcional).
        foto_veiculo_url: URL da foto do veículo cadastrada (R2/S3), para thumbnail na busca.
    """

    placa: str
    modelo: str | None = None
    cor: str | None = None
    ano: int | None = None
    foto_veiculo_url: str | None = None

    model_config = {"from_attributes": True}
```

**Passo 2: Buscar fotos dos veículos no service**

Em `app/services/consulta_service.py`, localizar o método `pessoas_por_veiculo` (linha ~223).

Esse método chama `self.veiculo_repo.get_pessoas_por_veiculo(...)` e retorna uma lista de dicts `{"pessoa": Pessoa, "veiculo": Veiculo}`.

Adicionar após a chamada ao repo a busca das fotos dos veículos encontrados:

```python
from sqlalchemy import select
from app.models.foto import Foto

async def pessoas_por_veiculo(self, placa, modelo, cor, skip, limit, user):
    rows = await self.veiculo_repo.get_pessoas_por_veiculo(
        placa=placa,
        modelo=modelo,
        cor=cor,
        guarnicao_id=user.guarnicao_id,
        skip=skip,
        limit=limit,
    )

    # Buscar foto principal de cada veículo único
    veiculo_ids = list({row[1].id for row in rows})
    fotos_veiculos: dict[int, str | None] = {}
    if veiculo_ids:
        stmt = (
            select(Foto.veiculo_id, Foto.arquivo_url)
            .where(
                Foto.veiculo_id.in_(veiculo_ids),
                Foto.ativo == True,  # noqa: E712
            )
            .order_by(Foto.criado_em.desc())
        )
        result = await self.db.execute(stmt)
        for veiculo_id, arquivo_url in result.all():
            if veiculo_id not in fotos_veiculos:
                fotos_veiculos[veiculo_id] = arquivo_url

    return [
        {"pessoa": row[0], "veiculo": row[1], "foto_veiculo_url": fotos_veiculos.get(row[1].id)}
        for row in rows
    ]
```

**Nota:** Verificar como está implementado atualmente o método `pessoas_por_veiculo` no service antes de editar — o código acima é o padrão esperado mas pode diferir em detalhes.

**Passo 3: Passar `foto_veiculo_url` no endpoint**

Em `app/api/v1/consultas.py`, no bloco que monta `PessoaComVeiculoRead` (linha ~198-219), adicionar `foto_veiculo_url` ao `VeiculoInfo`:

```python
return [
    PessoaComVeiculoRead(
        ...
        veiculo_info=VeiculoInfo(
            placa=row["veiculo"].placa,
            modelo=row["veiculo"].modelo,
            cor=row["veiculo"].cor,
            ano=row["veiculo"].ano,
            foto_veiculo_url=row.get("foto_veiculo_url"),
        ),
    )
    for row in rows
]
```

**Passo 4: Testar via curl/Swagger**

```bash
# Buscar veículo — verificar que foto_veiculo_url aparece no response
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/consultas/pessoas-por-veiculo?placa=ABC"
```

Verificar que `veiculo_info.foto_veiculo_url` está presente no JSON (pode ser `null` se não houver foto cadastrada).

**Passo 5: Commit**

```bash
git add app/schemas/consulta.py app/services/consulta_service.py app/api/v1/consultas.py
git commit -m "feat(consulta): incluir foto_veiculo_url no response de busca por veículo"
```

---

## Task 4: Avatar + thumbnail na busca por veículo (frontend)

**Files:**
- Modify: `frontend/js/pages/consulta.js:338-355`

**Passo 1: Localizar o template x-for de pessoasVeiculo (linha ~338)**

Encontre:
```html
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
      <svg class="w-4 h-4 text-slate-500 shrink-0" .../>
    </div>
  </div>
</template>
```

**Passo 2: Substituir o `<div class="flex items-center justify-between">` interno**

Substituir de:
```html
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
```

Para:
```html
      <div class="flex items-center gap-3">
        <!-- Avatar da pessoa -->
        <template x-if="p.foto_principal_url">
          <img :src="p.foto_principal_url" class="w-8 h-8 rounded-full object-cover shrink-0">
        </template>
        <template x-if="!p.foto_principal_url">
          <div class="w-8 h-8 rounded-full bg-slate-700 shrink-0 flex items-center justify-center text-slate-500">
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
            </svg>
          </div>
        </template>
        <!-- Texto -->
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
          <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
          <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
          <p x-show="p.veiculo_info" class="text-xs text-slate-500 mt-0.5"
             x-text="'Vinculado via: ' + [p.veiculo_info?.placa, p.veiculo_info?.modelo, p.veiculo_info?.cor, p.veiculo_info?.ano].filter(Boolean).join(' · ')">
          </p>
        </div>
        <!-- Thumbnail do veículo -->
        <template x-if="p.veiculo_info?.foto_veiculo_url">
          <img :src="p.veiculo_info.foto_veiculo_url"
               class="w-8 h-8 rounded object-cover shrink-0 border border-slate-600">
        </template>
        <template x-if="!p.veiculo_info?.foto_veiculo_url">
          <div class="w-8 h-8 rounded bg-slate-700 shrink-0 flex items-center justify-center text-slate-500">
            <svg class="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12"/>
            </svg>
          </div>
        </template>
        <svg class="w-4 h-4 text-slate-500 shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
        </svg>
      </div>
```

**Passo 3: Commit**

```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(consulta): exibir avatar de pessoa e thumbnail de veículo na busca por veículo"
```

---

## Task 5: Upload only no cadastro de Nova Pessoa (consulta)

Remover `capture="environment"` do input de foto no form "Nova Pessoa" e adicionar mini-preview.

**Files:**
- Modify: `frontend/js/pages/consulta.js:199-205`

**Passo 1: Localizar o campo foto no form (linha ~199)**

Encontre:
```html
          <div>
            <label class="block text-xs text-slate-400 mb-1">Foto</label>
            <input type="file" accept="image/*" capture="environment"
                   @change="fotoPessoa = $event.target.files[0] || null"
                   class="text-sm text-slate-400 w-full">
            <p x-show="fotoPessoa" class="text-xs text-slate-500 mt-1" x-text="fotoPessoa?.name"></p>
          </div>
```

**Passo 2: Substituir o bloco inteiro**

Substituir de:
```html
          <div>
            <label class="block text-xs text-slate-400 mb-1">Foto</label>
            <input type="file" accept="image/*" capture="environment"
                   @change="fotoPessoa = $event.target.files[0] || null"
                   class="text-sm text-slate-400 w-full">
            <p x-show="fotoPessoa" class="text-xs text-slate-500 mt-1" x-text="fotoPessoa?.name"></p>
          </div>
```

Para:
```html
          <div>
            <label class="block text-xs text-slate-400 mb-1">Foto</label>
            <label class="cursor-pointer inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded bg-slate-700 text-blue-400 hover:bg-slate-600 transition-colors">
              📁 Selecionar foto
              <input type="file" accept="image/*"
                     @change="fotoPessoa = $event.target.files[0] || null; fotoPessoaPreviewUrl = fotoPessoa ? URL.createObjectURL(fotoPessoa) : ''"
                     class="hidden">
            </label>
            <div x-show="fotoPessoa" class="flex items-center gap-2 mt-2">
              <img :src="fotoPessoaPreviewUrl" class="w-12 h-12 rounded object-cover shrink-0">
              <span class="text-xs text-slate-500 truncate" x-text="fotoPessoa?.name"></span>
            </div>
          </div>
```

**Passo 3: Adicionar `fotoPessoaPreviewUrl` ao estado da página**

No objeto `consultaPage()` (linha ~372), adicionar ao estado após `fotoPessoa: null`:
```javascript
    fotoPessoa: null,
    fotoPessoaPreviewUrl: "",
```

**Passo 4: Limpar o preview ao resetar o form**

No método `criarPessoa()` (linha ~607), após `this.fotoPessoa = null;`, adicionar:
```javascript
        this.fotoPessoa = null;
        this.fotoPessoaPreviewUrl = "";
```

Também no botão "Cancelar" do form e no botão "+ Nova Pessoa" (linhas 17 e 152), adicionar `fotoPessoaPreviewUrl = ''` ao reset. Exemplo na linha 152:
```javascript
@click="showCadastroPessoa = false; novaPessoa = { ... }; fotoPessoa = null; fotoPessoaPreviewUrl = ''; erroCadastro = null"
```

E na linha 17 (botão "+ Nova Pessoa"):
```javascript
@click="showCadastroPessoa = !showCadastroPessoa; novaPessoa = { ... }; fotoPessoa = null; fotoPessoaPreviewUrl = ''; erroCadastro = null"
```

**Passo 5: Commit**

```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(consulta): upload de foto (sem câmera forçada) com preview no cadastro de pessoa"
```

---

## Task 6: Câmera + Upload com preview em pessoa-detalhe

Adicionar botão "+ Foto" na seção "Fotos" da ficha, com opções câmera e galeria, preview e upload via API.

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:69-89` (seção Fotos)
- Modify: `frontend/js/pages/pessoa-detalhe.js` (estado + método `uploadNovaFoto`)

**Passo 1: Adicionar estado para nova foto**

No objeto `pessoaDetalhePage()`, localizar onde as variáveis de estado são declaradas (próximo à linha 534 — `fotos: []`). Adicionar:

```javascript
    fotos: [],
    novaFotoFile: null,
    novaFotoPreviewUrl: "",
    uploadandoFoto: false,
```

**Passo 2: Adicionar método `uploadNovaFoto`**

No objeto do Alpine, adicionar o método após os métodos existentes de carregamento:

```javascript
    async uploadNovaFoto() {
      if (!this.novaFotoFile) return;
      this.uploadandoFoto = true;
      try {
        await api.uploadFile("/fotos/upload", this.novaFotoFile, {
          tipo: "rosto",
          pessoa_id: this.pessoaId,
        });
        // Recarregar lista de fotos
        this.fotos = await api.get(`/fotos/pessoa/${this.pessoaId}`);
        // Limpar estado
        if (this.novaFotoPreviewUrl) URL.revokeObjectURL(this.novaFotoPreviewUrl);
        this.novaFotoFile = null;
        this.novaFotoPreviewUrl = "";
        showToast("Foto adicionada com sucesso!", "success");
      } catch (err) {
        showToast(err?.message || "Erro ao enviar foto", "error");
      } finally {
        this.uploadandoFoto = false;
      }
    },

    onNovaFotoSelected(event) {
      const file = event.target.files?.[0];
      if (!file) return;
      if (this.novaFotoPreviewUrl) URL.revokeObjectURL(this.novaFotoPreviewUrl);
      this.novaFotoFile = file;
      this.novaFotoPreviewUrl = URL.createObjectURL(file);
    },
```

**Passo 3: Atualizar o template HTML da seção Fotos**

Localizar a seção "Fotos" (linha ~69-89):

```html
          <!-- Fotos -->
          <div x-show="fotos.length > 0" class="card space-y-2 border-l-4 border-l-amber-500">
            <h3 class="text-sm font-semibold text-slate-300">
              Fotos (<span x-text="fotos.length"></span>)
            </h3>
            <div class="grid grid-cols-3 gap-2">
              <template x-for="foto in fotos" :key="foto.id">
                <div>
                  <div class="relative">
                    <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
                         @click="fotoAmpliada = foto.arquivo_url">
                    <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                          x-text="foto.tipo || 'foto'"></span>
                  </div>
                  <p class="text-xs text-slate-400 text-center mt-1"
                     x-show="foto.data_hora"
                     x-text="foto.data_hora ? new Date(foto.data_hora).toLocaleDateString('pt-BR') : ''"></p>
                </div>
              </template>
            </div>
          </div>
```

Substituir por:

```html
          <!-- Fotos -->
          <div class="card space-y-2 border-l-4 border-l-amber-500">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-slate-300">
                Fotos (<span x-text="fotos.length"></span>)
              </h3>
              <!-- Botões câmera + galeria -->
              <div class="flex gap-1.5">
                <label class="cursor-pointer text-xs px-2 py-1 rounded bg-slate-700 text-blue-400 hover:bg-slate-600 transition-colors">
                  📷
                  <input type="file" accept="image/*" capture="environment" class="hidden"
                         @change="onNovaFotoSelected($event)">
                </label>
                <label class="cursor-pointer text-xs px-2 py-1 rounded bg-slate-700 text-blue-400 hover:bg-slate-600 transition-colors">
                  📁
                  <input type="file" accept="image/*" class="hidden"
                         @change="onNovaFotoSelected($event)">
                </label>
              </div>
            </div>

            <!-- Preview + botão enviar (aparece após selecionar) -->
            <div x-show="novaFotoFile" class="flex items-center gap-3 p-2 bg-slate-700/50 rounded-lg">
              <img :src="novaFotoPreviewUrl" class="w-12 h-12 rounded object-cover shrink-0">
              <div class="flex-1 min-w-0">
                <p class="text-xs text-slate-400 truncate" x-text="novaFotoFile?.name"></p>
              </div>
              <div class="flex gap-1.5 shrink-0">
                <button @click="uploadNovaFoto()"
                        :disabled="uploadandoFoto"
                        class="text-xs px-2 py-1 rounded bg-green-700 text-green-200 hover:bg-green-600 transition-colors disabled:opacity-50">
                  <span x-show="!uploadandoFoto">Enviar</span>
                  <span x-show="uploadandoFoto" class="flex items-center gap-1"><span class="spinner-xs"></span></span>
                </button>
                <button @click="novaFotoFile = null; if (novaFotoPreviewUrl) URL.revokeObjectURL(novaFotoPreviewUrl); novaFotoPreviewUrl = ''"
                        class="text-xs px-2 py-1 rounded bg-slate-600 text-slate-400 hover:bg-slate-500 transition-colors">
                  ✕
                </button>
              </div>
            </div>

            <!-- Grid de fotos existentes -->
            <div x-show="fotos.length > 0" class="grid grid-cols-3 gap-2">
              <template x-for="foto in fotos" :key="foto.id">
                <div>
                  <div class="relative">
                    <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
                         @click="fotoAmpliada = foto.arquivo_url">
                    <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                          x-text="foto.tipo || 'foto'"></span>
                  </div>
                  <p class="text-xs text-slate-400 text-center mt-1"
                     x-show="foto.data_hora"
                     x-text="foto.data_hora ? new Date(foto.data_hora).toLocaleDateString('pt-BR') : ''"></p>
                </div>
              </template>
            </div>

            <!-- Estado vazio -->
            <p x-show="fotos.length === 0 && !novaFotoFile" class="text-xs text-slate-500">
              Nenhuma foto cadastrada.
            </p>
          </div>
```

**Nota sobre `spinner-xs`:** O projeto usa a classe `.spinner` definida em `app.css`. Se não houver uma variante menor, use o mesmo `.spinner` ou substitua por `...` como texto de loading.

**Passo 4: Verificar método `uploadFile` da api.js**

Verificar em `frontend/js/api.js` se o método `uploadFile` aceita o formato `{ tipo, pessoa_id }` como params. Se aceitar como terceiro argumento, o código acima está correto. Se tiver assinatura diferente, ajustar a chamada.

**Passo 5: Testar manualmente**

1. Abrir ficha de uma pessoa
2. Clicar em 📷 — deve abrir câmera no mobile / seletor com câmera como opção no desktop
3. Clicar em 📁 — deve abrir seletor de arquivos/galeria
4. Após selecionar: verificar que preview aparece
5. Clicar "Enviar": verificar que foto aparece no grid

**Passo 6: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(pessoa-detalhe): adicionar foto via câmera ou galeria com preview"
```

---

## Resumo dos commits esperados

1. `feat(consulta): exibir avatar nos resultados de busca por texto`
2. `feat(consulta): exibir avatar nos resultados de busca por endereço`
3. `feat(consulta): incluir foto_veiculo_url no response de busca por veículo`
4. `feat(consulta): exibir avatar de pessoa e thumbnail de veículo na busca por veículo`
5. `feat(consulta): upload de foto (sem câmera forçada) com preview no cadastro de pessoa`
6. `feat(pessoa-detalhe): adicionar foto via câmera ou galeria com preview`
