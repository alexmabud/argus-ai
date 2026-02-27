# Padronização do Ambiente - Argus AI

## Status: ✅ COMPLETO

Todos os comandos, execuções e instalações de dependências devem usar **exclusivamente** o ambiente virtual `.venv` do projeto.

### 1. Ambiente Virtual (.venv)

#### ✅ Localização
```
C:\projetos\argus_ai\.venv
```

#### ✅ Ativação
```bash
# Git Bash / Windows
source .venv/Scripts/activate

# CMD (Windows)
.venv\Scripts\activate.bat

# PowerShell (Windows)
.\.venv\Scripts\Activate.ps1
```

#### ✅ Verificação
```bash
# Deve mostrar .venv
which python
# Saída: /c/projetos/argus_ai/.venv/Scripts/python

python -c "import sys; print(sys.prefix)"
# Saída: C:\projetos\argus_ai\.venv
```

#### ✅ Dependências Instaladas
- **Total**: 123 pacotes
- **Core**: FastAPI, SQLAlchemy, asyncpg, Pydantic, pytest
- **ML**: sentence-transformers, torch
- **Dev**: ruff, mypy, pytest-asyncio, pre-commit
- **Storage**: aioboto3, boto3
- **Database**: pgvector, geoalchemy2, alembic

### 2. IDE - VSCode

#### ✅ Interpretador Python Configurado
**Arquivo**: `.vscode/settings.json`

```json
"python.defaultInterpreterPath": "${workspaceFolder}\\.venv\\Scripts\\python.exe"
```

- ✅ Usa caminho relativo com `${workspaceFolder}`
- ✅ Aponta para `.venv\Scripts\python.exe`
- ✅ Auto-ativa ambiente no terminal
- ✅ Formatter: ruff (com organizeImports)

#### ✅ Verificação no VSCode
1. Abrir comando: `Ctrl+Shift+P`
2. Digitar: `Python: Select Interpreter`
3. Deve aparecer: `.\.venv\Scripts\python.exe` ou similar

### 3. Conda/Anaconda

#### ✅ Status
- Conda base **NÃO** está auto-ativado
- `conda info` mostra: `active environment : None`
- Não há conflito com .venv

#### ✅ Se Precisar Desativar Conda
```bash
# Verificar configuração
conda config --show auto_activate_base

# Desativar auto-ativação (se necessário)
conda config --set auto_activate_base false
```

### 4. Boas Práticas

#### ✅ SEMPRE Fazer Antes de Trabalhar
```bash
cd c:\projetos\argus_ai
source .venv/Scripts/activate
```

#### ✅ Instalar Dependências
```bash
# Sempre com pip (dentro do .venv)
pip install pacote

# NUNCA usar:
# pip install --user pacote  ← instala globalmente
# conda install pacote        ← instala no Conda
```

#### ✅ Rodar Testes
```bash
source .venv/Scripts/activate
pytest --cov=app -v
```

#### ✅ Executar Aplicação
```bash
source .venv/Scripts/activate
python -m app.main

# Ou com FastAPI dev server
uvicorn app.main:app --reload
```

#### ✅ Executar Scripts
```bash
source .venv/Scripts/activate
python scripts/atualizar_legislacao.py
```

### 5. Verificação Rápida

Use este script para validar o ambiente:

```bash
#!/bin/bash
cd c:/projetos/argus_ai
source .venv/Scripts/activate

echo "=== Verificação de Ambiente ==="
echo "Python: $(which python)"
echo "Prefix: $(python -c 'import sys; print(sys.prefix)')"
echo "Pacotes: $(pip list | wc -l)"

# Verificar dependências críticas
python -c "
import fastapi, sqlalchemy, pytest, ruff, mypy
print('Todos os pacotes críticos OK')
"
```

### 6. Problemas Comuns

#### Problema: "ModuleNotFoundError: No module named 'app'"
**Solução**: Verificar se .venv está ativado
```bash
which python  # deve ser .venv/Scripts/python
```

#### Problema: VSCode mostra interpretador errado
**Solução**:
1. Abrir Command Palette: `Ctrl+Shift+P`
2. `Python: Clear Cache`
3. Reselecionar interpretador

#### Problema: pip não encontra pacote
**Solução**: Verificar se está usando pip do .venv
```bash
which pip  # deve ser .venv/Scripts/pip
```

### 7. GitHub Actions

GitHub Actions usa **serviços de container** para PostgreSQL/Redis:
- ✅ Independente do ambiente local
- ✅ Python 3.11 instalado via `setup-python@v5`
- ✅ Dependências instaladas via pip no CI workflow
- ✅ Suporta `continue-on-error` para deps opcionais

### 8. Documentação Relacionada

- [CLAUDE.md](./CLAUDE.md) - Stack técnico e convenções
- [.github/workflows/ci.yml](.github/workflows/ci.yml) - GitHub Actions CI/CD
- [pyproject.toml](./pyproject.toml) - Configuração pytest

---

**Última atualização**: 27 de Fevereiro de 2026
**Status**: ✅ Ambiente totalmente padronizado para .venv
