# Design: Legenda com Dados Pessoais na Foto Ampliada

**Data:** 2026-04-04  
**Status:** Aprovado

## Problema

Ao abrir a foto ampliada de um abordado, o modal exibe apenas a imagem. Quando o operador tira um print para registro, não há dados da pessoa na captura. Queremos exibir uma legenda abaixo da foto com nome, dados pessoais e último endereço.

## Solução

Abordagem A — Legenda abaixo da foto no modal existente.

Modificar o modal de `fotoAmpliada` (linha ~139-143 de `pessoa-detalhe.js`) para ter um container vertical: foto em cima, bloco de dados abaixo. Sem novo estado Alpine — usa `pessoa` que já está disponível no escopo.

## Layout

```
┌─────────────────────────────────┐
│                                 │
│         [foto ampliada]         │
│                                 │
├─────────────────────────────────┤
│ CAUAN VINICIUS BATISTA DE SOUSA │
│ Vulgo: Cau           (se tiver) │
│ Nasc: 24/10/2007 (18 anos)      │
│ CPF: ***.***.***/***-**          │
│ End: Qd 3, Cj 3D, Jardim Roriz  │  (se tiver)
└─────────────────────────────────┘
```

## Comportamento

- A legenda aparece em **ambos** os fluxos de abertura:
  - Grid principal (linha ~120)
  - Modal "todas as fotos" (linha ~160)
- Clique na **foto** fecha o modal; clique na **legenda** NÃO fecha (usar `@click.stop`)
- Se não houver CPF cadastrado, omite a linha de CPF
- Se não houver endereço, omite a linha de endereço
- Se não houver apelido, omite o vulgo
- Endereço exibido: `pessoa.enderecos[0]` (primeiro = atual), formatado via `formatEndereco(end)`
- Nascimento formatado via `formatarNascimento(data_nascimento, '')` (já existe)

## Visual

- Container com fundo `rgba(5,10,15,0.95)`, bordas arredondadas somente na base (`border-radius: 0 0 4px 4px`)
- Padding interno: `0.75rem`
- Nome: `font-family: var(--font-display)`, `font-weight: 700`, `color: var(--color-text)`, `text-transform: uppercase`
- Demais campos: `font-size: 0.8rem`, `color: var(--color-text-muted)`, `font-family: var(--font-data)`
- Largura máxima do container foto+legenda: `min(90vw, 480px)`

## Implementação

### Arquivo único afetado

`frontend/js/pages/pessoa-detalhe.js`

### Mudança no modal (linha ~139-143)

**Antes:**
```html
<div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
     style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 1rem;">
  <img :src="fotoAmpliada" style="max-width: 100%; max-height: 100%; border-radius: 4px;">
</div>
```

**Depois:**
```html
<div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
     style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 1rem;">
  <div @click.stop style="display: flex; flex-direction: column; max-width: min(90vw, 480px); width: 100%;">
    <img :src="fotoAmpliada" @click="fotoAmpliada = null"
         style="width: 100%; border-radius: 4px 4px 0 0; display: block; cursor: pointer;">
    <div style="background: rgba(5,10,15,0.95); border-radius: 0 0 4px 4px; padding: 0.75rem;">
      <!-- nome -->
      <p style="font-family: var(--font-display); font-weight: 700; color: var(--color-text); text-transform: uppercase; margin: 0 0 0.375rem 0;" x-text="pessoa.nome"></p>
      <!-- vulgo -->
      <p x-show="pessoa.apelido" style="font-size: 0.8rem; color: var(--color-secondary); font-family: var(--font-data); margin: 0 0 0.2rem 0;" x-text="'Vulgo: ' + pessoa.apelido"></p>
      <!-- nascimento -->
      <p x-show="pessoa.data_nascimento" style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
         x-text="'Nasc: ' + formatarNascimento(pessoa.data_nascimento, '')"></p>
      <!-- cpf -->
      <p x-show="pessoa.cpf || pessoa.cpf_masked" style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
         x-text="'CPF: ' + (pessoa.cpf || pessoa.cpf_masked)"></p>
      <!-- endereço atual -->
      <p x-show="pessoa.enderecos?.length > 0" style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0;"
         x-text="'End: ' + formatEndereco(pessoa.enderecos?.[0])"></p>
    </div>
  </div>
</div>
```

## Sem mudanças em

- API / backend
- Banco de dados
- Schemas Pydantic
- Testes de backend
- Outros arquivos frontend
