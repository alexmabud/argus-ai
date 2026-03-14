# Cadastro de Pessoa via Consulta — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Permitir cadastrar uma pessoa diretamente na tela de Consulta, sem precisar criar uma abordagem.

**Architecture:** Mudança exclusivamente no frontend (`consulta.js`). Adiciona estado, método `criarPessoa()` e HTML do formulário inline ao `consultaPage()`. Reutiliza a mesma lógica e campos do formulário de pessoa em `abordagem-nova.js`. Após salvar, navega para `pessoa-detalhe` da pessoa criada.

**Tech Stack:** Alpine.js (estado/eventos), `api.post()` wrapper existente, `POST /pessoas/` + `POST /pessoas/{id}/enderecos` (backend já pronto).

---

### Task 1: Adicionar estado e método `criarPessoa()` ao `consultaPage()`

**Files:**
- Modify: `frontend/js/pages/consulta.js`

**Step 1: Adicionar variáveis de estado ao objeto retornado por `consultaPage()`**

Localizar o bloco de estado no início de `consultaPage()` (após `// Dados auxiliares`) e adicionar:

```js
// Cadastro nova pessoa
showCadastroPessoa: false,
novaPessoa: { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" },
salvandoPessoa: false,
erroCadastro: null,
```

**Step 2: Adicionar método `criarPessoa()` dentro do objeto de `consultaPage()`, antes do fechamento `}`**

```js
async criarPessoa() {
  const nome = this.novaPessoa.nome.trim();
  if (!nome) {
    this.erroCadastro = "Nome é obrigatório.";
    return;
  }

  this.salvandoPessoa = true;
  this.erroCadastro = null;

  try {
    const pessoaData = { nome };
    if (this.novaPessoa.cpf.trim()) pessoaData.cpf = this.novaPessoa.cpf.trim();
    if (this.novaPessoa.data_nascimento) pessoaData.data_nascimento = this.novaPessoa.data_nascimento;
    if (this.novaPessoa.apelido.trim()) pessoaData.apelido = this.novaPessoa.apelido.trim();

    const pessoa = await api.post("/pessoas/", pessoaData);

    const temEndereco = this.novaPessoa.endereco.trim()
      || this.novaPessoa.bairro.trim()
      || this.novaPessoa.cidade.trim()
      || this.novaPessoa.estado.trim();

    if (temEndereco) {
      await api.post(`/pessoas/${pessoa.id}/enderecos`, {
        endereco: this.novaPessoa.endereco.trim() || "-",
        bairro: this.novaPessoa.bairro.trim() || null,
        cidade: this.novaPessoa.cidade.trim() || null,
        estado: this.novaPessoa.estado.trim().toUpperCase() || null,
      });
    }

    // Reset e navegar para ficha
    this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" };
    this.showCadastroPessoa = false;
    showToast("Pessoa cadastrada com sucesso!", "success");
    this.viewPessoa(pessoa.id);
  } catch (err) {
    this.erroCadastro = err.message || "Erro ao cadastrar pessoa.";
  } finally {
    this.salvandoPessoa = false;
  }
},
```

**Step 3: Verificar manualmente no browser que não há erros de sintaxe JS**

Abrir o console do browser em `http://localhost:8000` após salvar o arquivo e confirmar que não há erros.

---

### Task 2: Adicionar HTML do formulário e botões na seção "Pessoa" de `consulta.js`

**Files:**
- Modify: `frontend/js/pages/consulta.js`

**Step 1: Adicionar botão "+ Nova Pessoa" no cabeçalho do card Pessoa**

Localizar a linha:
```html
<p class="text-sm font-semibold text-slate-300">Pessoa</p>
```

Substituir por:
```html
<div class="flex items-center justify-between">
  <p class="text-sm font-semibold text-slate-300">Pessoa</p>
  <button @click="showCadastroPessoa = !showCadastroPessoa; novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', endereco: '', bairro: '', cidade: '', estado: '' }; erroCadastro = null"
          class="text-xs text-blue-400 hover:text-blue-300">
    + Nova Pessoa
  </button>
</div>
```

**Step 2: Modificar mensagem "Nenhuma pessoa encontrada" para incluir botão contextual**

Localizar:
```html
<!-- Sem resultados pessoa -->
<p x-show="searched && !loadingPessoa && buscouPessoa && pessoasTexto.length === 0 && pessoasFoto.length === 0 && !fotoSearchDone"
   class="text-xs text-slate-500 pt-1">
  Nenhuma pessoa encontrada.
</p>
```

Substituir por:
```html
<!-- Sem resultados pessoa -->
<div x-show="searched && !loadingPessoa && buscouPessoa && pessoasTexto.length === 0 && pessoasFoto.length === 0 && !fotoSearchDone"
     class="pt-1">
  <p class="text-xs text-slate-500 inline">Nenhuma pessoa encontrada. </p>
  <button @click="showCadastroPessoa = true; if (query && !/^\d/.test(query)) novaPessoa.nome = query; else if (query) novaPessoa.cpf = query"
          class="text-xs text-blue-400 hover:text-blue-300 font-medium">
    Cadastrar
  </button>
</div>
```

