# Fix Fotos na Consulta de Pessoa — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir exibição de fotos de pessoa na consulta e adicionar fotos de veículo abaixo dos dados de veículos.

**Architecture:**
Dois problemas distintos. O primeiro é de URL: o container Docker usa `S3_ENDPOINT=http://minio:9000` (hostname interno) para fazer upload, mas essa mesma URL é salva no banco e retornada ao browser — que não consegue resolver `minio`. A solução é separar o endpoint interno do endpoint público com uma nova config `S3_PUBLIC_URL`. O segundo problema é que fotos de veículo são enviadas sem `pessoa_id`, apenas com `abordagem_id`, então não aparecem em `/fotos/pessoa/{id}`. A solução é buscar fotos das abordagens no frontend e exibi-las separadamente.

**Tech Stack:** Python/FastAPI, Pydantic Settings, Alpine.js, MinIO (dev) / Cloudflare R2 (prod)

---

## Diagnóstico

### Problema 1 — Foto aparece placeholder mas não carrega a imagem

**Causa:** `storage_service.py` constrói a URL pública usando `settings.S3_ENDPOINT`:
```python
url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"
```
No Docker Compose, a API recebe `S3_ENDPOINT=http://minio:9000` (hostname interno do Docker). Essa URL é salva no banco. Quando o browser tenta carregar `http://minio:9000/argus/fotos/...`, falha — o browser não conhece o hostname `minio`.

**Fix:** Adicionar `S3_PUBLIC_URL` (opcional, padrão = `S3_ENDPOINT`). O docker-compose não precisa sobrescrever essa variável, então ela herda do `.env` onde já está `S3_ENDPOINT=http://localhost:9000` — que o browser consegue acessar.

### Problema 2 — Fotos de veículo não aparecem na consulta de pessoa

**Causa:** Em `abordagem-nova.js`, fotos de veículo são enviadas com:
```js
{ tipo: "veiculo", abordagem_id: result.id }  // sem pessoa_id!
```
O endpoint `GET /fotos/pessoa/{pessoaId}` retorna apenas fotos com `pessoa_id` correspondente. Fotos de veículo ficam "perdidas" — existem no banco mas não são carregadas.

**Fix:** No frontend (`pessoa-detalhe.js`), após carregar abordagens, buscar fotos de cada abordagem em paralelo, filtrar por `tipo in ['veiculo', 'placa']`, e exibir uma galeria abaixo da seção de veículos.

---

### Task 1: Adicionar `S3_PUBLIC_URL` ao config

**Files:**
- Modify: `app/config.py`
- Modify: `app/services/storage_service.py`
- Modify: `.env.example`

**Step 1: Adicionar campo `S3_PUBLIC_URL` em `app/config.py`**

Localizar o bloco de configurações de storage (em torno da linha 76) e adicionar após `S3_BUCKET`:

```python
S3_BUCKET: str = "argus"
S3_PUBLIC_URL: str | None = None  # URL pública do storage (browser). Default: S3_ENDPOINT

@property
def s3_public_url(self) -> str:
    """Retorna a URL pública do storage, usada nas URLs retornadas ao browser."""
    return self.S3_PUBLIC_URL or self.S3_ENDPOINT
```

Também atualizar o docstring da classe para incluir:
```
S3_PUBLIC_URL: URL pública do storage acessível pelo browser (ex: http://localhost:9000). Opcional — padrão S3_ENDPOINT.
```

**Step 2: Atualizar `storage_service.py` para usar `s3_public_url`**

Na linha 77 de `app/services/storage_service.py`, trocar:
```python
url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{key}"
```
por:
```python
url = f"{settings.s3_public_url}/{settings.S3_BUCKET}/{key}"
```

**Step 3: Atualizar `.env.example`**

Adicionar após `S3_BUCKET=argus`:
```
# URL pública do storage acessível pelo browser.
# Em desenvolvimento com Docker, S3_ENDPOINT é http://minio:9000 (interno),
# mas o browser acessa em http://localhost:9000.
# Defina esta variável se o endpoint interno diferir do público.
# S3_PUBLIC_URL=http://localhost:9000
```

**Step 4: Verificar manualmente**

Subir o ambiente com `docker compose up -d`, fazer upload de uma foto via nova abordagem, consultar a pessoa e confirmar que a imagem carrega corretamente no browser.

**Step 5: Commit**

```bash
git add app/config.py app/services/storage_service.py .env.example
git commit -m "fix(storage): separar S3_PUBLIC_URL do endpoint interno para URLs acessíveis pelo browser"
```

---

### Task 2: Carregar e exibir fotos de veículo na consulta de pessoa

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Step 1: Adicionar `fotosVeiculos` ao estado Alpine em `pessoaDetalhePage()`**

No objeto retornado por `pessoaDetalhePage()` (linha ~188), adicionar:
```js
fotosVeiculos: [],   // fotos de tipo 'veiculo' ou 'placa' das abordagens
```

**Step 2: Carregar fotos de veículo em `carregarAbordagens()`**

Após `this.abordagens = abordagens;`, buscar fotos de cada abordagem em paralelo e filtrar por tipo:

```js
// Carregar fotos de veículo/placa de todas as abordagens em paralelo
const fotosPromises = abordagens.map(ab =>
  api.get(`/fotos/abordagem/${ab.id}`).catch(() => [])
);
const fotosResultados = await Promise.all(fotosPromises);
const tiposVeiculo = ['veiculo', 'placa'];
this.fotosVeiculos = fotosResultados
  .flat()
  .filter(f => tiposVeiculo.includes(f.tipo));
```

**Step 3: Adicionar seção de fotos de veículo no template HTML**

Em `renderPessoaDetalhe()`, localizar o bloco `<!-- Veículos vinculados -->` (linha ~104) e adicionar a seção de fotos **imediatamente após** o fechamento do `</div>` desse bloco (linha ~122):

```html
<!-- Fotos de veículos -->
<div x-show="fotosVeiculos.length > 0" class="card space-y-2">
  <h3 class="text-sm font-semibold text-slate-300">
    Fotos de Veículos (<span x-text="fotosVeiculos.length"></span>)
  </h3>
  <div class="grid grid-cols-3 gap-2">
    <template x-for="foto in fotosVeiculos" :key="foto.id">
      <div class="relative">
        <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
             @click="fotoAmpliada = foto.arquivo_url">
        <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
              x-text="foto.tipo"></span>
      </div>
    </template>
  </div>
</div>
```

**Step 4: Verificar manualmente**

1. Registrar uma abordagem com foto de veículo
2. Consultar a pessoa abordada
3. Confirmar que a seção "Fotos de Veículos" aparece abaixo de "Veículos"
4. Confirmar que as fotos carregam corretamente

**Step 5: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): exibir fotos de veículo abaixo dos dados de veículos na consulta de pessoa"
```

---

## Ordem de execução

Executar Task 1 antes de Task 2. A Task 1 corrige o problema de URL que também afeta as fotos de veículo.
