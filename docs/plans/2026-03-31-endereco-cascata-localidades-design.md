# Design: Endereço em Cascata com Tabela Localidades

**Data:** 2026-03-31  
**Status:** Aprovado

## Problema

O cadastro de endereço em pessoa-detalhe usa campos de texto livre para bairro, cidade e estado, gerando duplicatas e inconsistências nos dados ("São Paulo", "SP", "sao paulo", "S. Paulo").

## Solução

Tabela hierárquica `localidades` + dropdowns/autocomplete em cascata no frontend. Cadastro de novas entradas inline para evitar duplicatas.

---

## Banco de Dados

### Nova tabela `localidades`

```sql
CREATE TABLE localidades (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(200) NOT NULL,        -- normalizado (sem acento, lower) para busca
    nome_exibicao   VARCHAR(200) NOT NULL,        -- nome original para exibição
    tipo            VARCHAR(10) NOT NULL,          -- 'estado' | 'cidade' | 'bairro'
    sigla           VARCHAR(2),                   -- só para estados (AC, SP, RJ...)
    parent_id       INTEGER REFERENCES localidades(id),  -- nullable para estados
    ativo           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Constraints lógicas** (validadas no service):
- `tipo = 'estado'` → `parent_id` deve ser NULL, `sigla` obrigatória
- `tipo = 'cidade'` → `parent_id` aponta para um estado
- `tipo = 'bairro'` → `parent_id` aponta para uma cidade

**Seed:** 27 estados brasileiros pré-cadastrados.

### Alterações em `enderecos_pessoa`

Adicionar colunas (nullable para não quebrar dados existentes):
- `estado_id` FK → localidades(id)
- `cidade_id` FK → localidades(id)
- `bairro_id` FK → localidades(id)

Colunas texto `estado`, `cidade`, `bairro` mantidas como deprecated — serão removidas em migration futura.

---

## API

### Novo router `/api/v1/localidades`

```
GET /localidades?tipo=estado
    → lista todos os 27 estados ordenados por nome

GET /localidades?tipo=cidade&parent_id={estado_id}&q={texto}
    → autocomplete: cidades do estado filtradas por texto (ILIKE %q%)
    → retorna máx 10 resultados

GET /localidades?tipo=bairro&parent_id={cidade_id}&q={texto}
    → autocomplete: bairros da cidade filtrados por texto
    → retorna máx 10 resultados

POST /localidades
    body: { nome, tipo, parent_id }
    → valida hierarquia
    → normaliza nome para busca (remove acento, lower)
    → retorna { id, nome_exibicao, tipo }
```

**Busca:** `ILIKE %q%` no campo `nome` (já normalizado). Sem pg_trgm necessário.

**Validações no service:**
- Não permite duplicata: mesmo `nome` normalizado + mesmo `parent_id` + mesmo `tipo`
- Cidade sem estado pai → erro 400
- Bairro sem cidade pai → erro 400

### Alterações em schemas existentes

`EnderecoPessoaCreate` e `EnderecoPessoaUpdate` passam a aceitar opcionalmente:
- `estado_id: int | None`
- `cidade_id: int | None`
- `bairro_id: int | None`

---

## Frontend (pessoa-detalhe.js)

### Componente de endereço substituído

**Antes:** 3 inputs texto livres (Bairro, Cidade, UF)

**Depois:**

1. **Estado** — `<select>` fixo, carregado uma vez ao abrir o modal via `GET /localidades?tipo=estado`

2. **Cidade** — input com autocomplete
   - Desabilitado até estado ser selecionado
   - Ao digitar ≥2 chars → `GET /localidades?tipo=cidade&parent_id={estadoId}&q={texto}`
   - Dropdown com sugestões abaixo do input
   - Sem resultado: exibe **"+ Cadastrar '{texto}' como nova cidade"**
     → `POST /localidades` → cidade criada e selecionada automaticamente

3. **Bairro** — mesmo comportamento, desabilitado até cidade ser selecionada

### Estado Alpine.js adicionado

```js
estadoId: null,
cidadeId: null,
bairroId: null,
cidadeTexto: '',
bairroTexto: '',
cidadeSugestoes: [],
bairroSugestoes: [],
```

### Ao resetar estado → limpar cidade e bairro
### Ao resetar cidade → limpar bairro

### Payload ao salvar endereço

```js
{
  endereco: '...',   // logradouro + número (texto livre — mantido)
  estado_id: 5,
  cidade_id: 42,
  bairro_id: 118,    // nullable
}
```

---

## Fluxo completo — exemplo

```
1. Usuário abre modal de endereço
2. Seleciona "SP" no dropdown de estados  →  estadoId = 5
3. Digita "Campin" no campo cidade
   →  GET /localidades?tipo=cidade&parent_id=5&q=campin
   →  sem resultado
   →  exibe "+ Cadastrar 'Campin...' como nova cidade"
4. Clica no botão
   →  POST /localidades { nome: "Campinas", tipo: "cidade", parent_id: 5 }
   →  cidade criada, cidadeId = 42
5. Campo bairro habilitado, digita "Centro"
   →  GET /localidades?tipo=bairro&parent_id=42&q=centro
   →  sem resultado → "+ Cadastrar 'Centro' como novo bairro"
6. Clica → bairroId = 118
7. Salva endereço com estado_id, cidade_id, bairro_id
```

---

## O que NÃO muda

- Campo `endereco` (logradouro + número) continua texto livre
- Abordagem continua puxando localização de pessoa-detalhe automaticamente
- Dados existentes não são quebrados (colunas texto mantidas)
