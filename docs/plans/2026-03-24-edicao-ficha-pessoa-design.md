# Design: Edição de Ficha de Pessoa

**Data:** 2026-03-24
**Status:** Aprovado

## Contexto

Ao abrir a ficha de uma pessoa em Consultas, os dados são read-only. Operadores precisam corrigir dados pessoais cadastrados errado e endereços incompletos/incorretos sem precisar criar registros novos.

## Decisões

- **Modelo de edição:** Modal (limpo, rápido pra uso em campo)
- **Endereço:** Edição sobrescreve dados antigos (audit log preserva histórico)
- **Campos editáveis:** Todos os dados pessoais + todos os campos de endereço
- **Abordagem:** Dois modais separados (dados pessoais + endereço)

## Backend

### PATCH /pessoas/{pessoa_id}

- Expõe `PessoaService.atualizar()` já existente
- Usa schema `PessoaUpdate` já existente (todos campos opcionais)
- Campos: `nome`, `cpf`, `data_nascimento`, `apelido`, `observacoes`
- Se CPF mudar: recriptografa (Fernet) + recalcula hash SHA-256
- Validação multi-tenancy + audit log automático
- Rate limit consistente com outros endpoints

### PATCH /pessoas/{pessoa_id}/enderecos/{endereco_id}

- Novo schema `EnderecoUpdate` (campos opcionais, mesmos do `EnderecoCreate`)
- Novo método `atualizar_endereco()` no `PessoaService`
- Se latitude/longitude mudar: atualiza geometria PostGIS
- Validação multi-tenancy + audit log
- Campos: `endereco`, `bairro`, `cidade`, `estado`, `latitude`, `longitude`, `data_inicio`, `data_fim`

### Ambos endpoints

- Retornam objeto atualizado
- Rate limit: 30 req/min (consistente)
- Tenant check obrigatório

## Frontend

### Modal Dados Pessoais

- Botão lápis no canto superior direito do card "Dados Pessoais"
- Abre modal com campos: Nome, CPF, Data Nascimento, Apelido, Observações
- Campos pré-preenchidos com valores atuais
- Botões: Salvar / Cancelar
- Ao salvar: PATCH /pessoas/{id} → fecha modal → atualiza ficha

### Modal Endereço (edição + criação)

- Ícone lápis em cada card de endereço → abre modal em modo edição (pré-preenchido)
- Botão "+ Novo Endereço" no header da seção → abre modal em modo criação (vazio)
- Campos: Logradouro, Bairro, Cidade, Estado
- Ao salvar: PATCH (edição) ou POST (criação) → fecha modal → atualiza lista

### UX

- Loading spinner no botão Salvar durante request
- Toast de sucesso/erro após operação
- Estilo dos modais consistente com modal de vínculos manuais existente

## Arquivos impactados

### Backend
- `app/api/v1/pessoas.py` — novo endpoint PATCH pessoa + PATCH endereço
- `app/schemas/pessoa.py` — novo schema EnderecoUpdate
- `app/services/pessoa_service.py` — novo método atualizar_endereco()
- `app/repositories/pessoa_repo.py` — novo método update_endereco() se necessário

### Frontend
- `frontend/js/pages/pessoa-detalhe.js` — botões de edição + modais + lógica de submit
