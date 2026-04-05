# Design: Exibir Idade na Ficha do Abordado

**Data:** 2026-04-04  
**Status:** Aprovado

## Problema

A ficha do abordado exibe a data de nascimento formatada, mas o operador precisa calcular mentalmente a idade. Queremos exibir a idade automaticamente ao lado da data.

## Solução

Abordagem B — método helper no componente Alpine.js.

Adicionar o método `calcularIdade(data)` no objeto Alpine de `pessoa-detalhe.js` e usá-lo nos dois locais onde a data de nascimento é exibida.

## Comportamento Esperado

**Ficha principal:**
> Nascimento: 24/10/2007 *(18 anos)*

**Preview de busca (linha 382):**
> Nascimento: 24/10/2007 *(18 anos)*

- A idade aparece entre parênteses, com cor `var(--color-text-dim)` (mais fraca)
- Se `data_nascimento` for nulo/vazio, não exibe nada
- A idade é calculada em relação à data atual do navegador
- Ajuste correto: se o aniversário ainda não ocorreu no ano corrente, subtrai 1

## Implementação

### Método a adicionar no componente Alpine

```js
calcularIdade(dataNascimento) {
    if (!dataNascimento) return null;
    const hoje = new Date();
    const nasc = new Date(dataNascimento + 'T00:00:00');
    let idade = hoje.getFullYear() - nasc.getFullYear();
    const m = hoje.getMonth() - nasc.getMonth();
    if (m < 0 || (m === 0 && hoje.getDate() < nasc.getDate())) idade--;
    return idade;
}
```

### Locais a alterar em `frontend/js/pages/pessoa-detalhe.js`

| Linha | Descrição |
|-------|-----------|
| ~56   | Ficha principal — `<span x-text="...">` da data de nascimento |
| ~382  | Preview de busca — texto de nascimento concatenado |

### Template resultante (linha ~56)

```html
<span style="color: var(--color-text-muted); margin-left: 0.25rem;"
      x-text="pessoa.data_nascimento
        ? new Date(pessoa.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR')
          + (calcularIdade(pessoa.data_nascimento) !== null
              ? ' (' + calcularIdade(pessoa.data_nascimento) + ' anos)'
              : '')
        : '—'">
</span>
```

## Arquivos Afetados

- `frontend/js/pages/pessoa-detalhe.js` — único arquivo a modificar

## Sem mudanças em

- API / backend
- Banco de dados
- Schemas Pydantic
- Testes de backend
