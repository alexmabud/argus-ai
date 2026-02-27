# Argus AI — Compliance LGPD

## Visão Geral

O Argus AI implementa medidas de proteção de dados pessoais conforme a Lei Geral de Proteção de Dados (LGPD - Lei 13.709/2018).

## Medidas Implementadas

### 1. Criptografia de Dados Sensíveis

**CPF**: Criptografado com Fernet (AES-256-CBC) antes de armazenar.
- Campo `cpf_criptografado`: texto cifrado
- Campo `cpf_hash`: SHA-256 para busca sem decifrar
- Campo `cpf_masked`: exibição parcial (`***.***.789-00`)
- Chave de criptografia em variável de ambiente (`ENCRYPTION_KEY`)

**Implementação**: `app/core/crypto.py`

### 2. Audit Log

Todas as operações sensíveis são registradas com:
- ID do usuário que executou
- Ação realizada (CREATE, UPDATE, DELETE, READ)
- Recurso afetado e ID
- IP de origem e User-Agent
- Timestamp UTC

**Implementação**: `app/services/audit_service.py`, `app/models/audit_log.py`

### 3. Soft Delete

Nenhum dado é removido fisicamente do banco. Todos os models com dados pessoais usam `SoftDeleteMixin`:
- Campo `deleted_at`: timestamp da exclusão lógica
- Queries filtram automaticamente registros deletados
- Dados preservados para auditoria e compliance

**Implementação**: `app/models/base.py` (`SoftDeleteMixin`)

### 4. Multi-Tenancy

Isolamento de dados por guarnição:
- Cada registro possui `guarnicao_id`
- Queries filtradas automaticamente via `MultiTenantMixin`
- Usuário só acessa dados da própria guarnição

**Implementação**: `app/models/base.py` (`MultiTenantMixin`)

### 5. Anonimização Periódica

Script de anonimização para dados além do período de retenção:
- Período padrão: 1825 dias (5 anos)
- Sobrescreve: nome → "ANONIMIZADO", CPF → null, observações → null
- Remove embeddings faciais (512-dim) das fotos
- Suporta modo `--dry-run` para simulação

**Implementação**: `scripts/anonimizar_dados.py`

**Execução**:
```bash
make anonimizar          # Executar anonimização
make anonimizar-dry      # Simulação (sem modificar)
```

### 6. Controle de Acesso

- Autenticação via JWT (access + refresh tokens)
- Rate limiting em todos os endpoints sensíveis
- CORS restrito a origens autorizadas

### 7. Segurança em Trânsito

- HTTPS obrigatório em produção
- Tokens JWT com expiração configurável
- Refresh token com rotação

## Direitos do Titular

| Direito LGPD | Implementação |
|--------------|---------------|
| Acesso | GET `/api/v1/pessoas/{id}` (dados mascarados) |
| Retificação | PUT `/api/v1/pessoas/{id}` |
| Eliminação | DELETE `/api/v1/pessoas/{id}` (soft delete) |
| Anonimização | `scripts/anonimizar_dados.py` (periódico) |
| Portabilidade | Export via API (formato JSON) |

## Configuração

```env
ENCRYPTION_KEY=<chave-fernet-base64>   # Criptografia CPF
DATA_RETENTION_DAYS=1825               # 5 anos de retenção
```
