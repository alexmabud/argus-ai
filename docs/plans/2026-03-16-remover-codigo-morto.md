# Remoção de Código Morto — Backend sem uso no Frontend

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remover todos os módulos e endpoints do backend que não são chamados pelo frontend, sem quebrar nada que está em uso.

**Architecture:** Remoção em 3 fases por ordem de risco: (1) módulos completamente mortos sem dependências — delete direto; (2) passagens — remoção em cascata que toca abordagem model/schema/service/repo; (3) endpoints individuais de módulos parcialmente usados.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, pytest-asyncio, arq worker

---

## MAPA DE DEPENDÊNCIAS (leia antes de começar)

```
legislacao   → isolado. Nenhum outro módulo importa.
               task embedding_generator.py → SÓ serve legislação.

passagens    → AbordagemPassagem está em app/models/abordagem.py
               → abordagem_service.py cria AbordagemPassagem
               → abordagem_repo.py faz selectinload de passagens
               → app/schemas/abordagem.py tem PassagemVinculoCreate/Read
               REMOVER nesta ordem: schema → service → repo → model → arquivos

relacionamentos → router (GET /relacionamentos/pessoa/{id}) não é usado
                → RelacionamentoService É usado por abordagem_service.py
                → RelacionamentoPessoa model É usado por pessoa.py
                REMOVER apenas o arquivo router.
```

---

## Fase 1 — Módulos completamente mortos (sem dependências externas)

### Task 1: Remover módulo Legislação

**Arquivos a deletar:**
- `app/api/v1/legislacao.py`
- `app/services/legislacao_service.py`
- `app/repositories/legislacao_repo.py`
- `app/schemas/legislacao.py`
- `app/models/legislacao.py`
- `app/tasks/embedding_generator.py`
- `scripts/seed_legislacao.py`
- `tests/integration/test_api_legislacao.py`

**Arquivos a modificar:**

**`app/api/v1/router.py`** — remover:
```python
# Remover estas 2 linhas:
from app.api.v1.legislacao import router as legislacao_router
api_router.include_router(legislacao_router)
```
Também remover "legislação" do docstring do módulo.

**`app/models/__init__.py`** — remover:
```python
# Remover esta linha:
from app.models.legislacao import Legislacao  # noqa: F401
```

**`app/worker.py`** — remover import e referência:
```python
# Remover esta linha de import:
from app.tasks.embedding_generator import gerar_embeddings_batch_task

# Na lista functions, remover gerar_embeddings_batch_task:
functions = [processar_pdf_task, processar_face_task]  # era: processar_pdf_task, gerar_embeddings_batch_task, processar_face_task
```
Também atualizar o docstring do módulo removendo menção a "geração de embeddings em batch".

**`Makefile`** — remover chamada ao seed de legislação do target `seed`:
```makefile
# Antes:
seed:
	$(PYTHON) scripts/seed_legislacao.py
	@if [ -f scripts/seed_passagens.py ]; ...

# Depois:
seed:
	@if [ -f scripts/seed_passagens.py ]; ...
```

**Verificação:**
```bash
make lint
make test
```
Expected: zero erros relacionados a `legislacao` ou `embedding_generator`.

**Commit:**
```bash
git add -A
git commit -m "refactor: remover módulo legislação (sem uso no frontend)"
```

---

### Task 2: Remover router de Relacionamentos

**ATENÇÃO:** Remover APENAS o arquivo do router. O `RelacionamentoService` e o model `RelacionamentoPessoa` continuam — são usados por `abordagem_service.py` e `pessoa.py`.

**Arquivo a deletar:**
- `app/api/v1/relacionamentos.py`

**`app/api/v1/router.py`** — remover:
```python
# Remover estas 2 linhas:
from app.api.v1.relacionamentos import router as relacionamentos_router
api_router.include_router(relacionamentos_router)
```
Também remover "relacionamentos" do docstring do módulo (a parte que descreve o router, não o conceito).

**Verificação:**
```bash
make lint
make test
```

**Commit:**
```bash
git commit -m "refactor: remover router /relacionamentos (endpoint não utilizado no frontend)"
```

---

## Fase 2 — Passagens (remoção em cascata)

Passagens está integrado no fluxo de criação de abordagem. A remoção precisa seguir a ordem exata abaixo para não quebrar imports.

### Task 3: Limpar schemas de abordagem

**Arquivo:** `app/schemas/abordagem.py`

Remover:
1. O import `from app.schemas.passagem import PassagemVinculoRead`
2. A classe `PassagemVinculoCreate` inteira
3. O campo `passagens: list[PassagemVinculoCreate] = []` de `AbordagemCreate`
4. O campo `passagens: list[PassagemVinculoRead] = []` de `AbordagemDetail`
5. Remover menções a passagens nos docstrings

