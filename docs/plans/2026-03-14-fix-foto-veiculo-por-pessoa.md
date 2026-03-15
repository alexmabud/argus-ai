# Fix: Foto de Veículo Por Pessoa Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir bug onde a foto de um veículo é exibida incorretamente na ficha de outra pessoa — garantindo que cada veículo tenha sua própria foto corretamente associada.

**Architecture:** Adicionar `veiculo_id` nullable ao modelo `Foto` (migração), propagar esse campo pela stack (service → router → frontend), e corrigir o frontend para capturar/exibir uma foto por veículo em vez de uma única variável global.

**Tech Stack:** SQLAlchemy 2.0 async, Alembic, FastAPI Form, Alpine.js

---

## Contexto do Bug

**Causa raiz 1 — Frontend (captura):** `abordagem-nova.js` usa uma única variável `fotoVeiculoFile: null`. Ao cadastrar dois veículos novos com foto, a segunda foto sobrescreve a primeira. Só a última foto é enviada no submit.

**Causa raiz 2 — Dados (sem vínculo):** O upload envia apenas `abordagem_id`, sem `veiculo_id`. Fotos de veículo ficam soltas — impossível saber qual foto pertence a qual veículo.

**Causa raiz 3 — Frontend (exibição):** `pessoa-detalhe.js` exibe todas as fotos de veículo de uma abordagem num array plano sem correlação com o veículo específico da pessoa.

---

## Task 1: Adicionar `veiculo_id` ao modelo Foto + Migration

**Files:**
- Modify: `app/models/foto.py`
- Modify: `app/schemas/foto.py`
- Create migration via: `make migrate msg="adicionar_veiculo_id_em_fotos"`

**Step 1: Adicionar campo ao modelo**

Em `app/models/foto.py`, após a linha `abordagem_id`:

```python
# Antes (linha ~52):
abordagem_id: Mapped[int | None] = mapped_column(ForeignKey("abordagens.id"), nullable=True)

# Depois — adicionar logo abaixo:
abordagem_id: Mapped[int | None] = mapped_column(ForeignKey("abordagens.id"), nullable=True)
veiculo_id: Mapped[int | None] = mapped_column(
    ForeignKey("veiculos.id", ondelete="SET NULL"), nullable=True, index=True
)
```

Atualizar docstring da classe para incluir:
```
veiculo_id: ID do veículo associado (FK, opcional — preencher para fotos tipo "veiculo"/"placa").
```

E adicionar relacionamento após `abordagem`:
```python
veiculo = relationship("Veiculo")
```

**Step 2: Adicionar campo ao schema FotoRead**

Em `app/schemas/foto.py`, em `FotoRead`, após `abordagem_id`:

```python
abordagem_id: int | None = None
veiculo_id: int | None = None  # ← adicionar
```

Atualizar docstring do `FotoRead` para incluir:
```
veiculo_id: ID do veículo associado (null se não for foto de veículo específico).
```

**Step 3: Criar migration**

```bash
make migrate msg="adicionar_veiculo_id_em_fotos"
```

Verificar arquivo gerado em `alembic/versions/`. Conferir que contém:
```python
op.add_column('fotos', sa.Column('veiculo_id', sa.Integer(), nullable=True))
op.create_index('ix_fotos_veiculo_id', 'fotos', ['veiculo_id'])
op.create_foreign_key(None, 'fotos', 'veiculos', ['veiculo_id'], ['id'], ondelete='SET NULL')
```

**Step 4: Aplicar migration**

```bash
docker compose exec api alembic upgrade head
# ou localmente:
alembic upgrade head
```

**Step 5: Commit**

```bash
git add app/models/foto.py app/schemas/foto.py alembic/versions/
git commit -m "feat(model): adicionar veiculo_id em Foto para vincular foto ao veiculo"
```

---

## Task 2: Propagar `veiculo_id` pelo backend (service + router)

**Files:**
- Modify: `app/services/foto_service.py` (método `upload_foto`)
- Modify: `app/api/v1/fotos.py` (endpoint `upload_foto`)

**Step 1: Adicionar `veiculo_id` ao `FotoService.upload_foto()`**

Em `app/services/foto_service.py`, no método `upload_foto`, adicionar parâmetro após `abordagem_id`:

```python
async def upload_foto(
    self,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    pessoa_id: int | None,
    abordagem_id: int | None,
    veiculo_id: int | None,   # ← adicionar
    tipo: str,
    latitude: float | None,
    longitude: float | None,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Foto:
```

Na criação do objeto `Foto` dentro do método (localizar onde é instanciado), adicionar o campo:
```python
foto = Foto(
    arquivo_url=url,
    tipo=tipo,
    data_hora=...,
    pessoa_id=pessoa_id,
    abordagem_id=abordagem_id,
    veiculo_id=veiculo_id,   # ← adicionar
    latitude=latitude,
    longitude=longitude,
)
```

Atualizar docstring do método:
```
veiculo_id: ID do veículo associado (opcional — para fotos tipo "veiculo"/"placa").
```

**Step 2: Adicionar `veiculo_id` ao endpoint de upload**

