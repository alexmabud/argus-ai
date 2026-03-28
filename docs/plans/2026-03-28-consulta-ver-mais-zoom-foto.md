# Consulta: Ver Mais Completo + Zoom de Foto Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Corrigir o "ver mais" para buscar todos os cadastros (não apenas os 20 já carregados) e adicionar press & hold para ampliar foto na lista e no modal.

**Architecture:** Tudo em `frontend/js/pages/consulta.js` — componente Alpine.js único. Sem mudanças de backend (API já suporta `limit=100`). Três tasks independentes executadas sequencialmente no mesmo arquivo.

**Tech Stack:** Alpine.js (x-data, x-show, x-for), Pointer Events API (pointerdown/pointerup), HTML/CSS inline (padrão do projeto)

---

## Task 1: Fix Ver Mais — buscar todos os registros ao abrir o modal

### Contexto
- `searchPorTexto()` (linha ~668): busca `/consultas/?q=...&tipo=pessoa` sem `limit` → recebe 20
- `searchPorEndereco()` (linha ~703): busca `/consultas/?q=&tipo=pessoa&bairro=...` sem `limit` → recebe 20
- `searchPorVeiculo()` (linha ~720): busca `/consultas/pessoas-por-veiculo?...` sem `limit` → recebe 20
- Botões "ver mais" (linhas 117, 343, 438): apenas `@click="modalVerMaisTexto = true"` — não refaz busca
- Estado dos modais (linhas 592-595): apenas booleanos `modalVerMaisTexto`, `modalVerMaisEndereco`, `modalVerMaisVeiculo`

**Files:**
- Modify: `frontend/js/pages/consulta.js`

---

**Step 1: Adicionar estado `loadingVerMais` no bloco de estado (linha ~595)**

Localizar o bloco:
```javascript
    // Estado — modais ver mais
    modalVerMaisTexto: false,
    modalVerMaisEndereco: false,
    modalVerMaisVeiculo: false,
```

Substituir por:
```javascript
    // Estado — modais ver mais
    modalVerMaisTexto: false,
    modalVerMaisEndereco: false,
    modalVerMaisVeiculo: false,
    loadingVerMais: false,
```

---

**Step 2: Adicionar métodos `abrirVerMaisTexto`, `abrirVerMaisEndereco`, `abrirVerMaisVeiculo` após o método `searchPorVeiculo` (logo antes de `viewPessoa`, linha ~737)**

Localizar:
```javascript
    viewPessoa(id) {
```

Inserir antes:
```javascript
    async abrirVerMaisTexto() {
      this.modalVerMaisTexto = true;
      this.loadingVerMais = true;
      try {
        const url = `/consultas/?q=${encodeURIComponent(this.query)}&tipo=pessoa&limit=100`;
        const r = await api.get(url);
        this.pessoasTexto = r.pessoas || [];
      } catch {
        showToast("Erro ao carregar todos os resultados", "error");
      } finally {
        this.loadingVerMais = false;
      }
    },

    async abrirVerMaisEndereco() {
      this.modalVerMaisEndereco = true;
      this.loadingVerMais = true;
      try {
        let url = `/consultas/?q=&tipo=pessoa&limit=100`;
        if (this.filtroBairro.length >= 2) url += `&bairro=${encodeURIComponent(this.filtroBairro)}`;
        if (this.filtroCidade.length >= 2) url += `&cidade=${encodeURIComponent(this.filtroCidade)}`;
        if (this.filtroEstado.length >= 1) url += `&estado=${encodeURIComponent(this.filtroEstado.toUpperCase())}`;
        const r = await api.get(url);
        this.pessoasEndereco = r.pessoas || [];
      } catch {
        showToast("Erro ao carregar todos os resultados", "error");
      } finally {
        this.loadingVerMais = false;
      }
    },

    async abrirVerMaisVeiculo() {
      this.modalVerMaisVeiculo = true;
      this.loadingVerMais = true;
      try {
        const params = new URLSearchParams();
        if (this.filtroPlaca.length >= 2) params.append("placa", this.filtroPlaca.toUpperCase());
        if (this.filtroModelo.length >= 2) params.append("modelo", this.filtroModelo);
        if (this.filtroCor.length >= 1) params.append("cor", this.filtroCor);
        params.append("limit", "100");
        const r = await api.get(`/consultas/pessoas-por-veiculo?${params}`);
        this.pessoasVeiculo = Array.isArray(r) ? r : [];
      } catch {
        showToast("Erro ao carregar todos os resultados", "error");
      } finally {
        this.loadingVerMais = false;
      }
    },

    viewPessoa(id) {
```

