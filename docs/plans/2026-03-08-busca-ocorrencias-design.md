# Design: Busca de Ocorrências por Nome, RAP e Data

**Data:** 2026-03-08
**Status:** Aprovado

## Contexto

A página de ocorrências (`ocorrencia-upload.js`) já permite cadastrar RAPs com upload de PDF. O worker processa o PDF e extrai o texto completo para o campo `texto_extraido`. O objetivo é adicionar uma seção de busca nessa mesma página, aproveitando o texto extraído para permitir que policiais encontrem ocorrências por nome de abordado, número RAP ou data.

## Objetivo

Adicionar busca de ocorrências diretamente na página de upload, mantendo tudo relacionado a ocorrências em um único lugar.

## Design

### Frontend — `frontend/js/pages/ocorrencia-upload.js`

Nova seção "Buscar Ocorrência" abaixo do formulário de upload com 3 filtros independentes:

- **Nome do abordado** — campo texto livre, busca no texto extraído do PDF
- **Número RAP** — campo texto, busca parcial no número da ocorrência
- **Data** — campo date, filtra pela data de criação

O usuário preenche um ou mais campos e clica em "Buscar". Os resultados aparecem em cards com:
- Número RAP
- Data de registro
- Botão "Abrir PDF" → abre `arquivo_pdf_url` em nova aba

### Backend

**Novo endpoint:**
```
GET /api/v1/ocorrencias/buscar?nome=X&rap=Y&data=2026-03-08
```

Todos os parâmetros são opcionais e combinados com AND. Multi-tenant por `guarnicao_id`.

**Estratégias de busca:**
- `nome` → `pg_trgm` ILIKE `%nome%` no campo `texto_extraido` (só ocorrências com `processada=True`)
- `rap` → ILIKE `%rap%` no campo `numero_ocorrencia`
- `data` → filtro `DATE(criado_em) = data`

**Resposta:** lista de `OcorrenciaRead` (campos já existentes)

### Arquivos a modificar

| Arquivo | Alteração |
|---|---|
| `app/repositories/ocorrencia_repo.py` | Novo método `buscar(nome, rap, data, guarnicao_id)` |
| `app/services/ocorrencia_service.py` | Novo método `buscar()` delegando ao repo |
| `app/api/v1/ocorrencias.py` | Novo endpoint `GET /buscar` |
| `frontend/js/pages/ocorrencia-upload.js` | Seção de busca + exibição de resultados |

### Sem alterações em

- Models SQLAlchemy (sem migration)
- Schemas Pydantic (reutiliza `OcorrenciaRead`)
- Worker / tasks
- Autenticação / permissões

## Critérios de Sucesso

- Busca por nome retorna ocorrências cujo texto extraído contém o nome
- Busca por RAP retorna ocorrências com número parcialmente correspondente
- Busca por data filtra corretamente
- Filtros combinados funcionam com AND
- Resultados exibem link funcional para o PDF
- Multi-tenancy: cada guarnição vê apenas suas ocorrências
