# Remover Redundâncias no Histórico de Abordagens

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remover dois elementos redundantes do card de histórico de abordagens na tela de detalhe de pessoa.

**Architecture:** Mudanças puramente frontend em dois arquivos:
1. `abordagem-nova.js` — parar de appendar texto de vínculos na observação ao criar abordagem
2. `pessoa-detalhe.js` — remover "Data da Abordagem" redundante e filtrar texto de vínculos antigos na exibição da observação

**Tech Stack:** HTML + Alpine.js (renderização de template no frontend)

---

## Contexto dos problemas

### Problema 1: "Data da Abordagem" duplicada
No card de histórico (`pessoa-detalhe.js:194-195`), aparece "Data da Abordagem: 08/03/2026, 12:37:12". O lado direito do mesmo card já exibe "Cadastrada em 08/03/2026 às 12:37" — informação idêntica, redundante.

### Problema 2: Veículo aparecendo na Observação
Ao criar uma abordagem, `abordagem-nova.js:643-655` appenda automaticamente o texto `"Vínculos: EEE5555 → Teste E"` ao campo de observação antes de salvar. Isso é redundante porque o sistema já armazena a relação veiculo↔pessoa na estrutura de dados e exibe em "Veículo Vinculado à Abordagem" no mesmo card. O texto fica salvo no banco, então a correção tem duas partes: parar de gerar e filtrar na exibição.

---

### Task 1: Remover "Data da Abordagem" do cabeçalho do card

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:194-195`

**Step 1: Remover o span de Data da Abordagem**

Em `frontend/js/pages/pessoa-detalhe.js`, remover as linhas 194-195:

```html
<!-- REMOVER estas duas linhas: -->
<span x-show="ab.data_hora" class="text-xs text-slate-400 ml-2"
      x-text="'Data da Abordagem: ' + new Date(ab.data_hora).toLocaleString('pt-BR')"></span>
```

Resultado — o `<div>` do cabeçalho ficará:

```html
<div class="flex items-start justify-between gap-2">
  <div>
    <span class="text-xs font-medium text-blue-400" x-text="'#' + ab.id"></span>
  </div>
  <span x-show="ab.criado_em" class="text-xs text-slate-500 shrink-0"
        x-text="'Cadastrada em ' + new Date(ab.criado_em).toLocaleDateString('pt-BR') + ' às ' + new Date(ab.criado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})"></span>
</div>
```

**Step 2: Verificar no browser**

Abrir a tela de detalhe de uma pessoa com abordagens. Confirmar que o card mostra apenas `#id` e "Cadastrada em ...", sem "Data da Abordagem".

**Step 3: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): remover 'Data da Abordagem' redundante do histórico de abordagens"
```

---

### Task 2: Parar de appendar vínculos na observação ao criar abordagem

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js:643-655`

**Step 1: Remover o bloco de montagem de vínculos**

Em `frontend/js/pages/abordagem-nova.js`, remover as linhas 643-655:

```javascript
// REMOVER este bloco inteiro:
// Montar nota de vínculos veículo → abordado na observação
const vinculos = Object.entries(this.veiculoPorPessoa)
  .filter(([vId, pId]) => pId && this.veiculoIds.includes(parseInt(vId)))
  .map(([vId, pId]) => {
    const veiculo = this.veiculosSelecionados.find((v) => v.id === parseInt(vId));
    const pessoa = this.pessoasSelecionadas.find((p) => p.id === pId);
    return veiculo && pessoa ? `${veiculo.placa} → ${pessoa.nome}` : null;
  })
  .filter(Boolean);
let obsTexto = this.observacao || "";
if (vinculos.length > 0) {
  obsTexto = (obsTexto ? obsTexto + "\n" : "") + "Vínculos: " + vinculos.join(", ");
}
```

Substituir pela linha simples:

```javascript
const obsTexto = this.observacao || "";
```

E ajustar a linha do payload logo abaixo (já referencia `obsTexto`, não precisa mudar):

```javascript
observacao: obsTexto || null,
```

**Step 2: Verificar no browser**

Criar uma nova abordagem com veículo vinculado. Confirmar que o campo observação salvo **não** contém "Vínculos: ...".

**Step 3: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "feat(frontend): remover append automático de vínculos veículo no campo observação"
```

---

### Task 3: Filtrar texto de vínculos antigos na exibição da Observação

**Contexto:** Registros já salvos no banco têm o texto "Vínculos: ..." no campo `observacao`. Esta task filtra esse texto na exibição para que não apareça na tela de consulta.

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:207-210`

**Step 1: Substituir exibição direta por versão filtrada**

Em `frontend/js/pages/pessoa-detalhe.js`, o bloco atual (linhas 206-210):

```html
<!-- Observação -->
<div x-show="ab.observacao" class="text-xs">
  <span class="text-slate-500 font-medium">Observação:</span>
  <span class="text-slate-300 ml-1" x-text="ab.observacao"></span>
</div>
```

Substituir por:

```html
<!-- Observação (filtra linha de vínculos auto-gerada) -->
<div x-show="ab.observacao?.split('\n').filter(l => !l.startsWith('Vínculos:')).join('\n').trim()" class="text-xs">
  <span class="text-slate-500 font-medium">Observação:</span>
  <span class="text-slate-300 ml-1"
        x-text="ab.observacao?.split('\n').filter(l => !l.startsWith('Vínculos:')).join('\n').trim()"></span>
</div>
```

Isso filtra a linha "Vínculos: ..." de registros antigos preservando qualquer texto real de observação que o policial tenha digitado.

**Step 2: Verificar no browser**

- Abrir detalhe de pessoa com abordagem antiga (que tem "Vínculos:" na observação) → campo Observação não deve aparecer ou deve aparecer sem a linha de vínculos
- Abrir detalhe de pessoa com abordagem que tem observação real → observação deve continuar aparecendo normalmente

**Step 3: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): filtrar linha 'Vínculos:' auto-gerada na exibição da observação"
```
