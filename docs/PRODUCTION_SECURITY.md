# 🔒 Segurança em Produção com Dados Reais

## Estratégia: Código Público + Dados Privados

### Como Funciona:
- ✅ **GitHub (público)**: Apenas código-fonte, sem dados
- ✅ **Servidor (privado)**: Código + banco de dados com dados reais criptografados
- ✅ **Dados reais NUNCA vão para o GitHub**: Ficam isolados no PostgreSQL do servidor

---

## 🛡️ Camadas de Proteção dos Dados Reais

### 1. **Criptografia em Repouso (Database)**

Os dados sensíveis são criptografados ANTES de ir para o banco:

```python
# CPF é criptografado com Fernet (AES-256)
from app.core.crypto import encrypt, hash_for_search

cpf_encrypted = encrypt("123.456.789-10")  # Fernet AES-256
cpf_hash = hash_for_search("123.456.789-10")  # SHA-256 para busca

# No banco:
# cpf_encrypted = "gAAAAABh..." (criptografado)
# cpf_hash = "abc123..." (hash para busca sem descriptografar)
```

**Garantia:** Mesmo se alguém roubar o banco de dados, os CPFs estarão criptografados.

### 1b. **Criptografia de Disco (OCI Vault)**

Os Block Volumes do servidor (`argus-banco` 50GB e `argus-fotos` 100GB) usam **customer-managed key** no OCI Vault:

- Vault: `argus-vault` — região `sa-saopaulo-1`
- Chave: `argus-disk-key` — AES-256, Software protection
- OCID da chave e vault armaenadas

**Garantia:** Acesso físico ao servidor ou ao storage da Oracle não é suficiente para ler os dados — a chave está sob controle exclusivo do administrador do sistema.

### 2. **Criptografia em Trânsito (HTTPS)**

```nginx
# Nginx config (produção)
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/seu-dominio/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
}
```

**Garantia:** Dados viajam criptografados entre cliente e servidor.

### 3. **Separação de Ambientes**

```bash
# PRODUÇÃO (dados reais)
DATABASE_URL=postgresql://user:pass@seu-servidor-producao.com:5432/argus_prod
ENCRYPTION_KEY=<sua-chave-producao-real>
SECRET_KEY=<sua-chave-jwt-producao-real>

# DESENVOLVIMENTO (dados fictícios)
DATABASE_URL=postgresql://argus:argus_dev@localhost:5432/argus_db
ENCRYPTION_KEY=<chave-dev-diferente>
SECRET_KEY=<chave-dev-diferente>
```

**Garantia:** Ambientes isolados, chaves diferentes, bancos diferentes.

### 4. **Acesso Restrito ao Servidor**

```bash
# SSH com chave (não senha)
ssh -i ~/.ssh/argus_prod.pem user@seu-servidor

# PostgreSQL aceita conexões APENAS do localhost (não da internet)
# Em postgresql.conf:
listen_addresses = 'localhost'

# Firewall bloqueia tudo exceto 443 (HTTPS)
ufw allow 443/tcp
ufw deny 5432/tcp  # PostgreSQL não acessível externamente
```

**Garantia:** Banco de dados não é acessível da internet.

### 5. **Backups Criptografados**

```bash
# Backup com criptografia GPG
pg_dump argus_prod | gzip | gpg --encrypt --recipient você@email.com > backup_$(date +%Y%m%d).sql.gz.gpg

# Armazenar em S3/R2 com criptografia do lado do servidor
aws s3 cp backup.sql.gz.gpg s3://argus-backups/ --sse AES256
```

**Garantia:** Backups são criptografados antes de sair do servidor.

### 6. **Audit Trail Completo**

```python
# TODO log é registrado
await audit_service.log(
    usuario_id=user.id,
    acao="READ",
    recurso="pessoa",
    recurso_id=pessoa.id,
    detalhes={"campos_acessados": ["nome", "cpf"]},
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent")
)
```

**Garantia:** Você sabe quem acessou o quê, quando e de onde.

### 7. **Multi-Tenancy**

```python
# Cada guarnição/equipe só vê seus próprios dados
query = TenantFilter.apply(query, Pessoa, user)
# WHERE pessoas.guarnicao_id = user.guarnicao_id
```

**Garantia:** Isolamento entre equipes.

---

## 🔑 Gerenciamento de Chaves de Produção

### NUNCA faça isso:
```bash
# ❌ ERRADO - chaves no código
SECRET_KEY = "minha-chave-secreta"

# ❌ ERRADO - chaves no GitHub
git add .env
git commit -m "add env"
```

### Sempre faça assim:
```bash
# ✅ CORRETO - chaves em variáveis de ambiente do servidor

# No servidor de produção:
echo "SECRET_KEY=$(openssl rand -hex 32)" >> /etc/argus/.env.production
echo "ENCRYPTION_KEY=$(python scripts/generate_encryption_key.py)" >> /etc/argus/.env.production

# Permissões restritas
chmod 600 /etc/argus/.env.production
chown argus:argus /etc/argus/.env.production
```

**Onde armazenar chaves:**
- ✅ Variáveis de ambiente do SO
- ✅ Secrets manager (AWS Secrets Manager, HashiCorp Vault)
- ✅ Arquivo .env NO SERVIDOR (nunca commitado)

**Onde NUNCA armazenar:**
- ❌ No código-fonte
- ❌ No Git/GitHub
- ❌ Em comentários no código
- ❌ Em logs

---

## 📊 Monitoramento de Segurança

### 1. Logs de Acesso