---

**Step 3: Atualizar os 3 botões "ver mais" para chamar os novos métodos**

Botão texto (linha ~117):
```html
          <button x-show="pessoasTexto.length > 10" @click="modalVerMaisTexto = true"
```
→ substituir por:
```html
          <button x-show="pessoasTexto.length > 10" @click="abrirVerMaisTexto()"
```

Botão endereço (linha ~343):
```html
          <button x-show="pessoasEndereco.length > 10" @click="modalVerMaisEndereco = true"
```
→ substituir por:
```html
          <button x-show="pessoasEndereco.length > 10" @click="abrirVerMaisEndereco()"
```

Botão veículo (linha ~438):
```html
          <button x-show="pessoasVeiculo.length > 10" @click="modalVerMaisVeiculo = true"
```
→ substituir por:
```html
          <button x-show="pessoasVeiculo.length > 10" @click="abrirVerMaisVeiculo()"
```

---

**Step 4: Adicionar spinner de loading dentro dos 3 modais**

Em cada modal, logo após o `<div style="display: grid; ...">` e antes do `</template>` final, adicionar spinner condicional. Exemplo para o modal texto — localizar:

```html
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasTexto" :key="'mt-' + p.id">
```

Substituir por:
```html
        <div x-show="loadingVerMais" style="display: flex; justify-content: center; padding: 1.5rem;">
          <span class="spinner"></span>
        </div>
        <div x-show="!loadingVerMais" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.375rem;">
          <template x-for="p in pessoasTexto" :key="'mt-' + p.id">
```

E fechar o novo `<div x-show="!loadingVerMais">` antes do `</div>` que fecha o grid. Repetir para os modais endereço e veículo (mesma estrutura).

---

**Step 5: Testar manualmente**
1. `make dev` (ou `docker compose up`)
2. Abrir consulta, buscar por nome com mais de 10 resultados
3. Clicar "ver mais" → verificar que spinner aparece e lista carrega com mais registros (até 100)
4. Repetir para busca por endereço e por veículo

---

**Step 6: Commit**
```bash
git add frontend/js/pages/consulta.js
git commit -m "fix(frontend): ver mais busca todos os registros com limit=100"
```

---

## Task 2: Zoom de foto por press & hold — lista inicial + overlay global

### Contexto
- Lista inicial mostra avatares 32×32px (linhas ~96-106 para texto, ~321-329 para endereço, ~403-411 para veículo)
- `viewPessoa(p.id)` é chamado no `@click` do `<div>` pai — não pode interferir com press & hold
- Precisamos distinguir click rápido (navegar) de press longo (zoom) com timer de 200ms

**Files:**
- Modify: `frontend/js/pages/consulta.js`

---

**Step 1: Adicionar estado do zoom e timer no bloco de estado (após `loadingVerMais`)**

Localizar:
```javascript
    loadingVerMais: false,
```

Adicionar logo após:
```javascript
    zoomFotoUrl: '',
    zoomFotoVisible: false,
    _zoomTimer: null,
```

---

**Step 2: Adicionar métodos de zoom após `abrirVerMaisVeiculo` e antes de `viewPessoa`**

Localizar:
```javascript
    viewPessoa(id) {
```

Inserir antes:
```javascript
    iniciarZoom(url) {
      if (!url) return;
      this._zoomTimer = setTimeout(() => {
        this.zoomFotoUrl = url;
        this.zoomFotoVisible = true;
      }, 200);
    },

    cancelarZoom() {
      clearTimeout(this._zoomTimer);
      this._zoomTimer = null;
      this.zoomFotoVisible = false;
    },

    viewPessoa(id) {
```

---

**Step 3: Adicionar overlay de zoom no HTML (logo antes do fechamento do `</div>` raiz da página, na linha ~546)**

Localizar (último bloco antes do fechamento):
```html
    </div>
  </div>
  `;
}
```

Substituir por:
```html
    </div>

    <!-- Overlay de zoom de foto -->
    <div x-show="zoomFotoVisible" @pointerdown.stop="cancelarZoom()"
         style="position:fixed;inset:0;z-index:100;background:rgba(0,0,0,0.92);display:flex;align-items:center;justify-content:center;touch-action:none;">
      <img :src="zoomFotoUrl" alt="Foto ampliada"
           style="max-width:80vw;max-height:80vh;border-radius:4px;object-fit:contain;pointer-events:none;">
    </div>
  </div>
  `;
}
```

