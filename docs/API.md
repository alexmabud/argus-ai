# Argus AI — Referência da API v1

Base URL: `/api/v1`

Autenticação: Bearer JWT (`Authorization: Bearer <access_token>`).

> **Fonte autoritativa:** o Swagger interativo em `/docs` (e o OpenAPI em `/openapi.json`)
> reflete sempre os parâmetros e schemas exatos. Esta página é um índice de alto nível.
>
> **Não há endpoint público de registro.** Usuários são criados por um admin
> (`POST /admin/usuarios`), que gera uma senha única.

## Auth (`/auth`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/auth/login` | Login (matrícula + senha) → access + refresh tokens | Não | 10/min |
| POST | `/auth/refresh` | Renovar access token a partir do refresh token | Não | 30/min |
| POST | `/auth/logout` | Invalida a sessão atual (`session_id`) | Sim | 30/min |
| GET | `/auth/me` | Dados do usuário autenticado (inclui flags de admin/permissões) | Sim | 30/min |
| PUT | `/auth/perfil` | Atualizar perfil (nome, nome de guerra, posto/graduação) | Sim | 10/min |
| POST | `/auth/perfil/foto` | Upload de foto de perfil | Sim | 10/min |

## Pessoas (`/pessoas`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/pessoas/` | Criar pessoa (CPF criptografado Fernet + hash SHA-256) | Sim | 30/min |
| GET | `/pessoas/` | Listar (busca fuzzy nome/apelido, CPF, paginação) | Sim | 30/min |
| GET | `/pessoas/{id}` | Detalhe com endereços, relacionamentos e contagem de abordagens | Sim | 30/min |
| PATCH | `/pessoas/{id}` | Atualizar pessoa | Sim | 30/min |
| DELETE | `/pessoas/{id}` | Soft delete | Sim | 10/min |
| POST | `/pessoas/{id}/enderecos` | Adicionar endereço (ponto PostGIS) | Sim | 10/min |
| PATCH | `/pessoas/{id}/enderecos/{end_id}` | Atualizar endereço | Sim | 30/min |
| GET | `/pessoas/{id}/abordagens` | Abordagens da pessoa | Sim | 30/min |
| POST | `/pessoas/{id}/vinculos-manuais` | Criar vínculo manual entre pessoas | Sim | 30/min |
| DELETE | `/pessoas/{id}/vinculos-manuais/{vinculo_id}` | Remover vínculo manual | Sim | 10/min |
| GET | `/pessoas/{id}/observacoes` | Listar observações operacionais | Sim | 30/min |
| POST | `/pessoas/{id}/observacoes` | Criar observação | Sim | 30/min |
| PATCH | `/pessoas/{id}/observacoes/{obs_id}` | Atualizar observação | Sim | 30/min |
| DELETE | `/pessoas/{id}/observacoes/{obs_id}` | Soft delete de observação | Sim | 10/min |

## Veículos (`/veiculos`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/veiculos/` | Listar (busca por placa/modelo/cor) | Sim | 30/min |
| POST | `/veiculos/` | Criar veículo (placa normalizada) | Sim | 30/min |
| GET | `/veiculos/localidades` | Modelos e cores distintos (autocomplete) | Sim | 30/min |

## Abordagens (`/abordagens`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/abordagens/` | Criar abordagem (com pessoas/veículos + auto-relacionamento) | Sim | 30/min |
| GET | `/abordagens/` | Listar paginado; busca textual (`q`) por nome de pessoa, placa e veículo (modelo/cor/tipo), ou filtro por `data` | Sim | 30/min |
| GET | `/abordagens/{id}` | Detalhe com pessoas, veículos e fotos | Sim | 60/min |

## Fotos (`/fotos`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/fotos/upload` | Upload de foto de pessoa (face embedding async via worker) | Sim | 10/min |
| POST | `/fotos/midias` | Upload de mídia (foto/vídeo) vinculada a abordagem | Sim | 20/min |
| GET | `/fotos/pessoa/{id}` | Fotos de uma pessoa | Sim | 30/min |
| GET | `/fotos/abordagem/{id}` | Mídias de uma abordagem | Sim | 30/min |
| POST | `/fotos/buscar-rosto` | Busca facial (pgvector 512-dim, distância cosseno) | Sim | 10/min |
| POST | `/fotos/ocr-placa` | OCR de placa (EasyOCR) | Sim | 10/min |
| GET | `/fotos/{id}/download` | Download forçado via proxy do backend (`Content-Disposition: attachment`); imagens recebem marca d'água queimada com a matrícula e o acesso é auditado (`DOWNLOAD_MIDIA`) | Sim | 30/min |

