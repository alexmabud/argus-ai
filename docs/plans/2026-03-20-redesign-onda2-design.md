# Redesign Onda 2 — Dashboard + Consulta + Cards

**Data:** 2026-03-20
**Escopo:** Dashboard analitico, pagina de consulta, cards de resultado

## 1. Dashboard Analitico

- Cards de resumo (Hoje/Mes/Total) em glass-card com grid responsivo
- Numeros grandes em Rajdhani 700 com cores cianoeletrico (abordagens) e verde terminal (pessoas)
- Labels em font-data uppercase dim
- Graficos ApexCharts com cores #00D4FF e #00FF88, grid #1A2940, font Rajdhani
- Calendario com dias ativos marcados por dot ciano pulsante, selecao com glow
- Pessoas recorrentes com rank badge ciano e contador bold
- Todos os cards com glass-card (backdrop-blur + borda ciano translucida)

## 2. Pagina de Consulta

- Titulo "CONSULTA OPERACIONAL" em font-display uppercase
- Subtitulo "Busca Integrada // Pessoa / Endereco / Veiculo" em font-data
- Campo de busca com icone e placeholder uppercase
- Botao de reconhecimento facial com borda dashed ciano (em vez de indigo)
- Loading com texto "ANALISANDO BASE OPERACIONAL..." em font-data
- Barra de confianca facial com cores semanticas (verde/amarelo/laranja)
- Separadores com linhas --color-border em vez de slate-700
- Formulario de cadastro inline com labels uppercase

## 3. Cards de Resultado

- Fundo var(--color-surface), borda --color-border
- Hover: borda ilumina para ciano translucido + box-shadow sutil
- Avatares com border-radius 4px (nao circular)
- Nome em font-body 13px, dados em font-data 11px dim
- Chevron de navegacao em cor dim