---

**Step 4: Adicionar eventos de zoom nas `<img>` da lista inicial (busca por texto)**

Localizar o bloco de avatar da lista de texto (linha ~96):
```html
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url" :alt="'Foto de ' + p.nome"
                     style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);">
              </template>
```

Substituir por:
```html
              <template x-if="p.foto_principal_url">
                <img :src="p.foto_principal_url" :alt="'Foto de ' + p.nome"
                     @pointerdown.stop="iniciarZoom(p.foto_principal_url)"
                     @pointerup.stop="cancelarZoom()" @pointerleave="cancelarZoom()"
                     style="width:32px;height:32px;border-radius:4px;object-fit:cover;flex-shrink:0;border:1px solid var(--color-border);touch-action:none;">
              </template>
```

Repetir o mesmo padrão para as listas de endereço (linha ~321) e veículo (linha ~403) — mesma substituição na `<img>` de avatar 32×32px.

---

**Step 5: Testar manualmente**
1. Buscar por nome → pressionar e segurar foto de um resultado por >200ms → foto deve ampliar
2. Soltar → overlay some
3. Clicar rápido na linha → navega para ficha (comportamento existente preservado)

---

**Step 6: Commit**
```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(frontend): zoom de foto por press & hold na lista de consulta"
```

---

## Task 3: Press & hold + click no modal "Ver Mais"

### Contexto
- Os 3 modais têm grid 4 colunas com `@click="modalVerMaisTexto = false; viewPessoa(p.id)"` no `<div>` pai
- As `<img>` dentro do modal não têm eventos de zoom ainda
- Queremos: press longo → zoom, click rápido → fechar modal + navegar
- Reusar `iniciarZoom` / `cancelarZoom` da Task 2

**Files:**
- Modify: `frontend/js/pages/consulta.js`

---

**Step 1: Substituir `@click` dos itens do modal texto por lógica press & hold**

Localizar no modal texto (linha ~467):
```html
            <div @click="modalVerMaisTexto = false; viewPessoa(p.id)" style="cursor: pointer; text-align: center; min-width: 0;">
```

Substituir por:
```html
            <div @pointerdown="iniciarZoom(p.foto_principal_url); _vmTextoTimer = setTimeout(() => {}, 0)"
                 @pointerup="cancelarZoom(); if (!zoomFotoVisible) { modalVerMaisTexto = false; viewPessoa(p.id); }"
                 @pointerleave="cancelarZoom()"
                 style="cursor: pointer; text-align: center; min-width: 0; touch-action: none;">
```

**Observação:** A lógica do `iniciarZoom` já usa setTimeout de 200ms. No `pointerup`, `zoomFotoVisible` só será `true` se o timer disparou (ou seja, segurou >200ms). Se `zoomFotoVisible` for false = foi click rápido = navega.

---

**Step 2: Repetir para modal endereço (linha ~498)**

Localizar:
```html
            <div @click="modalVerMaisEndereco = false; viewPessoa(p.id)" style="cursor: pointer; text-align: center; min-width: 0;">
```

Substituir por:
```html
            <div @pointerdown="iniciarZoom(p.foto_principal_url)"
                 @pointerup="cancelarZoom(); if (!zoomFotoVisible) { modalVerMaisEndereco = false; viewPessoa(p.id); }"
                 @pointerleave="cancelarZoom()"
                 style="cursor: pointer; text-align: center; min-width: 0; touch-action: none;">
```

---

**Step 3: Repetir para modal veículo (linha ~529)**

Localizar:
```html
            <div @click="modalVerMaisVeiculo = false; viewPessoa(p.id)" style="cursor: pointer; text-align: center; min-width: 0;">
```

Substituir por:
```html
            <div @pointerdown="iniciarZoom(p.foto_principal_url)"
                 @pointerup="cancelarZoom(); if (!zoomFotoVisible) { modalVerMaisVeiculo = false; viewPessoa(p.id); }"
                 @pointerleave="cancelarZoom()"
                 style="cursor: pointer; text-align: center; min-width: 0; touch-action: none;">
```

---

**Step 4: Testar manualmente**
1. Abrir modal "ver mais"
2. Pressionar e segurar foto >200ms → ampliar foto via overlay
3. Soltar → overlay some, modal continua aberto
4. Tocar/clicar rápido em uma foto → fecha modal + navega para ficha

---

**Step 5: Commit final**
```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(frontend): press & hold para zoom de foto no modal ver mais"
```
