# Design: Melhorias na Página de Consulta — Busca por Foto, Layout e Resultado por Veículo

**Data:** 2026-03-10
**Status:** Aprovado

## Problema

A página de consulta atual tem três limitações principais:

1. Não há como buscar uma pessoa por foto (comparação facial)
2. O layout dos cards de Endereço e Veículo usa grid de colunas, passando a impressão de que todos os campos precisam ser preenchidos
3. A busca por veículo retorna o card do veículo, não a ficha do abordado vinculado

## Solução

### 1. Busca por foto no card Pessoa

Adicionar ícone de clipe ao lado direito do campo de texto existente. Ao clicar, abre seletor de arquivo (imagens jpg/png/webp). Ao selecionar:

- Exibe miniatura da foto com botão `×` para remover
- Dispara `POST /fotos/buscar-rosto` com o arquivo
- Mostra spinner "Comparando rosto..." durante o processamento
- Exibe fichas das pessoas encontradas com barra de confiança colorida:
  - Verde: ≥ 80% de similaridade
  - Amarelo: 60–79%
  - Laranja: < 60%
- Se texto e foto estiverem ativos simultaneamente, as buscas rodam em paralelo e os resultados são mesclados (deduplicados por `pessoa_id`)

### 2. Layout dos cards — campos empilhados verticalmente

**Card "Filtros por Endereço":**

Cada campo ocupa largura total, empilhado verticalmente. Cada um é um filtro independente e hierárquico:
- Bairro → lista todos os abordados deste bairro
- Cidade → lista todos os abordados desta cidade (todos os bairros)
- Estado (UF) → lista todos os abordados deste estado (todas as cidades)

Texto do card:
- Título: "Filtros por Endereço"
- Subtítulo: "Filtre abordados pelo local de residência cadastrado."
- Hint abaixo de cada campo explicando o escopo

**Card "Buscar por Veículo":**

Campos empilhados verticalmente. Campo "Cor" aparece apenas quando "Modelo" é preenchido.

Texto do card:
- Título: "Buscar por Veículo"
- Subtítulo: "Encontre o abordado pelo veículo com que foi visto."

### 3. Resultado de veículo retorna ficha do abordado

Ao buscar por placa ou modelo/cor, o resultado exibe fichas de pessoas (igual às outras buscas), não cards de veículo. Cada ficha tem uma linha extra:

> Vinculado via: ABC·1234 · Gol Branco 2020

Se um veículo estiver vinculado a múltiplas pessoas em abordagens distintas, todas aparecem.

## Arquitetura

### Sem migrations

Nenhuma alteração de banco de dados. Todos os vínculos já existem via `AbordagemVeiculo` e `AbordagemPessoa`.

### Backend — novo endpoint

**`GET /consultas/pessoas-por-veiculo`**

Parâmetros query (todos opcionais, mínimo 1):
- `placa: str` — busca parcial ILIKE
- `modelo: str` — busca parcial ILIKE
- `cor: str` — busca parcial ILIKE (opcional, combinado com modelo)

Lógica:
1. Busca veículos que atendam os filtros
2. Via `AbordagemVeiculo` resolve as abordagens
3. Via `AbordagemPessoa` resolve as pessoas de cada abordagem
4. Deduplicação por `pessoa_id`
5. Retorna lista de `PessoaComEnderecoRead` com campo extra `veiculo_info`

Retorno: reutiliza schema `PessoaComEnderecoRead` existente, acrescido de campo `veiculo_info: VeiculoInfo` (placa, modelo, cor).

### Backend — ajuste em `/fotos/buscar-rosto`

Schema `BuscaRostoItem` ganha campos opcionais vindos da pessoa vinculada à foto:
- `nome: str | None`
- `cpf_masked: str | None`
- `apelido: str | None`
- `foto_principal_url: str | None`

O serviço `FotoService.buscar_por_rosto` faz join com `Pessoa` para popular esses campos.

### Frontend — `consulta.js`

**Novos estados Alpine.js:**
- `fotoFile: null` — arquivo selecionado
- `fotoPreviewUrl: ''` — URL do object URL para miniatura
- `pessoasFoto: []` — resultados da busca facial
- `buscouFoto: false`

**Novos métodos:**
- `onFotoSelect(event)` — lê arquivo, gera preview, dispara busca
- `removeFoto()` — limpa arquivo e preview
- `searchPorFoto()` — faz multipart POST para `/fotos/buscar-rosto`
- `searchPorVeiculo()` — chama novo endpoint `/consultas/pessoas-por-veiculo`

**Resultado unificado de pessoas:**
- `get pessoasVisiveis()` mescla `pessoas` (texto) + `pessoasFoto` (foto), deduplicado por `id`
- Fichas de foto incluem `similaridade` para renderizar a barra de confiança

## Fluxo de dados — busca por foto

```
Usuário seleciona arquivo
  → onFotoSelect() gera preview
  → searchPorFoto() envia multipart POST /fotos/buscar-rosto
  → BuscaRostoResponse { resultados: [{pessoa_id, similaridade, nome, ...}] }
  → pessoasFoto populado
  → pessoasVisiveis mescla com pessoas (texto)
  → Render: card pessoa + barra de confiança colorida
```

## Fluxo de dados — busca por veículo

```
Usuário digita placa ou modelo
  → onInput() debounce 400ms
  → searchPorVeiculo() GET /consultas/pessoas-por-veiculo?placa=...
  → Lista PessoaComEnderecoRead com veiculo_info
  → Render: ficha do abordado + linha "Vinculado via: ABC·1234 · Gol Branco"
```

## Arquivos a modificar

| Arquivo | Tipo de mudança |
|---|---|
| `app/api/v1/consultas.py` | Novo endpoint `GET /pessoas-por-veiculo` |
| `app/services/consulta_service.py` | Novo método `pessoas_por_veiculo()` |
| `app/schemas/consulta.py` | Novo schema `VeiculoInfo`, campo em `PessoaComEnderecoRead` |
| `app/schemas/foto.py` | Campos opcionais em `BuscaRostoItem` |
| `app/services/foto_service.py` | Join com Pessoa em `buscar_por_rosto()` |
| `frontend/js/pages/consulta.js` | Layout + busca por foto + resultado por veículo |
