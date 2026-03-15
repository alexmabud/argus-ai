# Design: Modal de Sucesso ao Registrar Abordagem

**Data:** 2026-03-15
**Status:** Aprovado

## Problema

Após registrar uma abordagem, o sistema exibe apenas um texto simples (`<p>`) abaixo do botão informando o sucesso. O usuário não percebe com clareza que a operação foi concluída, e não tem uma ação explícita para continuar o trabalho (nova abordagem ou voltar ao início).

## Objetivo

Exibir um modal de confirmação visualmente prominente logo após o sucesso do registro, com duas ações claras:
1. Registrar nova abordagem
2. Ir para a página inicial

## Decisão de Design

**Opção escolhida: Modal overlay inline (Alpine.js)**

Modal de sobreposição embutido diretamente no template `renderAbordagemNova()`, controlado por estado no componente `abordagemForm()`.

## Comportamento

- Após submit bem-sucedido (online ou offline), o modal aparece por cima do formulário
- O modal não pode ser fechado clicando fora (forçar escolha explícita)
- **"Registrar nova abordagem"** → reseta o formulário e fecha o modal (permanece na mesma página)
- **"Ir para página inicial"** → navega para `home` via `navigate('home')`
- A mensagem de sucesso exibida no modal varia:
  - Online: "Abordagem #123 registrada com sucesso."
  - Offline: "Abordagem salva na fila offline. Será sincronizada automaticamente."

## Alterações nos Arquivos

### `frontend/js/pages/abordagem-nova.js`

**Estado adicional em `abordagemForm()`:**
- `showSuccessModal: false` — controla visibilidade do modal
- `abordagemId: null` — ID da abordagem registrada (para exibição)

**Lógica de submit:**
- Remover `this.sucesso = ...` inline
- Após sucesso: `this.showSuccessModal = true; this.abordagemId = result.id`
- Mover o reset do formulário para um método separado `resetForm()` chamado pelo botão "Nova abordagem"

**Template `renderAbordagemNova()`:**
- Remover `<p x-show="sucesso"...>` abaixo do submit
- Adicionar bloco de modal antes do fechamento do `</div>` principal:
  - Overlay: `fixed inset-0 z-50 bg-black/70 flex items-center justify-center`
  - Card: `bg-slate-800 rounded-xl p-6 mx-4 max-w-sm w-full space-y-4`
  - Ícone de check verde
  - Título "Abordagem registrada!"
  - Mensagem dinâmica com ID ou status offline
  - Botão primário "Registrar nova abordagem"
  - Botão secundário "Ir para página inicial"

## Impacto

- Apenas 1 arquivo modificado: `frontend/js/pages/abordagem-nova.js`
- Sem dependências novas
- Sem breaking changes