```python
# Monitorar acessos suspeitos
# - Muitas consultas em pouco tempo (possível scraping)
# - Acessos de IPs desconhecidos
# - Tentativas de SQL injection

# Em app/core/middleware.py (AuditMiddleware)
if request.url.path.contains("--") or request.url.path.contains("'"):
    await audit.log(usuario_id=0, acao="SECURITY_ALERT",
                    recurso="sql_injection_attempt",
                    ip_address=request.client.host)
```

### 2. Alertas Automáticos

```python
# Configurar alertas para:
- Tentativas de login falhas (>5 em 10min)
- Acesso a dados sensíveis fora do horário
- Mudanças em campos criptografados
- Exportação em massa de dados
```

### 3. Rate Limiting em Produção

```python
# Em produção, ser mais restritivo
RATE_LIMIT_DEFAULT = "30/minute"  # Ao invés de 60
RATE_LIMIT_HEAVY = "5/minute"     # IA e buscas pesadas
```

---

## 🔐 Checklist de Segurança em Produção

### Antes do Deploy:

- [ ] `.env` NÃO está no repositório
- [ ] `.env` está no `.gitignore`
- [ ] `SECRET_KEY` é diferente de dev (gerado com `openssl rand -hex 32`)
- [ ] `ENCRYPTION_KEY` é diferente de dev (gerado com script)
- [ ] `DEBUG=false` em produção
- [ ] HTTPS configurado (Let's Encrypt)
- [ ] PostgreSQL aceita APENAS conexões localhost
- [ ] Firewall configurado (apenas 443 aberto)
- [ ] Backups automáticos configurados
- [ ] Backup criptografado com GPG
- [ ] Logs de acesso configurados
- [ ] Alertas de segurança ativos
- [ ] `CORS_ORIGINS` restrito (não `["*"]`)

### Semanalmente:

- [ ] Revisar logs de audit_logs para atividades suspeitas
- [ ] Verificar tentativas de acesso não autorizado
- [ ] Rodar `pip-audit` para vulnerabilidades
- [ ] Verificar se backups estão funcionando

### Mensalmente:

- [ ] Rotacionar senha do banco de dados
- [ ] Revisar permissões de usuários
- [ ] Verificar se há dados órfãos
- [ ] Testar restauração de backup

### Anualmente:

- [ ] Rotacionar `ENCRYPTION_KEY` (cuidado: precisa re-criptografar dados)
- [ ] Auditoria de segurança completa
- [ ] Revisar conformidade LGPD

---

## 🚨 Resposta a Incidentes

### Se suspeitar de vazamento:

1. **Isolar imediatamente**
   ```bash
   # Derrubar o servidor temporariamente
   systemctl stop argus

   # Bloquear acesso ao banco
   ufw deny 5432/tcp
   ```

2. **Investigar**
   ```sql
   -- Verificar últimos acessos
   SELECT * FROM audit_logs
   ORDER BY timestamp DESC
   LIMIT 100;

   -- Buscar ações suspeitas
   SELECT * FROM audit_logs
   WHERE acao = 'EXPORT'
   OR acao LIKE '%DELETE%'
   ORDER BY timestamp DESC;
   ```

3. **Rotacionar chaves**
   ```bash
   # Gerar novas chaves
   openssl rand -hex 32 > new_secret.key
   python scripts/generate_encryption_key.py > new_encryption.key

   # Atualizar .env
   # Reiniciar serviço
   ```

4. **Notificar afetados** (LGPD obriga)
   - Informar autoridades (ANPD)
   - Informar usuários afetados
   - Documentar o incidente

---

## 🎯 Fluxo de Dados Seguro

```
[Cliente]
   ↓ (HTTPS/TLS)
[Nginx] → [FastAPI]
              ↓
         [Service] ← (Validação Pydantic)
              ↓
         [Crypto Service] ← (Criptografa CPF com Fernet)
              ↓
         [Repository]
              ↓
         [PostgreSQL] ← (Dados criptografados em disco)
              ↓
         [Backup] ← (Criptografado com GPG)
              ↓
         [S3/R2] ← (Server-side encryption)
```

**Em NENHUM momento dados sensíveis trafegam ou são armazenados em texto claro.**

---

## 📝 Conformidade LGPD

### Direitos Implementados:

1. **Direito ao Acesso** ✅
   - Usuário pode consultar seus dados
   - API: `GET /api/v1/pessoas/{id}`

2. **Direito à Portabilidade** ✅
   - Exportar dados em JSON
   - API: `GET /api/v1/pessoas/{id}/exportar`

3. **Direito à Retificação** ✅
   - Usuário pode corrigir dados
   - API: `PUT /api/v1/pessoas/{id}`

4. **Direito ao Esquecimento** ✅
   - Soft delete (não remove fisicamente)
   - Anonização após período de retenção
   - API: `DELETE /api/v1/pessoas/{id}` (marca como inativo)

5. **Audit Trail** ✅
   - Log de TODAS as ações
   - Tabela `audit_logs` imutável

---

## 🔒 Resumo Final

### Dados Reais NUNCA vão para o GitHub porque:

1. ✅ Estão no banco de dados PostgreSQL (não no código)
2. ✅ São criptografados com Fernet antes de salvar
3. ✅ `.env` com chaves está no `.gitignore`
4. ✅ Backups são criptografados antes de sair do servidor
5. ✅ Servidor de produção é separado do código público

### GitHub só tem:

- ✅ Código-fonte (Python, SQL schemas, configs)
- ✅ Documentação
- ✅ `.env.example` (SEM valores reais)
- ✅ Estrutura de arquivos

### Servidor de produção tem:

- ✅ Código + banco de dados com dados reais criptografados
- ✅ `.env` com chaves reais (NUNCA commitado)
- ✅ Logs de acesso
- ✅ Backups criptografados

---

**Você pode ter o código público E dados privados seguros ao mesmo tempo!** 🔒✨