Em `app/api/v1/fotos.py`, no endpoint `upload_foto`:

```python
@router.post("/upload", ...)
async def upload_foto(
    request: Request,
    file: UploadFile,
    tipo: FotoTipo = Form(FotoTipo.rosto),
    pessoa_id: int | None = Form(None),
    abordagem_id: int | None = Form(None),
    veiculo_id: int | None = Form(None),   # ← adicionar
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    ...
```

Propagar para o service:
```python
foto = await service.upload_foto(
    ...
    pessoa_id=pessoa_id,
    abordagem_id=abordagem_id,
    veiculo_id=veiculo_id,   # ← adicionar
    ...
)
```

Atualizar docstring do endpoint:
```
veiculo_id: ID do veículo associado (opcional — para fotos de veículos específicos).
```

**Step 3: Verificar que `FotoRead` serializa `veiculo_id` corretamente**

O campo já foi adicionado no Task 1. Confirmar que `model_config = {"from_attributes": True}` está presente — já está.

**Step 4: Commit**

```bash
git add app/services/foto_service.py app/api/v1/fotos.py
git commit -m "feat(api): aceitar veiculo_id no upload de foto para vincular ao veiculo"
```

---

## Task 3: Corrigir captura de foto no formulário de abordagem

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js`

**Contexto:** O formulário tem dois fluxos de adição de veículo:
1. **Veículo novo** (inline form `showNovoVeiculo`): usuário digita placa + seleciona foto, clica "Salvar veículo". O veículo é criado via API (`POST /veiculos/`) e o ID retornado é conhecido. A foto era guardada em `fotoVeiculoFile` para upload posterior no submit.
2. **Veículo existente** (autocomplete): selecionado via busca. Atualmente não tem campo de foto.

**Step 1: Trocar `fotoVeiculoFile` por `fotosVeiculos` (dict por veiculo_id)**

Localizar a inicialização do estado (~linha 398-404):

```javascript
// Antes:
fotoVeiculoFile: null,

// Depois:
fotosVeiculos: {},   // { [veiculo_id]: File }
```

**Step 2: Ao salvar veículo novo, guardar foto por ID**

Localizar o bloco de submit do veículo novo (~linha 596-616). Após `const veiculo = await api.post("/veiculos/", veiculoData)`, antes do reset:

```javascript
// Antes (linha ~615 — comentário):
// Reset (fotoVeiculoFile mantida — será enviada no submit() com o abordagem_id)
this.novoVeiculo = { placa: "", modelo: "", cor: "", ano: "" };
this.showNovoVeiculo = false;

// Depois:
if (this.fotoVeiculoFile) {
  this.fotosVeiculos = { ...this.fotosVeiculos, [veiculo.id]: this.fotoVeiculoFile };
  this.fotoVeiculoFile = null;
}
this.novoVeiculo = { placa: "", modelo: "", cor: "", ano: "" };
this.showNovoVeiculo = false;
```

> Nota: `fotoVeiculoFile` pode continuar existindo temporariamente como variável auxiliar do form inline. Ela já é definida no `@change="onFotoVeiculoSelected($event)"` do input de foto no form inline. Basta movê-la para `fotosVeiculos` quando o veículo for salvo.

**Step 3: Adicionar input de foto por veículo na seção de vínculo**

Localizar a seção `x-for="v in veiculosSelecionados"` (~linha 249). Dentro do loop, após o bloco de seleção de abordado (~linha 285), adicionar input de foto para veículos existentes (os selecionados via autocomplete que não passaram pelo form inline):

```html
<!-- Foto do veículo -->
<div class="flex items-center gap-2 mt-2">
  <label :for="'foto-v-' + v.id"
         class="cursor-pointer text-xs px-2 py-1 rounded flex items-center gap-1"
         :class="fotosVeiculos[v.id] ? 'bg-green-900/50 text-green-400' : 'bg-slate-700 text-blue-400 hover:bg-slate-600'">
    <span x-text="fotosVeiculos[v.id] ? '✓ Foto veículo' : '📷 Foto veículo'"></span>
  </label>
  <input type="file" accept="image/*" capture="environment"
         :id="'foto-v-' + v.id" class="hidden"
         @change="fotosVeiculos = {...fotosVeiculos, [v.id]: $event.target.files[0]}">
</div>
```

**Step 4: Corrigir o upload no submit()**

Localizar o bloco de upload de foto do veículo no submit (~linha 716-722):

```javascript
// Antes:
// Upload foto do veículo se houver
if (this.fotoVeiculoFile && result.id) {
  await api.uploadFile("/fotos/upload", this.fotoVeiculoFile, {
    tipo: "veiculo",
    abordagem_id: result.id,
  });
}

// Depois:
// Upload foto de cada veículo
for (const [veiculoIdStr, file] of Object.entries(this.fotosVeiculos)) {
  if (file) {
    await api.uploadFile("/fotos/upload", file, {
      tipo: "veiculo",
      abordagem_id: result.id,
      veiculo_id: parseInt(veiculoIdStr),
    });
  }
}
```

**Step 5: Limpar `fotosVeiculos` no reset após submit**

Localizar o reset (~linha 744-746):

```javascript
// Antes:
this.veiculoPorPessoa = {};
this.fotoVeiculoFile = null;

