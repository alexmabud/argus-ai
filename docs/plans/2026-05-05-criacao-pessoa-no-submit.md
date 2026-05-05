# Design: Criação de pessoa somente no submit da abordagem

**Data:** 2026-05-05  
**Status:** Aprovado

## Problema

Ao iniciar uma abordagem e cadastrar um novo abordado, o sistema faz `POST /pessoas/` imediatamente quando o usuário clica "Salvar e adicionar". Se o usuário não finalizar a abordagem (erro, desistência, dado errado), uma ficha de pessoa incompleta é criada no banco sem estar vinculada a nenhuma abordagem.

## Solução — Opção A: tudo local, criação no submit

Adie a criação da pessoa no banco para o momento em que a abordagem é efetivamente submetida.

### Mudanças (apenas frontend)

**Arquivo:** `frontend/js/pages/abordagem-nova.js`

#### 1. Novo array de estado

```js
novasPessoas: []  // pessoas ainda não criadas no banco
```

Cada entrada: `{ _tempId: -1, nome, cpf, data_nascimento, apelido, nome_mae, endereco, estado_id, cidade_id, bairro_id }`

#### 2. `criarPessoa()` refatorado

- Remove chamadas `api.post("/pessoas/")` e `api.post("/pessoas/{id}/enderecos")`
- Gera ID temporário negativo sequencial (`-1`, `-2`, ...)
- Empurra dados em `novasPessoas[]`
- Adiciona tempId em `pessoaIds[]` e objeto display em `pessoasSelecionadas[]`
- UI não muda — abordado aparece na lista normalmente

#### 3. `submit()` modificado

Antes de criar a abordagem:
1. Itera `novasPessoas[]`
2. Para cada: `POST /pessoas/` → obtém ID real
3. Se tiver endereço: `POST /pessoas/{id}/enderecos`
4. Substitui tempId pelo ID real em `pessoaIds[]`
5. Se qualquer criação falhar: exibe erro e aborta (abordagem não é criada)
6. Após todos IDs resolvidos: segue fluxo normal `POST /abordagens/`

#### 4. Remoção de abordado

Ao remover pessoa da lista com tempId, remove também de `novasPessoas[]`.

## Trade-offs

- **Risco aceito:** se o submit falhar após criar algumas pessoas mas antes de criar a abordagem, essas pessoas existem no banco sem abordagem vinculada. Isso é aceitável — a pessoa pode ser buscada e associada numa abordagem futura normalmente. O cenário atual já tinha esse risco por falha de rede.
- **Sem mudança de backend:** zero impacto em routers, services ou schemas.
- **Atomicidade:** não garantida no banco, mas o fluxo de criação de pessoas antes da abordagem é sequencial e com tratamento de erro.
