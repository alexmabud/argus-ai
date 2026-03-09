# Design: Campo Data da Ocorrência

**Data:** 2026-03-09

## Problema

A data exibida nas listas de ocorrências é `criado_em` (quando o registro foi feito no sistema), mas o fato pode ter ocorrido dias antes. O policial precisa registrar a data real do fato.

## Decisão

Adicionar campo `data_ocorrencia DATE NOT NULL` ao modelo `Ocorrencia`.

## Backend

- **Modelo:** `data_ocorrencia: Mapped[date]` — `DATE NOT NULL`
- **Migration:** coluna com `DEFAULT CURRENT_DATE` para linhas existentes
- **API POST /ocorrencias/:** parâmetro `data_ocorrencia: date = Form(...)` obrigatório
- **Schema OcorrenciaRead:** expõe `data_ocorrencia: date`
- **Busca por data:** filtro `data` em `buscar()` passa a filtrar por `data_ocorrencia` (não mais `criado_em`)

## Frontend

- **Formulário:** campo `<input type="date">` obrigatório, pré-preenchido com hoje
- **Listas:** exibir ambas as datas — "Ocorrido em DD/MM/AAAA · Registrado em DD/MM/AAAA"
- **Campo busca por data:** sem mudança visual, passa a filtrar por `data_ocorrencia`

## Fora do escopo

- Hora da ocorrência (apenas data)
- Tornar campo opcional