// Depois:
this.veiculoPorPessoa = {};
this.fotosVeiculos = {};
this.fotoVeiculoFile = null;
```

**Step 6: Verificar no browser**

1. Criar abordagem com dois veículos novos, cada um com foto diferente
2. Verificar no Network tab que dois requests de upload são feitos, cada um com `veiculo_id` correto

**Step 7: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "fix(frontend): capturar foto por veiculo em abordagem (era unica variavel global)"
```

---

## Task 4: Corrigir exibição de fotos de veículo na ficha da pessoa

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Contexto:** A ficha da pessoa mostra "Veículos Vinculados ao Abordado" com a lista de veículos (`this.veiculos`) e "Fotos de Veículos Vinculados ao Abordado" com um array plano `this.fotosVeiculos`. O problema: as fotos são exibidas sem correlação com os veículos. Com a correção do backend (Task 1+2), cada foto agora tem `veiculo_id`.

**Step 1: Converter `fotosVeiculos` para um mapa por `veiculo_id`**

Localizar o carregamento de fotos (~linha 382-385):

```javascript
// Antes:
const tiposVeiculo = ['veiculo', 'placa'];
this.fotosVeiculos = fotosResultados
  .flat()
  .filter(f => tiposVeiculo.includes(f.tipo));

// Depois — mapa: { [veiculo_id]: foto } (primeira foto por veículo)
const tiposVeiculo = ['veiculo', 'placa'];
const fotosPlanas = fotosResultados.flat().filter(f => tiposVeiculo.includes(f.tipo));
const mapaFotos = {};
for (const foto of fotosPlanas) {
  if (foto.veiculo_id && !mapaFotos[foto.veiculo_id]) {
    mapaFotos[foto.veiculo_id] = foto;
  }
}
this.fotosVeiculos = mapaFotos;   // { [veiculo_id]: FotoRead }
```

**Step 2: Atualizar a exibição — mostrar foto junto ao veículo**

Localizar a seção de veículos vinculados na template HTML (~linha 150-180). Encontrar onde cada veículo é renderizado (provavelmente `x-for="v in veiculos"`). Adicionar a foto do veículo ao lado/abaixo das informações do veículo:

```html
<!-- Dentro do template x-for="v in veiculos" -->
<template x-if="fotosVeiculos[v.id]">
  <img :src="fotosVeiculos[v.id].arquivo_url"
       class="w-16 h-16 object-cover rounded-lg cursor-pointer"
       @click="fotoAmpliada = fotosVeiculos[v.id].arquivo_url"
       loading="lazy">
</template>
```

**Step 3: Remover a seção separada "Fotos de Veículos"**

Localizar o bloco (~linha 184-203):
```html
<!-- Fotos de veículos -->
<div x-show="fotosVeiculos.length > 0" class="space-y-2">
  ...
</div>
```

Remover esse bloco inteiro — as fotos agora aparecem integradas a cada veículo.

> Alternativa: se quiser manter a galeria separada, trocar `x-show="fotosVeiculos.length > 0"` por `x-show="Object.keys(fotosVeiculos).length > 0"` e adaptar o `x-for` para `x-for="foto in Object.values(fotosVeiculos)"`. Mas integrar junto ao veículo é mais legível.

**Step 4: Verificar onde `veiculos` é renderizado no HTML**

Ler a template HTML completa (arquivo `frontend/pessoa-detalhe.html` ou similar) para encontrar onde os veículos vinculados são exibidos e inserir a foto no local correto.

> Se o HTML estiver embutido no JS (string template), pesquisar por `x-for="v in veiculos"` ou similar.

**Step 5: Verificar no browser**

1. Abrir ficha do Teste A (que tem Gol)
2. Ver que aparece a foto do Gol (não mais do Celta)
3. Abrir ficha do Teste B (que tem Celta)
4. Ver que aparece a foto do Celta

**Step 6: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "fix(frontend): exibir foto do veiculo correto na ficha da pessoa"
```

---

## Task 5: Verificação final

**Step 1: Testar o fluxo completo**

1. Criar abordagem com Pessoa A + Gol (com foto) e Pessoa B + Celta (com foto)
2. Verificar no Network tab: 2 uploads de foto de veículo, cada um com `veiculo_id` diferente
3. Verificar no banco: `SELECT id, tipo, veiculo_id, abordagem_id FROM fotos WHERE tipo IN ('veiculo','placa');`
   - Deve mostrar 2 linhas, cada uma com `veiculo_id` diferente
4. Abrir ficha Pessoa A → ver foto do Gol
5. Abrir ficha Pessoa B → ver foto do Celta

**Step 2: Rodar testes**

```bash
make test
```

**Step 3: Commit final se houver ajustes**

```bash
git commit -m "fix(foto): corrigir vinculacao de foto por veiculo em abordagem multi-veiculo"
```
