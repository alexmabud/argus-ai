# Vínculo Veículo→Abordado: UX + Validação — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Tornar o vínculo veículo→abordado obrigatório no formulário de nova abordagem, com card visual claro e bloqueio no submit.

**Architecture:** Mudanças puramente frontend em dois arquivos JS. Sem alterações de backend ou API. A validação ocorre no método `submit()` antes de qualquer request, tanto online quanto offline.

**Tech Stack:** Alpine.js, Tailwind CSS (via classes utilitárias existentes no projeto)

---

### Task 1: Formatar placa no `getLabel()` do autocomplete

**Arquivo:**
- Modificar: `frontend/js/components/autocomplete.js:89-91`

**Contexto:**
A função `formatarPlaca()` já existe globalmente em `frontend/js/app.js` e insere o traço automaticamente (ex: `ABC1234` → `ABC-1234`). O `getLabel()` para veículo precisa usá-la ao exibir a placa nas tags e no dropdown.

**Passo 1: Aplicar a mudança**

Em `autocomplete.js`, substituir o bloco do tipo `veiculo` em `getLabel()`:

```js
// ANTES (linha 89-91):
if (tipo === "veiculo") {
  return item.modelo ? `${item.placa} — ${item.modelo}` : item.placa;
}

// DEPOIS:
if (tipo === "veiculo") {
  const placa = formatarPlaca(item.placa || "");
  return item.modelo ? `${placa} — ${item.modelo}` : placa;
}
```

**Passo 2: Testar manualmente**

1. Abrir o app em `http://localhost:8000`
2. Ir em Nova Abordagem → campo "Veículo envolvido"
3. Buscar uma placa (ex: `ABC1234` ou `ABC-1234`)
4. Confirmar que a tag exibe `ABC-1234` com o traço

**Passo 3: Commit**

```bash
git add frontend/js/components/autocomplete.js
git commit -m "fix(frontend): formatar placa com traço no getLabel do autocomplete"
```

---

### Task 2: Redesenhar a seção de vínculo veículo→abordado

**Arquivo:**
- Modificar: `frontend/js/pages/abordagem-nova.js:247-266` (bloco HTML do vínculo)

**Contexto:**
O bloco atual (dentro da seção "Veículo envolvido na abordagem") fica dentro de um `x-show` condicional e exibe botões pequenos com apenas o primeiro nome do abordado. Precisamos transformá-lo em um card visual por veículo, com borda colorida dinâmica.

**Passo 1: Substituir o bloco HTML do vínculo**

Localizar o bloco entre os comentários `<!-- Vínculo veículo → abordado -->` e o botão `<!-- Botão para cadastrar sem buscar -->` (linhas 247–266). Substituir pelo novo HTML:

```html
<!-- Vínculo veículo → abordado -->
<div x-show="veiculosSelecionados.length > 0 && pessoasSelecionadas.length > 0"
     class="pt-1 space-y-2">
  <template x-for="v in veiculosSelecionados" :key="v.id">
    <div class="rounded-lg border p-3 space-y-2 transition-colors"
         :class="veiculoPorPessoa[v.id]
           ? 'border-green-500/60 bg-green-900/10'
           : 'border-yellow-500/60 bg-yellow-900/10'"
         :id="'vinculo-' + v.id">

      <!-- Cabeçalho: placa + status -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-slate-400 text-base">🚗</span>
          <div>
            <span class="font-mono font-bold text-base text-slate-100"
                  x-text="formatarPlaca(v.placa || '')"></span>
            <span x-show="v.modelo || v.cor"
                  class="block text-xs text-slate-400"
                  x-text="[v.modelo, v.cor].filter(Boolean).join(' — ')"></span>
          </div>
        </div>
        <span x-show="veiculoPorPessoa[v.id]"
              class="text-green-400 text-sm font-medium">✓ vinculado</span>
        <span x-show="!veiculoPorPessoa[v.id]"
              class="text-yellow-400 text-xs">⚠ sem vínculo</span>
      </div>

      <!-- Seleção do condutor -->
      <div>
        <p class="text-xs text-slate-400 mb-2">Quem estava no veículo?</p>
        <div class="flex flex-wrap gap-2">
          <template x-for="p in pessoasSelecionadas" :key="p.id">
            <button type="button"
                    @click="veiculoPorPessoa = {...veiculoPorPessoa, [v.id]: veiculoPorPessoa[v.id] === p.id ? null : p.id}"
                    class="text-sm px-3 py-2 rounded-lg border transition-colors"
                    :class="veiculoPorPessoa[v.id] === p.id
                      ? 'bg-blue-600 border-blue-500 text-white font-medium'
                      : 'bg-slate-700 border-slate-600 text-slate-300 hover:bg-slate-600'">
              <span x-text="p.nome"></span>
            </button>
          </template>
        </div>
      </div>
    </div>
  </template>
</div>
```

