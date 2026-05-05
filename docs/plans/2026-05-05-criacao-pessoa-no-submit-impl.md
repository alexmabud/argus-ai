# Criação de Pessoa Somente no Submit da Abordagem — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adiar a criação da ficha de pessoa no banco para o momento em que a abordagem é finalizada, eliminando cadastros incompletos por abandono do formulário.

**Architecture:** Apenas frontend — `criarPessoa()` passa a salvar dados localmente com IDs temporários negativos (-1, -2, …). O `submit()` cria as pessoas na API antes de criar a abordagem, substituindo os IDs temporários pelos reais.

**Tech Stack:** Alpine.js (state reativo), `api.post()` (wrapper fetch), `parseDateBR()` (utilitário local)

---

### Task 1: Adicionar variáveis de estado para pessoas temporárias

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js:497-555` (bloco de estado em `abordagemForm()`)

**Step 1: Adicionar `novasPessoas` e `_tempIdCounter` ao estado**

Localizar o bloco de estado da seção `// Cadastro nova pessoa` (linha ~517) e adicionar após `cpfCadastroErro`:

```javascript
// Pessoas novas ainda não criadas no banco (criadas no submit)
novasPessoas: [],
_tempIdCounter: 0,
```

**Step 2: Verificar visualmente**

Confirmar que o objeto retornado por `abordagemForm()` tem as duas novas propriedades antes de `anEstadoId`.

---

### Task 2: Refatorar `criarPessoa()` para salvar localmente

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js:676-741`

**Step 1: Substituir o corpo de `criarPessoa()`**

Substituir completamente o método — de `async criarPessoa() {` até o `},` que fecha o bloco — pelo seguinte:

```javascript
criarPessoa() {
  const nome = this.novaPessoa.nome.trim();
  if (!nome) {
    this.erroPessoa = "Nome é obrigatório.";
    return;
  }

  if (this.novaPessoa.cpf.trim() && !validarCPF(this.novaPessoa.cpf)) {
    this.cpfCadastroErro = "CPF inválido";
    return;
  }

  this._tempIdCounter--;
  const tempId = this._tempIdCounter;

  const pessoaTemp = {
    id: tempId,
    nome,
    cpf: this.novaPessoa.cpf.trim() || null,
    data_nascimento: parseDateBR(this.novaPessoa.data_nascimento) || null,
    apelido: this.novaPessoa.apelido.trim() || null,
    nome_mae: this.novaPessoa.nome_mae.trim() || null,
    _endereco: this.novaPessoa.endereco.trim() || null,
    _estado_id: this.anEstadoId ? parseInt(this.anEstadoId) : null,
    _cidade_id: this.anCidadeId || null,
    _bairro_id: this.anBairroId || null,
  };

  this.novasPessoas.push(pessoaTemp);
  this.pessoaIds.push(tempId);
  this.pessoasSelecionadas.push(pessoaTemp);

  // Adicionar nas tags do autocomplete para exibição
  const autocompleteEl = this.$el.querySelector("[x-data*='autocompleteComponent']");
  if (autocompleteEl?._x_dataStack) {
    autocompleteEl._x_dataStack[0].selected.push(pessoaTemp);
  }

  // Reset formulário
  this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", nome_mae: "", endereco: "" };
  this.cpfCadastroErro = "";
  this.anEstadoId = null; this.anCidadeId = null; this.anCidadeTexto = "";
  this.anBairroId = null; this.anBairroTexto = "";
  this.showNovaPessoa = false;
  this.erroPessoa = null;
},
```

**Nota:** o método deixa de ser `async` pois não faz mais chamadas de API.

---

### Task 3: Sincronizar remoção de pessoas temporárias no listener

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js:584-593`

**Step 1: Atualizar o listener `pessoa-selected`**

Localizar o listener (dentro de `initForm()`):

```javascript
this.$el.addEventListener("pessoa-selected", (e) => {
  this.pessoaIds = e.detail.selected.map((s) => s.id);
  this.pessoasSelecionadas = e.detail.selected;
  // Buscar endereços das pessoas selecionadas
  for (const p of e.detail.selected) {
    if (!this.pessoaEnderecos[p.id]) {
      this.carregarEnderecos(p.id);
    }
  }
});
```

Substituir por:

