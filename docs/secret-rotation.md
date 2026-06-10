# Rotação de Segredos — Argus AI

Procedimento para rotação periódica de credenciais e chaves criptográficas.
Rotação recomendada: **a cada 90 dias** ou imediatamente após suspeita de comprometimento.

---

## 1. `SECRET_KEY` — Assinatura JWT

**Impacto:** invalida todos os tokens de acesso e refresh em circulação.
Todos os usuários precisarão fazer login novamente após a rotação.

```bash
# 1. Gerar nova chave
NEW_KEY=$(openssl rand -hex 32)
echo "Nova SECRET_KEY: $NEW_KEY"

# 2. Substituir no .env do servidor
# SECRET_KEY=<nova_chave>

# 3. Reiniciar a api e o worker (tokens antigos serão rejeitados imediatamente)
docker compose -f docker-compose.prod.yml restart api worker
```

---

## 2. `ENCRYPTION_KEY` — Fernet AES-256 (CPFs)

⚠️ **Atenção:** esta rotação exige re-cifragem de todos os CPFs no banco.
Planejar janela de manutenção com 0 requests de escrita.

```bash
# 1. Gerar nova chave Fernet
NEW_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "Nova ENCRYPTION_KEY: $NEW_KEY"

# 2. Fazer dump dos CPFs atuais (com chave velha) ANTES de trocar .env
# (usar scripts/anonimizar_dados.py como referência para leitura bulk)

# 3. Atualizar ENCRYPTION_KEY no .env

# 4. Re-cifrar: descriptografar com chave velha → cifrar com nova
# (escrever script de migração de CPFs — não existe ainda)

# 5. Reiniciar após re-cifragem completa
docker compose -f docker-compose.prod.yml restart api worker
```

> **TODO:** criar script `scripts/reencrypt_cpfs.py` quando a rotação for necessária.

---

## 3. `CPF_HMAC_KEY` — Pepper HMAC-SHA256

⚠️ **Atenção:** rotacionar esta chave invalida todos os hashes de busca de CPF.
Exige re-hash de todos os registros (coluna `cpf_hash_busca`).

```bash
# 1. Gerar nova chave
NEW_KEY=$(openssl rand -hex 32)
echo "Nova CPF_HMAC_KEY: $NEW_KEY"

# 2. Atualizar .env e re-hashear todos os CPFs no banco antes de reiniciar
# (escrever script de migração)

# 3. Reiniciar após re-hash completo
docker compose -f docker-compose.prod.yml restart api worker
```

---

## 4. `TELEGRAM_BOT_TOKEN` — Alertas de Segurança

Sem impacto operacional para os usuários.

```bash
# 1. Revogar bot antigo no BotFather do Telegram (/revoke)
# 2. Criar novo token no BotFather (/newbot ou /mybots → API Token)
# 3. Atualizar TELEGRAM_BOT_TOKEN no .env
# 4. Reiniciar serviços
docker compose -f docker-compose.prod.yml restart api worker
```

---

## 5. Credenciais MinIO / S3

```bash
# 1. Criar nova access key no painel MinIO (Identities → Service Accounts)
# 2. Atualizar S3_ACCESS_KEY e S3_SECRET_KEY no .env
# 3. Reiniciar
docker compose -f docker-compose.prod.yml restart api worker
# 4. Remover a chave antiga no painel MinIO
```

---

## 6. MEK OCI Vault (criptografia de disco)

Ver `docs/oci-disk-encryption.md` para o procedimento de rotação da
Master Encryption Key no OCI Vault. A rotação cria uma nova versão da
MEK sem precisar re-cifrar os dados (o OCI faz transparentemente).

---

## Checklist de Rotação

- [ ] Gerar nova chave/credencial
- [ ] Fazer backup do `.env` atual antes de editar
- [ ] Atualizar `.env` no servidor (não commitar no git)
- [ ] Verificar impacto (re-cifragem necessária?)
- [ ] Reiniciar serviços afetados
- [ ] Verificar logs de startup para erros de validação
- [ ] Testar login/operação após reinicialização
- [ ] Revogar/apagar credencial antiga
- [ ] Guardar nova credencial no cofre Cryptomator

---

*Manter senhas mestras (GPG + Customer Secret Key Oracle) no Cryptomator — nunca no servidor.*
