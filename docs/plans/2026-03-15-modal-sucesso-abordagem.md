# Modal de Sucesso ao Registrar Abordagem — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir um modal de confirmação visualmente prominente após o registro de uma abordagem, com opções de registrar nova abordagem ou ir para a página inicial.

**Architecture:** Modal overlay inline no componente Alpine.js `abordagemForm()` — controlado por estado booleano `showSuccessModal`. O reset do formulário é extraído para `resetForm()` chamado pelo botão "Nova abordagem". Navegação via `navigate('home')` no app root.

**Tech Stack:** Alpine.js (x-show, x-cloak), Tailwind CSS, PWA frontend

---

### Task 1: Adicionar estado do modal e extrair resetForm()

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js` (função `abordagemForm()`, linhas ~400-776)

**Step 1: Adicionar `showSuccessModal` e `abordagemId` ao estado inicial**

Localizar o bloco de estado em `abordagemForm()` (linha ~401) e adicionar após `sucesso: null,`:

```js
// Modal de sucesso
showSuccessModal: false,
abordagemId: null,
successMessage: null,
```

**Step 2: Extrair o reset do formulário para método `resetForm()`**

Após o método `submit()`, adicionar o novo método. O bloco de reset que está dentro do `try` do `submit()` (linhas ~755-768) deve ser extraído:

```js
resetForm() {
  this.clientId = null;
  this.observacao = "";
  this.pessoaIds = [];
  this.pessoasSelecionadas = [];
  this.fotosPessoas = {};
  this.pessoaEnderecos = {};
  this.novoEnderecoAberto = {};
  this.novoEnderecoData = {};
  this.veiculoIds = [];
  this.veiculosSelecionados = [];
  this.veiculoPorPessoa = {};
  this.fotosVeiculos = {};
  this.fotoVeiculoFile = null;
  this.showNovaPessoa = false;
  this.showNovoVeiculo = false;
  this.novaPessoa = { nome: "", cpf: "", data_nascimento: "", apelido: "", endereco: "", bairro: "", cidade: "", estado: "" };
  this.novoVeiculo = { placa: "", modelo: "", cor: "", ano: "" };
},
```

**Step 3: No método `submit()`, substituir o bloco de reset e `this.sucesso` pelo modal**

Substituir no bloco online (após uploads de fotos):
```js
// DE:
this.sucesso = `Abordagem #${result.id} registrada com sucesso!`;
// ... bloco de reset ...

// PARA:
this.abordagemId = result.id;
this.successMessage = `Abordagem #${result.id} registrada com sucesso.`;
this.resetForm();
this.showSuccessModal = true;
```

Substituir no bloco offline:
```js
// DE:
this.sucesso = "Abordagem salva na fila offline. Será sincronizada automaticamente.";
// ... bloco de reset ...

// PARA:
this.abordagemId = null;
this.successMessage = "Abordagem salva na fila offline. Será sincronizada automaticamente.";
this.resetForm();
this.showSuccessModal = true;
```

**Step 4: Verificar manualmente no browser**

Abrir a página de nova abordagem e verificar que o estado `showSuccessModal` existe no Alpine.js devtools (ou inspecionar `document.querySelector('[x-data]')._x_dataStack`).

**Step 5: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "refactor(abordagem): extrair resetForm e adicionar estado do modal de sucesso"
```

---

### Task 2: Adicionar o modal ao template HTML

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js` (função `renderAbordagemNova()`)

**Step 1: Remover a linha de sucesso inline do template**

Localizar e remover (está na seção "6. Submit", linha ~394):
```html
<p x-show="sucesso" class="text-sm text-green-400" x-text="sucesso"></p>
```

**Step 2: Adicionar o modal antes do fechamento do `</div>` principal**

Localizar o fechamento do template em `renderAbordagemNova()` (a linha que contém `</div>` antes do backtick de fechamento, linha ~396) e adicionar o modal antes dele:

```html
      <!-- Modal de sucesso -->
      <div x-show="showSuccessModal" x-cloak
           class="fixed inset-0 z-50 bg-black/70 flex items-center justify-center px-4">
        <div class="bg-slate-800 border border-slate-600 rounded-xl p-6 max-w-sm w-full space-y-5 shadow-2xl">

          <!-- Ícone de check -->
          <div class="flex justify-center">
            <div class="w-14 h-14 rounded-full bg-green-900/50 border border-green-500/50 flex items-center justify-center">
              <svg class="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          <!-- Título e mensagem -->
          <div class="text-center space-y-1">
            <h3 class="text-lg font-bold text-slate-100">Abordagem registrada!</h3>
            <p class="text-sm text-slate-400" x-text="successMessage"></p>
          </div>

          <!-- Ações -->
          <div class="space-y-2 pt-1">
            <button @click="showSuccessModal = false; captureGPS()"
                    class="btn btn-primary w-full">
              Registrar nova abordagem
            </button>
            <button @click="document.querySelector('[x-data]')._x_dataStack[0].navigate('home')"
                    class="w-full px-4 py-2 rounded-lg text-sm font-medium text-slate-300 hover:text-slate-100 hover:bg-slate-700 transition-colors">
              Ir para página inicial
            </button>
          </div>

        </div>
      </div>
```

**Nota:** O botão "Registrar nova abordagem" fecha o modal (`showSuccessModal = false`) e chama `captureGPS()` para já iniciar a captura de GPS para a próxima abordagem. O formulário já foi resetado pelo `resetForm()` no submit.

**Step 3: Testar manualmente**

1. Registrar uma abordagem com dados válidos
2. Confirmar que o modal aparece com ícone verde, título e mensagem correta
3. Clicar "Registrar nova abordagem": modal fecha, formulário está limpo, GPS inicia
4. Registrar outra abordagem e clicar "Ir para página inicial": navega para home

**Step 4: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "feat(abordagem): adicionar modal de sucesso ao registrar abordagem"
```

---

## Checklist de validação final

- [ ] Modal aparece após submit online com mensagem "Abordagem #N registrada com sucesso."
- [ ] Modal aparece após submit offline com mensagem de fila
- [ ] "Registrar nova abordagem" fecha modal e limpa formulário
- [ ] "Ir para página inicial" navega para home
- [ ] Modal não aparece ao entrar na página (apenas após submit)
- [ ] Sem regressão no submit com erro (modal não aparece em caso de falha)
