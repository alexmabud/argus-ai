# Coabordados no Histórico de Abordagens — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir avatares clicáveis das pessoas coabordadas em cada card do Histórico de Abordagens na ficha de pessoa, com modal de preview ao clicar.

**Architecture:** Mudança puramente frontend em `pessoa-detalhe.js`. O backend já retorna `AbordagemDetail.pessoas` com todos os dados necessários. Adiciona estado `pessoaPreview` ao Alpine, fileira de avatares em cada card de abordagem (excluindo a pessoa atual), e modal overlay com dados básicos + botão para navegar à ficha completa.

**Tech Stack:** Alpine.js (x-data/x-show/x-for), Tailwind CSS, HTML inline no JS (padrão existente do projeto)

---

## Contexto do Código

- **Arquivo principal:** `frontend/js/pages/pessoa-detalhe.js`
- **Função de renderização:** `renderPessoaDetalhe(appState)` — retorna HTML como string template literal
- **Função de estado Alpine:** `pessoaDetalhePage(pessoaId)` — retorna objeto com estado e métodos
- **Histórico de Abordagens:** linhas 183-222 do arquivo — `<template x-for="(ab, idx) in abordagens">`
- **Modal de foto ampliada existente (referência de padrão):** linhas 92-95 — usa `x-show="fotoAmpliada"` com `@click="fotoAmpliada = null"`
- **Navegação para ficha:** método `viewPessoa(id)` — já existe, linhas 439-445
- **Os dados disponíveis em cada `ab`:** `ab.id`, `ab.pessoas` (array de PessoaRead com `id`, `nome`, `apelido`, `cpf_masked`, `data_nascimento`, `foto_principal_url`), `ab.veiculos`, `ab.endereco_texto`, `ab.observacao`
- **`pessoaId`** é a variável JS (número) do ID da pessoa atual — disponível no escopo da função `pessoaDetalhePage(pessoaId)`

> ⚠️ Não há testes automatizados para frontend neste projeto. Validação é manual no browser.

---

