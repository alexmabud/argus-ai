# Design: Relatório de Abordagens

**Data:** 2026-04-06  
**Status:** Aprovado

## Problema

A tab "Ocorrência" no bottom nav exibia apenas um formulário de upload de PDF (RAP), sem listagem nem visualização das abordagens realizadas. O policial não tinha onde consultar o histórico de abordagens que registrou, ver os envolvidos, ou vincular documentos a uma abordagem específica.

## Solução

Substituir completamente a tela `ocorrencia-upload` por duas novas telas:

1. **Relatório de Abordagens** (lista) — entrada pela tab do bottom nav
2. **Detalhe da Abordagem** — aberta ao tocar em um card da lista

A RAP (PDF) e mídias extras passam a ser anexadas diretamente na tela de detalhe, com o `abordagem_id` preenchido automaticamente.

## Arquitetura

### Backend — novos endpoints

**`GET /abordagens/`**
- Lista paginada das abordagens do usuário autenticado (`usuario_id`)
- Parâmetros: `skip`, `limit` (padrão 20)
- Retorna por abordagem: `id`, `data_hora`, `endereco_texto`, `observacao`, lista de pessoas (`id`, `nome`, `foto_principal_url`), lista de veículos (`id`, `placa`, `modelo`, `cor`, `ano`, foto_url), ocorrência vinculada (`id`, `numero_ocorrencia`) se existir

**`GET /abordagens/{id}`**
- Detalhe completo de uma abordagem (mesma estrutura acima + coordenadas para o mapa)
- Retorna 404 se não pertencer à guarnição do usuário

**Novos métodos no `AbordagemService`:**
- `listar(usuario_id, skip, limit)` → lista paginada
- `buscar_por_id(id, guarnicao_id)` → detalhe com validação de tenant

**Novo schema `AbordagemListItem`** com dados suficientes para renderizar o card da lista sem chamadas extras.

### Backend — sem alteração necessária

- `POST /ocorrencias/` — já existe, recebe `abordagem_id` via form
- `POST /fotos/upload` — já existe; mídias extras usam `tipo="midia_abordagem"`
- `GET /fotos/abordagem/{id}` — já existe, usado no detalhe

### Frontend — arquivos alterados/criados

| Arquivo | Ação |
|---|---|
| `frontend/js/pages/ocorrencias.js` | **Novo** — lista de abordagens |
| `frontend/js/pages/abordagem-detalhe.js` | **Novo** — detalhe completo |
| `frontend/js/pages/ocorrencia-upload.js` | **Removido** |
| `frontend/index.html` | Atualizar scripts, nav label e navigate() |

### Fluxo de dados

```
Tab "Relatórios"
  → GET /abordagens/?skip=0&limit=20
  → lista de cards (data, avatares, endereço, badge RAP)
  → toque no card
    → navigate('abordagem-detalhe', {id})
    → GET /abordagens/{id}               (dados base)
    → GET /fotos/abordagem/{id}          (fotos pessoas + veículos + mídias)
    → renderiza: pessoas clicáveis, veículos, mapa Leaflet, observação
    → se sem RAP: formulário upload PDF + número RAP → POST /ocorrencias/
    → se com RAP: exibe nome do arquivo + link para abrir
    → upload mídia: POST /fotos/upload (tipo="midia_abordagem", abordagem_id)
```

## Telas

### Tela 1 — Lista (ocorrencias.js)

- Header: "Relatório de Abordagens" / "Registros Operacionais"
- Barra de busca local (filtra por nome ou placa no resultado carregado)
- Cards com: avatares dos abordados (iniciais ou foto), data/hora, endereço, badge "RAP vinculada" (verde) ou "Sem RAP" (laranja), badge de mídias se houver, contador de veículos
- Paginação via scroll infinito ou botão "carregar mais"

### Tela 2 — Detalhe (abordagem-detalhe.js)

Seções em ordem:
1. **Abordados** — chips com foto/avatar, toque navega para `pessoa-detalhe`
2. **Veículos** — row com thumb, placa, modelo/cor/ano
3. **Localização** — mapa Leaflet (mesmo padrão de `pessoa-detalhe.js`) + endereço textual
4. **Observação** — caixa de texto read-only
5. **Boletim de Ocorrência (RAP)** — se existir: nome do arquivo + link para abrir; se não: campo número RAP + upload PDF + botão enviar
6. **Mídias** — grid de thumbnails existentes + botão "+" para adicionar (foto/vídeo/documento)

### Bottom nav

- Label atual: "Ocorrência" → **"Relatórios"**
- Navigate destino: `ocorrencias` (nova tela de lista)

## Decisões de design

| Decisão | Motivo |
|---|---|
| Reuso do model `Foto` com `tipo="midia_abordagem"` | Evita nova tabela/migration; storage MinIO já funciona para qualquer binário |
| Lista filtra por `usuario_id`, não `guarnicao_id` | Policial vê apenas suas próprias abordagens, não as de toda a guarnição |
| RAP vinculada à abordagem via `abordagem_id` na `Ocorrencia` | Relacionamento já existe no model; sem mudança de schema |
| Detalhe em tela separada (não accordion) | Padrão estabelecido em `pessoa-detalhe.js`; melhor UX mobile com mapa |

## Mockup

Arquivo de referência: `docs/mockups/ocorrencias-mockup.html`
