# Design: Exibir policial no card de abordagem (Relatórios)

**Data:** 2026-05-02  
**Status:** Aprovado

## Problema

Na página de relatórios, ao listar abordagens do dia, cada card mostra data/hora em azul mas não identifica qual policial realizou a abordagem. O usuário precisa abrir o detalhe para descobrir isso.

## Solução

Exibir `posto_graduacao` + `nome_guerra` do policial no canto direito da linha de data/hora, dentro do card, sem abrir nova tela.

### Resultado visual

```
[ 02/05/2026 · 14:35          SD João Silva ]
[ MARIA DA SILVA · JOSÉ SOUZA              ]
[ Rua das Flores, 123                      ]
[ #42  Sem RAP  1 mídia                    ]
```

- Data/hora: azul ciano `#00D4FF`, 10px (sem alteração)
- Nome do policial: branco suave `rgba(255,255,255,0.45)`, 10px
- Se `usuario` for `null` ou `nome_guerra` vazio: span não renderiza

## Escopo de mudanças

| Arquivo | Tipo de mudança |
|---------|----------------|
| `app/schemas/usuario.py` | Novo schema `UsuarioResumoRead` (id, posto_graduacao, nome_guerra) |
| `app/schemas/abordagem.py` | Adicionar `usuario: UsuarioResumoRead \| None` em `AbordagemDetail` |
| `app/models/abordagem.py` | Adicionar `relationship("Usuario", lazy="selectin")` |
| `frontend/js/pages/ocorrencias.js` | Linha de data/hora vira flex com nome do policial à direita |

**Sem migration** — FK `usuario_id` já existe.  
**Sem novo endpoint** — `AbordagemDetail` já é retornado pelo `GET /abordagens/`.

## Decisões de design

- **Opção A escolhida** (embutir `usuario` no `AbordagemDetail`): segue o padrão já usado para `pessoas`, `veiculos`, `fotos` e `ocorrencias` com `lazy="selectin"`.
- `posto_graduacao` já é armazenado abreviado (ex: `SD`, `CB`, `3SGT`) — exibir como está.
- Schema mínimo (`UsuarioResumoRead`) expõe apenas os 3 campos necessários, sem vazar dados sensíveis.