**Verificação:**
```bash
python -c "from app.schemas.abordagem import AbordagemCreate, AbordagemDetail; print('OK')"
```

---

### Task 4: Limpar abordagem_service.py

**Arquivo:** `app/services/abordagem_service.py`

Remover:
1. `from app.models.abordagem import AbordagemPassagem` do import (manter os outros imports de abordagem)
2. O bloco `# 7. Vincular passagens` inteiro:
   ```python
   # 7. Vincular passagens (AbordagemPassagem com pessoa_id)
   for passagem_vinculo in data.passagens:
       db.add(
           AbordagemPassagem(
               ...
           )
       )
   ```
3. Atualizar o docstring do método `criar` removendo menção ao passo 7 de passagens.
4. Renumerar o passo 8 para 7 nos docstrings (`# 8. Materializar relacionamentos` → `# 7. Materializar relacionamentos`).

**Verificação:**
```bash
python -c "from app.services.abordagem_service import AbordagemService; print('OK')"
```

---

### Task 5: Limpar abordagem_repo.py

**Arquivo:** `app/repositories/abordagem_repo.py`

Remover:
1. `AbordagemPassagem` do import de `app.models.abordagem`
2. A linha `selectinload(Abordagem.passagens).selectinload(AbordagemPassagem.passagem),` do eager load

**Verificação:**
```bash
python -c "from app.repositories.abordagem_repo import AbordagemRepository; print('OK')"
```

---

### Task 6: Limpar app/models/abordagem.py

**Arquivo:** `app/models/abordagem.py`

Remover:
1. O relacionamento `passagens` da classe `Abordagem`:
   ```python
   passagens = relationship(
       "AbordagemPassagem",
       ...
   )
   ```
2. A classe `AbordagemPassagem` inteira (linhas ~161–195)
3. Remover `passagens` do docstring da classe `Abordagem`

**Verificação:**
```bash
python -c "from app.models.abordagem import Abordagem; print('OK')"
```

---

### Task 7: Limpar app/models/__init__.py e deletar arquivos de passagem

**`app/models/__init__.py`** — remover:
```python
# Remover estas linhas:
from app.models.abordagem import (
    AbordagemPassagem,   # ← só remover esta linha do import
    ...
)
from app.models.passagem import Passagem  # noqa: F401
```

**Arquivos a deletar:**
- `app/api/v1/passagens.py`
- `app/services/passagem_service.py`
- `app/repositories/passagem_repo.py`
- `app/schemas/passagem.py`
- `app/models/passagem.py`

**`app/api/v1/router.py`** — remover:
```python
# Remover estas 2 linhas:
from app.api.v1.passagens import router as passagens_router
api_router.include_router(passagens_router)
```

**`Makefile`** — remover a linha de seed_passagens do target `seed` (ou manter o if-check, a critério):
O Makefile já tem `@if [ -f scripts/seed_passagens.py ]; then ...` — pode deixar como está (não faz nada se o arquivo não existe).

**Verificação completa:**
```bash
make lint
make test
```
Expected: zero erros de import, todos os testes passando.

**Commit:**
```bash
git commit -m "refactor: remover módulo passagens e AbordagemPassagem (sem uso no frontend)"
```

---

## Fase 3 — Endpoints individuais sem uso no frontend

### Task 8: Auth — remover POST /register

**Arquivo:** `app/api/v1/auth.py`

Remover o endpoint `@router.post("/register", ...)` e seu handler `registrar_usuario`.
Manter: `POST /login`, `POST /refresh`, `GET /me`.

Verificar se o handler usa alguma função importada exclusivamente para ele — se sim, remover o import também.

**Verificação:**
```bash
make lint
```

---

### Task 9: Pessoas — remover PUT e DELETE

**Arquivo:** `app/api/v1/pessoas.py`

Remover:
- `@router.put("/{pessoa_id}", ...)` e seu handler
- `@router.delete("/{pessoa_id}", ...)` e seu handler

Verificar se algum schema (`PessoaUpdate`?) só é usado nesses handlers — se sim, remover do import e do arquivo `app/schemas/pessoa.py`.

**Verificação:**
```bash
make lint
make test
```

---

### Task 10: Veículos — remover endpoints de leitura/edição/exclusão

**Arquivo:** `app/api/v1/veiculos.py`

Remover:
- `GET /veiculos/` (listar)
- `GET /veiculos/{veiculo_id}` (detalhe)
- `PUT /veiculos/{veiculo_id}` (atualizar)
- `DELETE /veiculos/{veiculo_id}` (desativar)

Manter:
- `POST /veiculos/` (criação — usado no frontend)
- `GET /veiculos/localidades` (usado no frontend)

Verificar schemas exclusivos desses endpoints (`VeiculoUpdate`?) e remover se não usados em outro lugar.