**Passo 2: Expor `formatarPlaca` ao Alpine**

A função `formatarPlaca` é global (definida em `app.js`), então pode ser chamada diretamente em expressões Alpine com `:x-text`. Não precisa de mudança extra — só verificar que funciona no passo de teste.

**Passo 3: Testar manualmente**

1. Ir em Nova Abordagem
2. Adicionar uma pessoa e um veículo
3. Confirmar que o card aparece com borda amarela e ícone ⚠
4. Clicar no nome da pessoa — confirmar que a borda vira verde e aparece "✓ vinculado"
5. Clicar novamente — confirmar que desvinccula (toggle) e volta ao amarelo
6. Verificar que a placa aparece no formato `ABC-1234` com `font-mono`
7. Verificar que o nome completo da pessoa aparece no botão (não apenas o primeiro nome)

**Passo 4: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "feat(frontend): redesign card vínculo veículo→abordado com borda dinâmica"
```

---

### Task 3: Validação no `submit()` — bloquear sem vínculo

**Arquivo:**
- Modificar: `frontend/js/pages/abordagem-nova.js` — método `submit()` (linha ~634)

**Contexto:**
O método `submit()` começa com `if (this.submitting) return;`. Precisamos adicionar validação logo após, antes de qualquer request. O state `veiculosPorPessoa` é um objeto `{ [veiculoId]: pessoaId | null }`.

**Passo 1: Adicionar validação no início de `submit()`**

Localizar o início do método `submit()`:

```js
async submit() {
  if (this.submitting) return;
  this.submitting = true;
  this.erro = null;
  this.sucesso = null;
```

Substituir por:

```js
async submit() {
  if (this.submitting) return;

  // Validar que todo veículo está vinculado a um abordado
  for (const v of this.veiculosSelecionados) {
    if (!this.veiculoPorPessoa[v.id]) {
      const placa = formatarPlaca(v.placa || "");
      this.erro = `Vincule o veículo ${placa} a um dos abordados antes de registrar.`;
      const cardEl = document.getElementById(`vinculo-${v.id}`);
      if (cardEl) cardEl.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
  }

  this.submitting = true;
  this.erro = null;
  this.sucesso = null;
```

**Passo 2: Testar manualmente — caminho do erro**

1. Adicionar uma pessoa e um veículo, mas NÃO vincular
2. Clicar em "Registrar Abordagem"
3. Confirmar que:
   - A abordagem NÃO é enviada
   - Aparece mensagem de erro com a placa formatada
   - A página rola até o card do veículo sem vínculo

**Passo 3: Testar manualmente — caminho feliz**

1. Adicionar pessoa + veículo e vincular (clicar no nome da pessoa no card)
2. Clicar em "Registrar Abordagem"
3. Confirmar que a abordagem é registrada normalmente

**Passo 4: Testar edge case — veículo sem pessoa (não deveria acontecer, mas testar)**

Confirmar que se `veiculosSelecionados` está vazio, o loop não bloqueia nada.

**Passo 5: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "feat(frontend): bloquear submit se veículo não vinculado a abordado"
```

---

## Resumo dos commits esperados

```
fix(frontend): formatar placa com traço no getLabel do autocomplete
feat(frontend): redesign card vínculo veículo→abordado com borda dinâmica
feat(frontend): bloquear submit se veículo não vinculado a abordado
```

## Verificação final

Após as três tasks, conferir:

- [ ] Placa exibe `ABC-1234` nas tags do autocomplete de veículo
- [ ] Card de vínculo aparece com borda amarela ⚠ quando sem vínculo
- [ ] Card de vínculo aparece com borda verde ✓ quando vinculado
- [ ] Nome completo do abordado aparece nos botões de seleção
- [ ] Submit bloqueado com mensagem clara se veículo sem vínculo
- [ ] Scroll automático até o card problemático
- [ ] Submit funciona normalmente quando tudo vinculado