### Task 1: Adicionar estado `pessoaPreview` ao Alpine

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js` (função `pessoaDetalhePage`, bloco de estado inicial)

**Contexto:** A função `pessoaDetalhePage(pessoaId)` retorna um objeto literal com o estado Alpine. Atualmente tem `fotoAmpliada: null` para o modal de foto. Seguir o mesmo padrão.

**Step 1: Localizar o bloco de estado na função `pessoaDetalhePage`**

Abrir `frontend/js/pages/pessoa-detalhe.js`, linha 264. O objeto retornado começa assim:
```js
return {
    pessoa: null,
    fotos: [],
    fotosVeiculos: [],
    abordagens: [],
    veiculos: [],
    fotoAmpliada: null,
    loading: true,
    ...
```

**Step 2: Adicionar `pessoaPreview: null` após `fotoAmpliada: null`**

```js
    fotoAmpliada: null,
    pessoaPreview: null,
```

**Step 3: Verificar no browser que nada quebrou**

Abrir a ficha de qualquer pessoa — deve carregar normalmente sem erros no console.

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(pessoa-detalhe): adicionar estado pessoaPreview para modal de coabordados"
```

---

### Task 2: Adicionar fileira de avatares de coabordados em cada card de abordagem

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js` (função `renderPessoaDetalhe`, seção Histórico de Abordagens)

**Contexto:** O bloco de cada abordagem fica dentro de `<template x-for="(ab, idx) in abordagens">` (linha 189). Atualmente termina com os veículos (linha ~218). Adicionar a fileira de coabordados logo após o bloco de veículos, dentro do mesmo `<div>` do card.

**Step 1: Localizar o fim do bloco de veículos na abordagem**

No `renderPessoaDetalhe`, encontrar este trecho (linha ~210-219):
```html
                  <!-- Veículos nesta abordagem -->
                  <div x-show="ab.veiculos?.length > 0" class="space-y-1">
                    <template x-for="av in ab.veiculos" :key="av.id">
                      <div class="text-xs text-slate-400">
                        <span class="text-slate-500 font-medium">Veículo Vinculado à Abordagem:</span>
                        <span class="ml-1" x-text="[formatPlaca(av.placa), av.modelo, av.cor, av.ano].filter(Boolean).join(' · ')"></span>
                      </div>
                    </template>
                  </div>
                </div>
              </template>
```

**Step 2: Inserir o bloco de coabordados ANTES do `</div>` que fecha o card (antes do `</template>`)**

Inserir após o `</div>` que fecha o bloco de veículos:

```html
                  <!-- Coabordados nesta abordagem -->
                  <template x-if="ab.pessoas?.filter(p => p.id !== ${pessoaId}).length > 0">
                    <div class="pt-1">
                      <p class="text-[10px] font-semibold text-slate-500 mb-1.5">Abordados juntos:</p>
                      <div class="flex flex-wrap gap-3">
                        <template x-for="p in ab.pessoas.filter(pp => pp.id !== ${pessoaId})" :key="p.id">
                          <div @click.stop="pessoaPreview = p"
                               class="flex flex-col items-center gap-1 cursor-pointer w-10">
                            <!-- Com foto -->
                            <template x-if="p.foto_principal_url">
                              <img :src="p.foto_principal_url"
                                   class="w-10 h-10 rounded-full object-cover border-2 border-slate-600 hover:border-blue-400 transition-colors"
                                   loading="lazy">
                            </template>
                            <!-- Sem foto: ícone silhueta -->
                            <template x-if="!p.foto_principal_url">
                              <div class="w-10 h-10 rounded-full bg-slate-700 border-2 border-slate-600 hover:border-blue-400 transition-colors flex items-center justify-center text-slate-400">
                                <svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                                </svg>
                              </div>
                            </template>
                            <span class="text-[9px] text-slate-400 text-center leading-tight w-10 truncate"
                                  x-text="p.nome.split(' ')[0]"></span>
                          </div>
                        </template>
                      </div>
                    </div>
                  </template>
```

> **Nota:** O `${pessoaId}` é interpolado no template literal da função — é um número JS, não uma string Alpine. Isso é correto e segue o padrão existente no arquivo (ex: linha 26: `pessoaDetalhePage(${pessoaId})`).

**Step 3: Verificar no browser**

1. Abrir a ficha de uma pessoa que tem abordagem com mais de 1 pessoa
2. Verificar que aparecem os avatares das outras pessoas abordadas juntas
3. Verificar que a pessoa atual NÃO aparece como coabordada
4. Verificar que avatares sem foto mostram o ícone silhueta
5. Verificar que o nome (primeiro nome) aparece embaixo do avatar

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(pessoa-detalhe): exibir avatares de coabordados no histórico de abordagens"
```

---

### Task 3: Adicionar modal overlay de preview da pessoa coabordada

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js` (função `renderPessoaDetalhe`, após o modal de foto ampliada)

**Contexto:** O modal de foto ampliada existe nas linhas 92-95 e usa o padrão `x-show` + `@click` para fechar. O novo modal segue exatamente o mesmo padrão. Inserir logo após o `</div>` do modal de foto ampliada (linha ~95).

**Step 1: Localizar o modal de foto ampliada**

```html
          <!-- Foto ampliada (modal) -->
          <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
               class="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
            <img :src="fotoAmpliada" class="max-w-full max-h-full rounded-lg">
          </div>
```

**Step 2: Inserir o modal de preview logo após esse bloco**

```html
          <!-- Modal preview de pessoa coabordada -->
          <div x-show="pessoaPreview" x-cloak
               @click.self="pessoaPreview = null"
               class="fixed inset-0 bg-black/60 z-50 flex items-end justify-center sm:items-center p-4">
            <div @click="viewPessoa(pessoaPreview.id)"
                 class="bg-slate-800 border border-slate-600 rounded-2xl p-5 w-full max-w-sm space-y-3 cursor-pointer hover:border-blue-500 transition-colors">
              <!-- Foto ou ícone -->
              <div class="flex justify-center">
                <template x-if="pessoaPreview?.foto_principal_url">
                  <img :src="pessoaPreview.foto_principal_url"
                       class="w-20 h-20 rounded-full object-cover border-2 border-slate-500">
                </template>
                <template x-if="!pessoaPreview?.foto_principal_url">
                  <div class="w-20 h-20 rounded-full bg-slate-700 border-2 border-slate-500 flex items-center justify-center text-slate-400">
                    <svg class="w-10 h-10" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                    </svg>
                  </div>
                </template>
              </div>
              <!-- Dados -->
              <div class="text-center space-y-1">
                <p class="text-base font-bold text-slate-100" x-text="pessoaPreview?.nome"></p>
                <p x-show="pessoaPreview?.apelido"
                   class="text-sm text-yellow-400 font-medium"
                   x-text="'Vulgo: ' + pessoaPreview?.apelido"></p>
                <p x-show="pessoaPreview?.cpf_masked"
                   class="text-xs text-slate-400"
                   x-text="'CPF: ' + pessoaPreview?.cpf_masked"></p>
                <p x-show="pessoaPreview?.data_nascimento"
                   class="text-xs text-slate-400"
                   x-text="'Nascimento: ' + (pessoaPreview?.data_nascimento ? new Date(pessoaPreview.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR') : '')"></p>
              </div>
              <!-- Botão -->
              <div class="pt-1">
                <div class="w-full text-center text-sm font-semibold text-blue-400 py-2 rounded-lg border border-blue-500/40 bg-blue-500/10">
                  Ver ficha completa →
                </div>
              </div>
            </div>
          </div>
```

> **Nota de UX:** `items-end` em mobile (drawer que sobe da base) e `sm:items-center` em telas maiores (modal centralizado). O clique em qualquer parte do card navega para a ficha. O clique fora do card (`@click.self`) fecha o modal.

**Step 3: Verificar no browser**

1. Clicar em um avatar de coabordado → modal deve aparecer
2. Verificar que dados (nome, apelido, CPF, nascimento) aparecem corretamente
3. Clicar fora do card → modal fecha, permanece na ficha atual
4. Abrir modal novamente → clicar no card → navega para ficha da pessoa coabordada
5. Verificar que modal não aparece ao carregar a página (estado inicial `null`)

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(pessoa-detalhe): adicionar modal preview de pessoa coabordada"
```

---

## Verificação Final

Após as 3 tasks, testar o fluxo completo:

1. Ir para Consulta → buscar pessoa que tenha abordagens com múltiplas pessoas
2. Abrir ficha → rolar até Histórico de Abordagens
3. Verificar avatares de coabordados em cada card de abordagem coletiva
4. Verificar que abordagens com somente 1 pessoa (a própria) não mostram a seção
5. Clicar avatar → verificar modal com dados corretos
6. Clicar fora → fechar modal
7. Clicar no card do modal → navegar para ficha do coabordado
8. Verificar que o botão "← Voltar" retorna corretamente

---

## Checklist de Qualidade

- [ ] Pessoa atual não aparece como coabordada dela mesma
- [ ] Abordagens solo não exibem seção de coabordados
- [ ] Avatar sem foto mostra ícone silhueta (não quebra)
- [ ] Modal fecha ao clicar fora
- [ ] Modal abre a ficha correta ao clicar dentro
- [ ] Não há erros no console JavaScript
- [ ] Layout funciona em mobile (tela estreita)
