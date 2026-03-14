# Design: Coabordados no Histórico de Abordagens

**Data:** 2026-03-14
**Status:** Aprovado
**Escopo:** Frontend only — `frontend/js/pages/pessoa-detalhe.js`

---

## Problema

Ao consultar a ficha de uma pessoa, o Histórico de Abordagens mostra data, endereço, observação e veículos — mas não exibe as outras pessoas que foram abordadas juntas naquela mesma ocorrência. Isso impede o policial de identificar vínculos visuais entre abordados.

## Solução

Adicionar uma fileira de avatares clicáveis no card de cada abordagem, exibindo as demais pessoas abordadas junto. Ao clicar em um avatar, abre um modal preview com dados básicos da pessoa. Clicando no modal, navega para a ficha completa dela.

---

## Backend

**Sem alterações.** O endpoint `GET /pessoas/{id}/abordagens` já retorna `AbordagemDetail` com o campo `pessoas: list[PessoaRead]`, que inclui `id`, `nome`, `apelido`, `cpf_masked`, `data_nascimento` e `foto_principal_url`.

---

## Frontend — `pessoa-detalhe.js`

### 1. Novo estado Alpine

```js
pessoaPreview: null  // PessoaRead da pessoa coabordada selecionada; null = modal fechado
```

### 2. Fileira de coabordados (dentro do card de cada abordagem)

Renderizada após os veículos no `<template x-for="(ab, idx) in abordagens">`.

**Regras:**
- Filtrar `ab.pessoas` excluindo a pessoa atual (`p.id !== pessoaId`)
- Só renderizar a seção se `ab.pessoas` tiver ao menos 1 pessoa após o filtro
- Cada avatar:
  - **Com foto:** `<img>` circular 40×40px com `object-cover`
  - **Sem foto:** ícone SVG silhueta genérica (mesmo estilo da busca por foto)
  - Nome completo centralizado abaixo, `text-[10px]`, truncado com `truncate w-10`
  - Clique → `pessoaPreview = p`

### 3. Modal overlay de preview

Overlay fixo `z-50` com backdrop `bg-black/60`, aparece quando `pessoaPreview !== null`.

**Fechar:** clique fora do card central (`@click.self="pessoaPreview = null"`).

**Conteúdo do card central:**
```
[ foto 80×80px arredondada | ícone silhueta se sem foto ]
Nome completo             — text-base font-bold
Vulgo: <apelido>          — text-sm text-yellow-400 (só se existir)
CPF: ***.***.***-34       — text-xs text-slate-400 (só se existir)
Nascimento: DD/MM/AAAA    — text-xs text-slate-400 (só se existir)
[ Botão "Ver ficha completa" → viewPessoa(pessoaPreview.id) ]
```

Clicar no card inteiro também navega para a ficha (`@click="viewPessoa(pessoaPreview.id)"`).

---

## Fluxo de interação

```
Ficha da Pessoa A
  └─ Histórico de Abordagens
       └─ Card Abordagem #42
            └─ Coabordados: [avatar B] [avatar C]
                 └─ Clique em avatar B
                      └─ Modal preview: foto + nome + cpf + nascimento
                           └─ Clique no modal → navega para Ficha da Pessoa B
```

---

## Arquivos modificados

| Arquivo | Tipo de mudança |
|---|---|
| `frontend/js/pages/pessoa-detalhe.js` | Adicionar estado `pessoaPreview`, fileira de avatares no card de abordagem, modal overlay |

---

## O que NÃO muda

- Backend: nenhum endpoint novo, nenhum schema novo
- Seção de Vínculos (`relacionamentos`): permanece inalterada
- Lógica de carregamento de abordagens: permanece inalterada
