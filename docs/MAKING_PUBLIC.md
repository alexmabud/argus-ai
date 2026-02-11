# 🌐 Checklist: Tornar o Repositório Público

## ✅ Antes de Tornar Público

### 1. Verificar Histórico do Git

```bash
# Procurar por arquivos sensíveis no histórico
git log --all --full-history --pretty=format: --name-only | grep -E '\.env$|\.key$|\.pem$'

# Se encontrar algo, você precisa limpar o histórico:
# (CUIDADO: isso reescreve o histórico)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

### 2. Verificar Segredos no Código

```bash
# Instalar detect-secrets
pip install detect-secrets

# Criar baseline
detect-secrets scan > .secrets.baseline

# Auditar baseline
detect-secrets audit .secrets.baseline
```

### 3. Verificar .gitignore

Certifique-se de que está ignorando:

```gitignore
# Já incluído no .gitignore do projeto
.env
.env.*
*.key
*.pem
encryption.key
*.log
pgdata/
redisdata/
uploads/
*.pdf
*.jpg (exceto icons)
```

### 4. Revisar Todos os Commits

```bash
# Listar commits recentes
git log --oneline -20

# Verificar diff de cada commit
git show <commit-hash>
```

### 5. Sanitizar Dados de Exemplo

- ✅ Certifique-se de que NÃO há dados reais em:
  - `scripts/seed_*.py` (quando criar)
  - Arquivos de teste
  - Fixtures
  - Exemplos na documentação

### 6. Atualizar Documentação

- ✅ README.md tem aviso de segurança
- ✅ SECURITY.md criado
- ✅ LICENSE criada (MIT)
- ✅ DATA_SANITIZATION.md criado

---

## 🚀 Passos Para Tornar Público

### 1. GitHub — Configurações do Repositório

```
1. Vá em: Settings → General → Danger Zone
2. Clique em "Change repository visibility"
3. Selecione "Make public"
4. Digite o nome do repositório para confirmar
5. Clique em "I understand, make this repository public"
```

### 2. Ativar GitHub Actions

```
1. Vá em: Settings → Actions → General
2. Em "Actions permissions", selecione:
   ✅ "Allow all actions and reusable workflows"
3. Salvar
```

### 3. Configurar Secrets (para CI)

```
1. Vá em: Settings → Secrets and variables → Actions
2. Adicione secrets APENAS para CI:
   - DATABASE_URL (test database)
   - SECRET_KEY (random, só para testes)
   - ENCRYPTION_KEY (random, só para testes)
```

**IMPORTANTE:** NUNCA adicione secrets de produção aqui!

### 4. Ativar Dependabot

```
1. Vá em: Settings → Security → Code security and analysis
2. Ative:
   ✅ Dependency graph
   ✅ Dependabot alerts
   ✅ Dependabot security updates
```

### 5. Adicionar Badges ao README

```markdown
![CI](https://github.com/SEU_USER/argus-ai/workflows/CI/badge.svg)
![Security](https://github.com/SEU_USER/argus-ai/workflows/Security%20Checks/badge.svg)
```

---

## 📋 Checklist Final (IMPRIMA ISSO)

Antes de clicar em "Make Public":

- [ ] Rodei `git log` e NÃO encontrei .env ou chaves
- [ ] `.gitignore` está correto
- [ ] `.env.example` existe (sem valores reais)
- [ ] README.md tem aviso de portfólio/demo
- [ ] SECURITY.md está criado
- [ ] LICENSE está criado
- [ ] NÃO há dados pessoais reais no código
- [ ] NÃO há fotos de pessoas reais
- [ ] NÃO há CPFs, RGs ou documentos reais
- [ ] NÃO há endereços residenciais reais
- [ ] Pre-commit hooks instalados
- [ ] Rodei `detect-secrets scan`
- [ ] Revisei todos os arquivos .py
- [ ] Revisei todos os arquivos .md
- [ ] Revisei migrations (quando criar)
- [ ] Revisei seeds (quando criar)
- [ ] GitHub Actions configurado
- [ ] Badges atualizados

---

## 🎯 Para o LinkedIn

Quando postar no LinkedIn:

### Post Sugerido:

```
🚀 Novo Projeto de Portfólio: Argus AI

Sistema de apoio operacional com IA que demonstra:

✅ FastAPI + SQLAlchemy 2.0 async
✅ PostgreSQL com pgvector (RAG) + PostGIS (geoespacial)
✅ Arquitetura limpa (API → Service → Repository)
✅ LGPD-compliant by design (criptografia, audit trail)
✅ Multi-tenancy + autenticação JWT
✅ PWA offline-first
✅ Background tasks com arq worker

Stack: Python 3.11+ | FastAPI | PostgreSQL 16 | Redis | Docker

⚠️ Projeto educacional/demonstração técnica
Não use em produção sem auditoria de segurança

🔗 GitHub: [link]

#Python #FastAPI #PostgreSQL #AI #MachineLearning #RAG #SoftwareArchitecture
```

### Screenshot Recomendado:

- Arquitetura (diagrama do README)
- Código limpo (exemplo de service layer)
- Docker compose up (demonstração)

**NÃO mostre:**
- Dados reais
- Chaves de API
- Tela de login com credenciais

---

## 🛡️ Manutenção Pós-Publicação

### Semanal:
- [ ] Verificar Dependabot alerts
- [ ] Revisar novos commits

### Mensal:
- [ ] Rodar `pip-audit`
- [ ] Rodar `bandit -r app/`
- [ ] Verificar issues abertas

### Sempre que receber PR externo:
- [ ] Revisar mudanças cuidadosamente
- [ ] Verificar se não introduz vulnerabilidades
- [ ] Rodar testes localmente

---

## 🚨 O Que Fazer em Caso de Vazamento

Se você acidentalmente commitou algo sensível:

### 1. Remover do GitHub IMEDIATAMENTE

```bash
# Se foi no último commit
git reset --hard HEAD~1
git push --force

# Se foi em commits antigos
# Use BFG Repo-Cleaner ou git filter-branch
```

### 2. Rotacionar Todas as Chaves

- Gere novas chaves de API
- Gere novo SECRET_KEY
- Gere novo ENCRYPTION_KEY
- Atualize em todos os ambientes

### 3. Notificar

Se dados de terceiros vazaram:
- Notificar as pessoas afetadas
- Seguir procedimentos da LGPD

---

## 📚 Recursos

- [GitHub: Making a private repository public](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility#making-a-private-repository-public)
- [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
