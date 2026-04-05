# Exibir Idade na Ficha do Abordado — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir a idade calculada automaticamente ao lado da data de nascimento na ficha do abordado.

**Architecture:** Adicionar o método `calcularIdade(dataNascimento)` no objeto Alpine.js de `pessoaDetalhePage` e usá-lo nos dois locais onde a data de nascimento é renderizada (ficha principal e preview de busca). Nenhuma mudança de API ou backend necessária.

**Tech Stack:** Alpine.js (x-text expressions), JavaScript vanilla, frontend PWA.

---

### Task 1: Adicionar método `calcularIdade` no componente Alpine

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:860` (logo após `_buscaTimer: null,`)

**Step 1: Localizar o ponto de inserção**

Abra `frontend/js/pages/pessoa-detalhe.js` e localize a linha:
```js
    _buscaTimer: null,
```
Ela fica em torno da linha 863. O método deve ser adicionado logo antes de `async load()` (linha ~887).

**Step 2: Adicionar o método no objeto retornado por `pessoaDetalhePage`**

Inserir após `_buscaTimer: null,` e antes de `// Edição de dados pessoais`:

```js
    calcularIdade(dataNascimento) {
      if (!dataNascimento) return null;
      const hoje = new Date();
      const nasc = new Date(dataNascimento + 'T00:00:00');
      let idade = hoje.getFullYear() - nasc.getFullYear();
      const m = hoje.getMonth() - nasc.getMonth();
      if (m < 0 || (m === 0 && hoje.getDate() < nasc.getDate())) idade--;
      return idade;
    },
```

**Step 3: Verificar manualmente no browser**

Abra o console do navegador na ficha de qualquer pessoa e execute:
```js
document.querySelector('[x-data]').__x.$data.calcularIdade('2007-10-24')
```
Resultado esperado: `18` (ou `19` se após 24/10/2026).

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): adicionar método calcularIdade no componente Alpine"
```

---

### Task 2: Exibir idade na ficha principal (seção Dados Pessoais)

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:56`

**Step 1: Localizar o span atual**

Linha ~56:
```html
<span style="color: var(--color-text-muted); margin-left: 0.25rem;" x-text="pessoa.data_nascimento ? new Date(pessoa.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '—'"></span>
```

**Step 2: Substituir pelo span com idade**

```html
<span style="color: var(--color-text-muted); margin-left: 0.25rem;"
      x-text="pessoa.data_nascimento
        ? new Date(pessoa.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') + ' (' + calcularIdade(pessoa.data_nascimento) + ' anos)'
        : '—'"></span>
```

**Step 3: Verificar no browser**

Na ficha de um abordado com data de nascimento preenchida, o campo deve mostrar:
> Nascimento: 24/10/2007 (18 anos)

Para abordado sem data de nascimento, deve mostrar `—` (sem quebrar).

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): exibir idade ao lado da data de nascimento na ficha"
```

---

### Task 3: Exibir idade no preview de busca de vínculo

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:382-384`

**Step 1: Localizar o parágrafo atual**

Linha ~382:
```html
<p x-show="pessoaPreview?.data_nascimento"
   style="font-size: 0.75rem; color: var(--color-text-muted); margin: 0;"
   x-text="'Nascimento: ' + (pessoaPreview?.data_nascimento ? new Date(pessoaPreview.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '')"></p>
```

**Step 2: Substituir pelo parágrafo com idade**

```html
<p x-show="pessoaPreview?.data_nascimento"
   style="font-size: 0.75rem; color: var(--color-text-muted); margin: 0;"
   x-text="'Nascimento: ' + (pessoaPreview?.data_nascimento ? new Date(pessoaPreview.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') + ' (' + calcularIdade(pessoaPreview.data_nascimento) + ' anos)' : '')"></p>
```

**Step 3: Verificar no browser**

No modal de adicionar vínculo, ao buscar e selecionar uma pessoa com data de nascimento, o preview deve mostrar:
> Nascimento: 24/10/2007 (18 anos)

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): exibir idade no preview de busca de vínculo"
```

---

## Checklist de validação final

- [ ] Ficha de pessoa com data de nascimento mostra "DD/MM/AAAA (X anos)"
- [ ] Ficha de pessoa **sem** data de nascimento mostra "—" sem erro
- [ ] Preview no modal de vínculo mostra a idade corretamente
- [ ] Não há erros no console do browser
- [ ] A idade vira corretamente na virada de aniversário (lógica de ajuste de mês/dia)