**Verificação:**
```bash
make lint
make test
```

---

### Task 11: Abordagens — remover endpoints de consulta/edição

**Arquivo:** `app/api/v1/abordagens.py`

Remover:
- `GET /abordagens/raio/` (busca geoespacial por raio)
- `GET /abordagens/` (listar)
- `GET /abordagens/{abordagem_id}` (detalhe)
- `PUT /abordagens/{abordagem_id}` (atualizar)
- `POST /abordagens/{abordagem_id}/pessoas/{pessoa_id}` (vincular pessoa)
- `DELETE /abordagens/{abordagem_id}/pessoas/{pessoa_id}` (desvincular pessoa)
- `POST /abordagens/{abordagem_id}/veiculos/{veiculo_id}` (vincular veículo)
- `DELETE /abordagens/{abordagem_id}/veiculos/{veiculo_id}` (desvincular veículo)

Manter:
- `POST /abordagens/` (criação — usado no frontend)

Verificar se os métodos de service usados nesses endpoints podem ser removidos também (ex: `abordagem_service.listar`, `abordagem_service.buscar_por_raio`).

Verificar `tests/integration/test_api_abordagens.py` — remover os testes que cobrem os endpoints removidos.

**Verificação:**
```bash
make lint
make test
```

**Commit:**
```bash
git commit -m "refactor: remover endpoints de leitura/edição sem uso (pessoas, veículos, abordagens, auth/register)"
```

---

### Task 12: Ocorrências — remover GET /{id}

**Arquivo:** `app/api/v1/ocorrencias.py`

Remover:
- `GET /ocorrencias/{ocorrencia_id}` (detalhe por ID)

Manter:
- `POST /ocorrencias/`
- `GET /ocorrencias/`
- `GET /ocorrencias/buscar`

**Verificação:**
```bash
make lint
make test
```

---

### Task 13: Analytics — remover 3 endpoints não usados pelo dashboard

**Arquivo:** `app/api/v1/analytics.py`

Remover:
- `GET /analytics/resumo` (período customizado via ?dias=N)
- `GET /analytics/mapa-calor`
- `GET /analytics/horarios-pico`

Manter (usados pelo dashboard.js):
- `GET /analytics/pessoas-recorrentes`
- `GET /analytics/resumo-hoje`
- `GET /analytics/resumo-mes`
- `GET /analytics/resumo-total`
- `GET /analytics/por-dia`
- `GET /analytics/por-mes`
- `GET /analytics/dias-com-abordagem`
- `GET /analytics/pessoas-do-dia`

**`tests/integration/test_api_analytics.py`** — remover as classes de teste:
- `class TestResumoEndpoint` (testa /resumo)
- `class TestMapaCalorEndpoint` (testa /mapa-calor)
- `class TestHorariosPicoEndpoint` (testa /horarios-pico)

Verificar se os métodos de service correspondentes (`analytics_service.resumo`, `analytics_service.mapa_calor`, `analytics_service.horarios_pico`) podem ser removidos também.

**Verificação final completa:**
```bash
make lint
make test
```
Expected: todos os testes passando, zero warnings de imports.

**Commit final:**
```bash
git commit -m "refactor: remover endpoints analytics sem uso (resumo, mapa-calor, horarios-pico)"
```

---

## Resumo dos arquivos afetados

| Ação | Arquivos |
|------|---------|
| **Deletar** | `app/api/v1/legislacao.py`, `app/api/v1/passagens.py`, `app/api/v1/relacionamentos.py` |
| **Deletar** | `app/services/legislacao_service.py`, `app/services/passagem_service.py` |
| **Deletar** | `app/repositories/legislacao_repo.py`, `app/repositories/passagem_repo.py` |
| **Deletar** | `app/schemas/legislacao.py`, `app/schemas/passagem.py` |
| **Deletar** | `app/models/legislacao.py`, `app/models/passagem.py` |
| **Deletar** | `app/tasks/embedding_generator.py`, `scripts/seed_legislacao.py` |
| **Deletar** | `tests/integration/test_api_legislacao.py` |
| **Modificar** | `app/api/v1/router.py`, `app/models/__init__.py`, `app/worker.py`, `Makefile` |
| **Modificar** | `app/models/abordagem.py`, `app/schemas/abordagem.py` |
| **Modificar** | `app/services/abordagem_service.py`, `app/repositories/abordagem_repo.py` |
| **Modificar** | `app/api/v1/auth.py`, `app/api/v1/pessoas.py`, `app/api/v1/veiculos.py` |
| **Modificar** | `app/api/v1/abordagens.py`, `app/api/v1/ocorrencias.py`, `app/api/v1/analytics.py` |
| **Modificar** | `tests/integration/test_api_analytics.py`, `tests/integration/test_api_abordagens.py` |
