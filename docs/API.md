# Argus AI — Referência da API v1

Base URL: `/api/v1`

Autenticação: Bearer JWT (`Authorization: Bearer <token>`)

## Auth

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/auth/register` | Registrar agente | Não | 5/min |
| POST | `/auth/login` | Login (matrícula + senha) | Não | 10/min |
| POST | `/auth/refresh` | Renovar token | Não | 10/min |
| GET | `/auth/me` | Dados do usuário autenticado | Sim | - |

## Pessoas

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/pessoas/` | Criar pessoa (CPF criptografado) | Sim | 30/min |
| GET | `/pessoas/` | Listar (busca fuzzy nome/apelido/CPF) | Sim | 30/min |
| GET | `/pessoas/{id}` | Detalhe com endereços e vínculos | Sim | 30/min |
| PUT | `/pessoas/{id}` | Atualizar pessoa | Sim | 30/min |
| DELETE | `/pessoas/{id}` | Soft delete | Sim | 30/min |
| POST | `/pessoas/{id}/enderecos` | Adicionar endereço | Sim | 30/min |

## Veículos

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/veiculos/` | Criar veículo | Sim | 30/min |
| GET | `/veiculos/` | Listar (busca por placa/modelo/cor) | Sim | 30/min |
| GET | `/veiculos/{id}` | Detalhe do veículo | Sim | 30/min |
| PUT | `/veiculos/{id}` | Atualizar (placa imutável) | Sim | 30/min |
| DELETE | `/veiculos/{id}` | Soft delete | Sim | 30/min |

## Abordagens

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/abordagens/` | Criar abordagem (com pessoas/veículos) | Sim | 30/min |
| GET | `/abordagens/` | Listar paginado | Sim | 30/min |
| GET | `/abordagens/raio/` | Busca por raio geográfico (PostGIS) | Sim | 30/min |
| GET | `/abordagens/{id}` | Detalhe com relações | Sim | 30/min |
| PUT | `/abordagens/{id}` | Atualizar observação | Sim | 30/min |
| POST | `/abordagens/{id}/pessoas/{pid}` | Vincular pessoa | Sim | 30/min |
| DELETE | `/abordagens/{id}/pessoas/{pid}` | Desvincular pessoa | Sim | 30/min |
| POST | `/abordagens/{id}/veiculos/{vid}` | Vincular veículo | Sim | 30/min |
| DELETE | `/abordagens/{id}/veiculos/{vid}` | Desvincular veículo | Sim | 30/min |

## Fotos

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/fotos/upload` | Upload multipart (S3/R2) | Sim | 10/min |
| GET | `/fotos/pessoa/{id}` | Fotos de uma pessoa | Sim | - |
| GET | `/fotos/abordagem/{id}` | Fotos de uma abordagem | Sim | - |
| POST | `/fotos/buscar-rosto` | Busca facial (pgvector 512-dim) | Sim | 10/min |
| POST | `/fotos/ocr-placa` | OCR de placa (EasyOCR) | Sim | 10/min |

## Passagens

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/passagens/` | Criar passagem criminal | Sim | 10/min |
| GET | `/passagens/` | Listar (filtro lei/artigo) | Sim | - |
| GET | `/passagens/{id}` | Detalhe | Sim | - |

## Consultas

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/consultas/?q=` | Busca unificada (pessoa, veículo, abordagem) | Sim | - |

## Ocorrências

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/ocorrencias/` | Upload PDF (processamento assíncrono) | Sim | 10/min |
| GET | `/ocorrencias/` | Listar paginado | Sim | - |
| GET | `/ocorrencias/{id}` | Detalhe | Sim | - |

## Legislação

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/legislacao/` | Listar artigos | Sim | - |
| GET | `/legislacao/busca?q=` | Busca semântica (pgvector 384-dim) | Sim | - |
| GET | `/legislacao/{id}` | Detalhe | Sim | - |

## RAG

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/rag/relatorio` | Gerar relatório com IA | Sim | 10/min |
| POST | `/rag/busca` | Busca semântica cross-domain | Sim | 30/min |

## Analytics

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/analytics/resumo?dias=30` | Resumo operacional | Sim | - |
| GET | `/analytics/mapa-calor?dias=30` | Pontos para heatmap | Sim | - |
| GET | `/analytics/horarios-pico?dias=30` | Distribuição horária | Sim | - |
| GET | `/analytics/pessoas-recorrentes?limit=20` | Top pessoas | Sim | - |
| GET | `/analytics/rag-qualidade` | Métricas RAG | Sim | - |

## Sync

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/sync/batch` | Sincronizar itens offline (idempotente) | Sim | - |

## Relacionamentos

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/relacionamentos/pessoa/{id}` | Vínculos de uma pessoa | Sim | - |

## Health

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/health` | Status da aplicação | Não |