```javascript
this.$el.addEventListener("pessoa-selected", (e) => {
  const currentIds = e.detail.selected.map((s) => s.id);
  this.pessoaIds = currentIds;
  this.pessoasSelecionadas = e.detail.selected;
  // Remover de novasPessoas qualquer entrada que foi desselecionada
  this.novasPessoas = this.novasPessoas.filter(p => currentIds.includes(p.id));
  // Buscar endereços apenas de pessoas já existentes no banco (id > 0)
  for (const p of e.detail.selected) {
    if (p.id > 0 && !this.pessoaEnderecos[p.id]) {
      this.carregarEnderecos(p.id);
    }
  }
});
```

---

### Task 4: Modificar `submit()` para criar pessoas antes da abordagem

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js:902-994`

**Step 1: Inserir bloco de criação de novas pessoas no início do `submit()`**

Localizar a linha após `this.submitting = true; this.erro = null;` (linha ~921) e inserir antes da geração do `client_id`:

```javascript
// Criar pessoas novas no banco antes de criar a abordagem
if (this.novasPessoas.length > 0) {
  try {
    for (const p of [...this.novasPessoas]) {
      const pessoaData = { nome: p.nome };
      if (p.cpf) pessoaData.cpf = p.cpf;
      if (p.data_nascimento) pessoaData.data_nascimento = p.data_nascimento;
      if (p.apelido) pessoaData.apelido = p.apelido;
      if (p.nome_mae) pessoaData.nome_mae = p.nome_mae;

      const pessoaCriada = await api.post("/pessoas/", pessoaData);

      if (p._endereco || p._estado_id || p._cidade_id) {
        await api.post(`/pessoas/${pessoaCriada.id}/enderecos`, {
          endereco: p._endereco || "-",
          estado_id: p._estado_id,
          cidade_id: p._cidade_id,
          bairro_id: p._bairro_id,
        });
      }

      // Substituir ID temporário pelo ID real
      const tempId = p.id;
      const realId = pessoaCriada.id;
      this.pessoaIds = this.pessoaIds.map(id => id === tempId ? realId : id);

      // Re-indexar foto da pessoa do ID temporário para o real
      if (this.fotosPessoas[tempId]) {
        this.fotosPessoas = { ...this.fotosPessoas, [realId]: this.fotosPessoas[tempId] };
        delete this.fotosPessoas[tempId];
      }
    }
    this.novasPessoas = [];
  } catch (err) {
    this.erro = err.message || "Erro ao cadastrar novo abordado.";
    this.submitting = false;
    return;
  }
}
```

---

### Task 5: Limpar `novasPessoas` e `_tempIdCounter` no `resetForm()`

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js:996-1023`

**Step 1: Adicionar reset das novas variáveis**

Dentro de `resetForm()`, após `this.showNovaPessoa = false;`, adicionar:

```javascript
this.novasPessoas = [];
this._tempIdCounter = 0;
```

---

### Task 6: Testar o fluxo manualmente

**Step 1: Subir ambiente local**
```bash
docker compose up
```

**Step 2: Fluxo de teste — novo abordado não finalizado**
1. Abrir `/abordagem-nova`
2. Buscar nome inexistente → clicar "+ Cadastrar novo abordado"
3. Preencher nome e clicar "Salvar e adicionar"
4. Verificar que a pessoa aparece na lista de abordados
5. Fechar/navegar para outra página **sem** finalizar a abordagem
6. Confirmar no banco (`SELECT * FROM pessoas ORDER BY id DESC LIMIT 5`) que nenhuma ficha foi criada

**Step 3: Fluxo de teste — finalizar a abordagem**
1. Repetir passos 1-4 acima
2. Preencher localização e clicar "Registrar abordagem"
3. Confirmar que a abordagem foi criada com sucesso
4. Confirmar no banco que a pessoa foi criada e vinculada à abordagem

**Step 4: Fluxo de teste — remover abordado temporário**
1. Adicionar novo abordado (fluxo acima)
2. Clicar × na tag para removê-lo
3. Verificar que desaparece da lista
4. Adicionar outro abordado real (via busca)
5. Finalizar abordagem — verificar que apenas o real aparece

**Step 5: Commit**
```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "feat(frontend): criar pessoa somente ao finalizar abordagem"
```
