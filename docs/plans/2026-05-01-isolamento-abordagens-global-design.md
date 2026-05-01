# Design: Isolamento de Abordagens — Cobertura Global

**Data:** 2026-05-01
**Status:** Aprovado

## Problema

O toggle `isolamento_abordagens` da equipe só funciona no endpoint de lista/relatório de abordagens. Analytics e consulta sempre filtram pela equipe do usuário, ignorando o toggle.

## Comportamento Esperado

| Toggle | Abordagens visíveis |
|--------|-------------------|
| ON (ativado) | Apenas da própria equipe |
| OFF (desativado) | De todas as equipes do sistema |

Pessoas cadastradas são sempre visíveis para todos, independente do toggle (spec do projeto).

## Abordagem Escolhida: Opção A — Estender padrão existente

O padrão `isolamento: bool` já existe no endpoint de abordagens. Estender para analytics e consulta com a mesma lógica.

**Conversão no nível da API:**
```python
isolamento = bool(user.guarnicao and user.guarnicao.isolamento_abordagens)
guarnicao_filter = user.guarnicao_id if isolamento else None
```

**No service/repo:** aceitar `guarnicao_id: int | None`. Quando `None`, omitir o filtro `WHERE guarnicao_id = X`.

## Componentes Afetados

### 1. Analytics (`app/api/v1/analytics.py` + `app/services/analytics_service.py`)

- Todos os 13 métodos do service mudam `guarnicao_id: int` → `guarnicao_id: int | None`
- Cada query adiciona o filtro condicionalmente: `if guarnicao_id is not None`
- API calcula `guarnicao_filter` uma vez por endpoint e repassa ao service

Métodos: `resumo_hoje`, `resumo_mes`, `resumo_total`, `por_dia`, `por_mes`,
`dias_com_abordagem`, `abordagens_do_dia`, `pessoas_do_dia`, `pessoas_recorrentes`,
`resumo`, `mapa_calor`, `horarios_pico`, `metricas_rag`

### 2. Consulta (`app/api/v1/consultas.py` + `app/services/consulta_service.py`)

**Pessoas:** sempre passar `guarnicao_id=None` nas buscas de pessoa.
O `pessoa_repo` já trata `None` como "sem filtro" — nenhuma mudança no repo.

**Abordagens por texto:** respeita o toggle. Passar `guarnicao_filter` (None ou ID).

### 3. Banco de dados

Mover o usuário admin (matrícula 7356226) de volta para o 3º Pelotão (guarnicao_id=2)
após as correções de código.

## O que NÃO muda

- Endpoint de lista/relatório de abordagens: já funciona corretamente
- Endpoint de detalhe de abordagem: já funciona corretamente
- Repositories de pessoa: já aceitam `None` como guarnicao_id

## Resultado Esperado

Após o fix, usuário no 3º Pelotão com toggle OFF vê:
- Analytics com números de todas as equipes
- Lista/relatório de abordagens de todas as equipes
- Busca de pessoas retorna qualquer pessoa do sistema
- Busca por texto retorna abordagens de todas as equipes
