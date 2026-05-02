# Política de Segurança

## 🔒 Projeto de Portfólio

**Este repositório é um projeto de demonstração técnica/portfólio.**

### ⚠️ Avisos Importantes

1. **NÃO use este código em produção sem auditoria completa de segurança**
2. **NUNCA comite dados sensíveis, chaves ou credenciais**
3. Este projeto demonstra arquitetura e boas práticas, mas não foi auditado para uso em ambiente real

---

## 🛡️ Medidas de Segurança Implementadas

### Criptografia
- ✅ **Fernet (AES-256)** para campos sensíveis (CPF)
- ✅ **SHA-256 hash** para busca sem descriptografia
- ✅ **bcrypt** para senhas de usuários
- ✅ **JWT** com refresh tokens

### LGPD Compliance
- ✅ **Soft delete** — dados nunca são removidos fisicamente
- ✅ **Audit trail** completo de todas as ações
- ✅ **Multi-tenancy** — isolamento por guarnição
- ✅ **Retenção controlada** (configurável via DATA_RETENTION_DAYS)

### Segurança de API
- ✅ **Rate limiting** via SlowAPI + Redis
- ✅ **CORS** configurável
- ✅ **Autenticação JWT** obrigatória
- ✅ **Validação** com Pydantic v2

---

## 🚨 O Que NUNCA Fazer

### ❌ Nunca Comite Estes Arquivos:
```
.env
.env.local
.env.production
*.key
*.pem
encryption.key
credentials.json
secrets.yaml
```

### ❌ Nunca Exponha:
- Chaves de API (Anthropic, Google Maps, etc.)
- SECRET_KEY do JWT
- ENCRYPTION_KEY do Fernet
- Credenciais de banco de dados
- Tokens de acesso
- Dados pessoais reais (CPF, endereços, fotos)

---

## ✅ Checklist de Segurança Para Deploy

Antes de fazer deploy em qualquer ambiente:

- [ ] Todas as chaves estão em variáveis de ambiente (nunca no código)
- [ ] `.env` está no `.gitignore` e NUNCA foi commitado
- [ ] SECRET_KEY é forte e único (gerado com `openssl rand -hex 32`)
- [ ] ENCRYPTION_KEY foi gerado com `scripts/generate_encryption_key.py`
- [ ] DEBUG=false em produção
- [ ] CORS_ORIGINS está restrito (não usar `["*"]`)
- [ ] PostgreSQL usa SSL em produção
- [ ] Redis requer autenticação
- [ ] Backups automáticos estão configurados
- [ ] Logs não expõem dados sensíveis
- [ ] Rate limiting está ativo
- [ ] HTTPS obrigatório (não aceita HTTP)

---

## 🔍 Auditoria de Segurança Recomendada

Antes de usar em produção, faça:

1. **Análise estática de código** — SAST (bandit, semgrep)
2. **Análise de dependências** — `pip-audit`, Dependabot
3. **Penetration testing** básico
4. **Code review** por especialista em segurança
5. **Auditoria LGPD** por DPO (Data Protection Officer)

---

## 📞 Reportar Vulnerabilidade

Se você encontrar uma vulnerabilidade de segurança neste projeto de portfólio:

1. **NÃO abra uma issue pública**
2. Entre em contato via email: alexmabud@gmail.com
3. Descreva a vulnerabilidade e passos para reproduzir
4. Aguarde resposta em até 48 horas

---

## 📄 Responsabilidade

**IMPORTANTE**: Este é um projeto educacional/de portfólio. O autor não se responsabiliza por:
- Uso em ambiente de produção sem auditoria adequada
- Perda de dados
- Violação de privacidade ou LGPD
- Falhas de segurança em deployments não autorizados

**Use por sua conta e risco.**

---

## 📚 Recursos de Segurança

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [LGPD - Lei Geral de Proteção de Dados](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