**Step 3: Adicionar formulário inline de cadastro após o bloco "Sem resultados pessoa"**

Adicionar imediatamente após o bloco substituído acima (antes do `<!-- Spinner pessoa -->`):

```html
<!-- Formulário inline: cadastrar nova pessoa -->
<div x-show="showCadastroPessoa" x-cloak class="bg-slate-800/50 border border-slate-600 rounded-lg p-4 space-y-3 mt-2">
  <div class="flex items-center justify-between">
    <h3 class="text-sm font-medium text-slate-200">Cadastrar nova pessoa</h3>
    <button @click="showCadastroPessoa = false; novaPessoa = { nome: '', cpf: '', data_nascimento: '', apelido: '', endereco: '', bairro: '', cidade: '', estado: '' }; erroCadastro = null"
            class="text-slate-400 hover:text-white text-xs">Cancelar</button>
  </div>

  <div>
    <label class="block text-xs text-slate-400 mb-1">Nome *</label>
    <input type="text" x-model="novaPessoa.nome" placeholder="Nome completo" class="w-full">
  </div>

  <div>
    <label class="block text-xs text-slate-400 mb-1">CPF</label>
    <input type="text" :value="novaPessoa.cpf"
           @input="novaPessoa.cpf = formatarCPF($event.target.value)"
           placeholder="000.000.000-00" maxlength="14" inputmode="numeric" class="w-full">
  </div>

  <div class="grid grid-cols-2 gap-2">
    <div>
      <label class="block text-xs text-slate-400 mb-1">Data de nascimento</label>
      <input type="date" x-model="novaPessoa.data_nascimento" class="w-full">
    </div>
    <div>
      <label class="block text-xs text-slate-400 mb-1">Vulgo</label>
      <input type="text" x-model="novaPessoa.apelido" placeholder="Apelido" class="w-full">
    </div>
  </div>

  <div>
    <label class="block text-xs text-slate-400 mb-1">Endereço</label>
    <input type="text" x-model="novaPessoa.endereco" placeholder="Rua e número" class="w-full">
  </div>

  <div class="grid grid-cols-3 gap-2">
    <div>
      <label class="block text-xs text-slate-400 mb-1">Bairro</label>
      <input type="text" list="lista-bairros-c" x-model="novaPessoa.bairro" placeholder="Bairro" class="w-full">
    </div>
    <div>
      <label class="block text-xs text-slate-400 mb-1">Cidade</label>
      <input type="text" list="lista-cidades-c" x-model="novaPessoa.cidade" placeholder="Cidade" class="w-full">
    </div>
    <div>
      <label class="block text-xs text-slate-400 mb-1">Estado (UF)</label>
      <input type="text" list="lista-estados-c" x-model="novaPessoa.estado" placeholder="DF" maxlength="2" class="w-full uppercase">
    </div>
  </div>

  <button @click="criarPessoa()" class="btn btn-primary text-sm w-full"
          :disabled="salvandoPessoa || !novaPessoa.nome.trim()">
    <span x-show="!salvandoPessoa">Salvar pessoa</span>
    <span x-show="salvandoPessoa" class="flex items-center justify-center gap-2">
      <span class="spinner"></span> Salvando...
    </span>
  </button>
  <p x-show="erroCadastro" class="text-xs text-red-400" x-text="erroCadastro"></p>
</div>
```

**Nota:** Reutiliza as `<datalist>` `lista-bairros-c`, `lista-cidades-c`, `lista-estados-c` já existentes no card de endereço logo abaixo — sem duplicação.

**Step 4: Bump da versão no `index.html`**

Em `frontend/index.html`, localizar:
```html
<script src="/js/pages/consulta.js?v=4"></script>
```
Alterar para:
```html
<script src="/js/pages/consulta.js?v=5"></script>
```

**Step 5: Testar manualmente**

1. Abrir `http://localhost:8000` → Consulta
2. Confirmar que "+ Nova Pessoa" aparece no cabeçalho do card
3. Clicar em "+ Nova Pessoa" → formulário abre
4. Preencher nome e salvar → navega para ficha da pessoa
5. Buscar um nome que não existe → aparece "Nenhuma pessoa encontrada. [Cadastrar]"
6. Clicar "Cadastrar" → formulário abre com nome pré-preenchido
7. Salvar → navega para ficha da pessoa
8. Ir para "Nova Abordagem" → buscar a pessoa recém-criada pelo nome → confirmar que aparece no autocomplete

**Step 6: Commit**

```bash
git add frontend/js/pages/consulta.js frontend/index.html
git commit -m "feat(consulta): adicionar cadastro de pessoa standalone na tela de consulta"
```
