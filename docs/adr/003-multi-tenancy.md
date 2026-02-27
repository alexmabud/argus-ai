# ADR 003 — Multi-Tenancy por Guarnição

## Status
Aceito

## Contexto
Múltiplas guarnições usam o mesmo sistema. Cada guarnição deve ver apenas seus próprios dados (abordagens, pessoas, veículos). As opções foram: schema por tenant, banco por tenant, filtro por coluna.

## Decisão
Multi-tenancy via coluna `guarnicao_id` em todas as tabelas sensíveis, com mixin SQLAlchemy para filtro automático.

### Implementação
- `MultiTenantMixin`: Adiciona `guarnicao_id` (FK) a todos os models
- Repositories filtram automaticamente por `guarnicao_id` do usuário autenticado
- Dados globais (legislação, passagens) não possuem tenant

### Tabelas com tenant
Pessoas, veículos, abordagens, fotos, ocorrências, audit logs

### Tabelas globais
Legislação, passagens, guarnições, usuários

## Consequências
- Isolamento de dados sem complexidade de schemas separados
- Single database simplifica backup, migrations e queries
- Performance garantida com índice composto `(guarnicao_id, ...)`
- Risco: erro de implementação pode vazar dados entre guarnições
- Mitigação: fixtures de teste verificam isolamento
