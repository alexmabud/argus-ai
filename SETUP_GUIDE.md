# Guia de Configuração - Argus AI

## Instalação de Dependências

### 1. Instalação Básica (Recomendado para CI/CD)
Instala apenas as dependências essenciais:

```bash
pip install -e .
```

### 2. Instalação com Desenvolvimento
Instala dependências para testes, lint e type checking:

```bash
pip install -e ".[dev]"
```

### 3. Instalação com Visão Computacional (Opcional)
Instala dependências para reconhecimento facial e OCR:

```bash
pip install -e ".[vision]"
```

**⚠️ Requer:** Microsoft Visual C++ 14.0 ou superior
- [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### 4. Instalação Completa
Todas as dependências:

```bash
pip install -e ".[dev,vision]"
```

---

## Configuração do Ambiente Local

### Pré-requisitos
- Python 3.11+
- PostgreSQL 16 com pgvector e PostGIS
- Redis 7+
- Docker e Docker Compose (recomendado)

### Passos

1. **Clone o repositório**
```bash
git clone <repo-url>
cd argus_ai
```

2. **Crie um ambiente virtual**
```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows
source .venv/bin/activate      # Linux/Mac
```

3. **Instale as dependências**
```bash
pip install -e ".[dev]"
```

4. **Configure variáveis de ambiente**
```bash
cp .env.example .env
# Edite .env com suas configurações
```

5. **Inicie os serviços**
```bash
make docker-up
```

6. **Rode as migrations**
```bash
make migrate
```

7. **Inicie o servidor**
```bash
make dev
```

---

## Comandos Úteis

```bash
# Desenvolvimento
make dev          # Inicia servidor com auto-reload
make worker       # Inicia arq worker em background

# Testes e Qualidade
make test         # Roda testes
make lint         # Ruff lint + mypy type check
make format       # Formata código com ruff

# Banco de Dados
make migrate      # Aplica migrations (ou inicializa schema se ainda não houver migration)
make init-db      # Inicializa schema direto pelo metadata SQLAlchemy
make migrate-create msg="descrição"  # Cria nova migration

# Dados
make seed         # Popula dados iniciais
make encrypt-key  # Gera chave de criptografia

# Docker
make docker-up    # Sobe containers
make docker-down  # Desce containers
make docker-logs  # Vê logs do API e worker
```

---

## Dependências Problemáticas

### insightface, easyocr, onnxruntime
Estas dependências requerem compilação C++ e podem falhar em ambientes sem:
- Visual C++ 14.0+ (Windows)
- GCC/Clang (Linux)
- Xcode (macOS)

**Solução:** Instale os [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) antes de `pip install -e ".[vision]"`

### CI/CD
O GitHub Actions foi configurado para:
- Instalar dependências opcionais com `continue-on-error: true`
- Permitir que testes rodem mesmo sem visão computacional
- Reportar vulnerabilidades sem falhar o build

---

## Troubleshooting

### Erro: "Python não configurado no VS Code"
1. `Ctrl + Shift + P` → "Python: Select Interpreter"
2. Selecione `.venv/Scripts/python.exe`

### Erro: "pip install -e ".[vision]" falha"
1. Instale [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. Reinicie o terminal
3. Tente novamente

### Erro: "PostgreSQL connection refused"
Certifique-se que PostgreSQL está rodando:
```bash
make docker-up
```

---

## Próximos Passos

- [ ] Configurar variáveis de ambiente (.env)
- [ ] Iniciar containers Docker
- [ ] Rodar migrations
- [ ] Executar testes
- [ ] Verificar linting e type checking
