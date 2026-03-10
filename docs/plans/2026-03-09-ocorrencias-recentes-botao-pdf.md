# Ocorrências Recentes — Botão Abrir PDF

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar botão "Abrir PDF" ao lado do chip de status em cada item da lista "Ocorrências Recentes".

**Architecture:** Mudança puramente de template Alpine.js no frontend. A API já retorna `arquivo_pdf_url` em `OcorrenciaRead`, basta expô-la na lista recente (o mesmo padrão já existe nos resultados de busca).

**Tech Stack:** Alpine.js, Tailwind CSS, HTML

---

### Task 1: Adicionar botão "Abrir PDF" na lista de Ocorrências Recentes

**Files:**
- Modify: `frontend/js/pages/ocorrencia-upload.js:109-111`

**Contexto do código atual (linhas 103–113):**

```html
<div class="card">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-sm font-medium text-slate-200" x-text="oc.numero_ocorrencia"></p>
      <p class="text-xs text-slate-500" x-text="new Date(oc.criado_em).toLocaleDateString('pt-BR')"></p>
    </div>
    <span class="text-xs px-2 py-0.5 rounded-full"
          :class="oc.processada ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'"
          x-text="oc.processada ? 'Processada' : 'Pendente'"></span>
  </div>
</div>
```

O chip de status está sozinho à direita. Basta envolver chip + botão num `div.flex.items-center.gap-2`.

**Step 1: Aplicar a mudança no template**

Substituir o bloco `<div class="card">` interno (linhas 103–113) por:

```html
<div class="card">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-sm font-medium text-slate-200" x-text="oc.numero_ocorrencia"></p>
      <p class="text-xs text-slate-500" x-text="new Date(oc.criado_em).toLocaleDateString('pt-BR')"></p>
    </div>
    <div class="flex items-center gap-2">
      <span class="text-xs px-2 py-0.5 rounded-full"
            :class="oc.processada ? 'bg-green-900/50 text-green-400' : 'bg-yellow-900/50 text-yellow-400'"
            x-text="oc.processada ? 'Processada' : 'Pendente'"></span>
      <a :href="oc.arquivo_pdf_url" target="_blank" rel="noopener"
         class="btn btn-secondary text-xs px-3 py-1">Abrir PDF</a>
    </div>
  </div>
</div>
```

**Diferença:** o `<span>` do chip e o `<a>` do botão ficam dentro de um `div.flex.items-center.gap-2`.
O padrão de `btn btn-secondary text-xs px-3 py-1` + `:href="oc.arquivo_pdf_url"` já existe nos resultados de busca (linha 88–90 do mesmo arquivo) — é cópia direta.

**Step 2: Verificar visualmente no browser**

1. Abrir `http://localhost:8000/#ocorrencia-upload`
2. Se não houver ocorrências cadastradas, cadastrar uma via o formulário de upload
3. Confirmar que cada item da lista exibe: `[numero_ocorrencia] [data] ... [chip] [Abrir PDF]`
4. Clicar em "Abrir PDF" → deve abrir o PDF em nova aba

**Step 3: Commit**

```bash
git add frontend/js/pages/ocorrencia-upload.js
git commit -m "feat(frontend): adicionar botão Abrir PDF na lista de ocorrências recentes"
```