## Consultas (`/consultas`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/consultas/` | Busca unificada por termo (pessoas + veículos + abordagens); filtra pessoas por endereço via texto (`bairro`/`cidade`/`estado`) ou por id de localidade em cascata (`estado_id`/`cidade_id`/`bairro_id`) | Sim | 30/min |
| GET | `/consultas/pessoas-por-veiculo` | Pessoas vinculadas a veículos (placa/modelo/cor) | Sim | 30/min |
| GET | `/consultas/localidades` | Bairros, cidades, estados distintos (filtros) | Sim | 30/min |

## Ocorrências (`/ocorrencias`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/ocorrencias/` | Upload de BO em PDF (extração de texto + embedding via worker) | Sim | 10/min |
| GET | `/ocorrencias/` | Listar paginado | Sim | 30/min |
| GET | `/ocorrencias/buscar` | Buscar por nome, número RAP ou data (busca textual) | Sim | 30/min |

> O embedding (pgvector 384-dim) é gerado e armazenado, mas a busca por similaridade
> ainda **não está exposta** em endpoint — a busca atual é textual.

## Localidades (`/localidades`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/localidades` | Listar localidades (estado/cidade/bairro) | Sim | 30/min |
| POST | `/localidades` | Criar localidade | Sim | 10/min |

## Analytics (`/analytics`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/analytics/resumo-hoje` | Totais do dia (abordagens, pessoas) | Sim | 30/min |
| GET | `/analytics/resumo-mes` | Totais do mês | Sim | 30/min |
| GET | `/analytics/resumo-total` | Totais gerais | Sim | 30/min |
| GET | `/analytics/pessoas-recorrentes` | Top pessoas mais abordadas | Sim | 30/min |
| GET | `/analytics/por-dia` | Série diária (últimos 30 dias) | Sim | 30/min |
| GET | `/analytics/por-mes` | Série mensal (últimos 12 meses) | Sim | 30/min |
| GET | `/analytics/dias-com-abordagem` | Dias do mês com atividade (calendário) | Sim | 30/min |
| GET | `/analytics/abordagens-do-dia` | Abordagens em data específica | Sim | 30/min |
| GET | `/analytics/pessoas-do-dia` | Pessoas abordadas em data específica | Sim | 30/min |

## Sync (`/sync`)

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| POST | `/sync/batch` | Sincronizar itens offline (idempotente por `client_id`) | Sim | 10/min |

## Admin (`/admin`)

Requer usuário admin. Operações sobre permissões granulares são controladas por super-admin.

| Método | Path | Descrição | Auth | Rate |
|--------|------|-----------|------|------|
| GET | `/admin/usuarios` | Listar usuários (ativos + pausados) | Admin | 30/min |
| POST | `/admin/usuarios` | Criar usuário com senha única auto-gerada | Admin | 10/min |
| PATCH | `/admin/usuarios/{id}/pausar` | Pausar/reativar acesso | Admin | 10/min |
| POST | `/admin/usuarios/{id}/gerar-senha` | Gerar nova senha única | Admin | 10/min |
| DELETE | `/admin/usuarios/{id}` | Excluir usuário (soft delete) | Admin | 10/min |
| PATCH | `/admin/usuarios/{id}/equipe` | Transferir usuário para outra equipe | Admin | 10/min |
| GET | `/admin/admins` | Listar admins e permissões granulares | Admin | 30/min |
| PUT | `/admin/usuarios/{id}/admin` | Definir/remover admin e permissões | Super-admin | 10/min |
| GET | `/admin/bpms` | Listar batalhões (BPMs) | Admin | 30/min |
| POST | `/admin/bpms` | Criar BPM | Admin | 10/min |
| PATCH | `/admin/bpms/{id}/toggle-isolamento` | Isolamento de dados por BPM | Admin | 10/min |
| GET | `/admin/equipes` | Listar equipes/guarnições | Admin | 30/min |
| POST | `/admin/equipes` | Criar equipe | Admin | 10/min |
| PATCH | `/admin/equipes/{id}/toggle-isolamento` | Isolamento de dados por equipe | Admin | 10/min |
| POST | `/admin/2fa/setup` | Iniciar configuração de 2FA (TOTP) | Admin | 5/min |
| POST | `/admin/2fa/verify` | Confirmar e ativar 2FA (TOTP) | Admin | 10/min |

## Health

| Método | Path | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/health` | Status da aplicação | Não |
