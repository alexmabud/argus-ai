# Melhorias na Consulta em Campo — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reordenar campos de "Dados Pessoais" na ficha de pessoa e exibir data de cadastro nos resultados de endereço e veículo na consulta em campo.

**Architecture:** Mudanças 1 e 2 são puramente frontend (reordenação HTML + campo já disponível na API). Mudança 3 exige backend: novo método no repositório que retorna tupla `(Pessoa, criado_em_do_endereco)`, novo schema `PessoaComEnderecoRead` e atualização do endpoint de consulta.

**Tech Stack:** Alpine.js (frontend), FastAPI + SQLAlchemy async (backend), Pydantic v2 (schemas), pytest async (testes).

---

### Task 1: Reordenar grade "Dados Pessoais" em pessoa-detalhe

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:34-50`

Sem testes (mudança visual pura de reordenação HTML).

**Step 1: Localizar e trocar as divs de "Abordagens" e "Cadastro"**

Em [pessoa-detalhe.js:43-50](frontend/js/pages/pessoa-detalhe.js#L43-L50), a grade atual tem:

```html
<!-- linha 2, col 1 -->
<div>
  <span class="text-slate-500">Abordagens:</span>
  <span class="text-slate-300 ml-1" x-text="pessoa.abordagens_count || 0"></span>
</div>
<!-- linha 2, col 2 -->
<div>
  <span class="text-slate-500">Cadastro:</span>
  <span class="text-slate-300 ml-1" x-text="new Date(pessoa.criado_em).toLocaleDateString('pt-BR')"></span>
</div>
```

Trocar para (Cadastro primeiro, depois Abordagens):

```html
<!-- linha 2, col 1 -->
<div>
  <span class="text-slate-500">Cadastro:</span>
  <span class="text-slate-300 ml-1" x-text="new Date(pessoa.criado_em).toLocaleDateString('pt-BR')"></span>
</div>
<!-- linha 2, col 2 -->
<div>
  <span class="text-slate-500">Abordagens:</span>
  <span class="text-slate-300 ml-1" x-text="pessoa.abordagens_count || 0"></span>
</div>
```

**Step 2: Verificar visualmente no browser**

Abrir a página de detalhe de qualquer pessoa e confirmar ordem: CPF | Nascimento / Cadastro | Abordagens.

**Step 3: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): reordenar campos Cadastro/Abordagens em Dados Pessoais"
```

---

### Task 2: Exibir data de cadastro do veículo nos resultados de consulta

**Files:**
- Modify: `frontend/js/pages/consulta.js:154-168`

Sem testes (campo `criado_em` já existe em `VeiculoRead` — apenas exibição ausente).

**Step 1: Adicionar linha de data no card de veículo**

Em [consulta.js:159-160](frontend/js/pages/consulta.js#L159-L160), após a linha de modelo/cor/ano, adicionar:

```html
<p x-show="v.criado_em" class="text-xs text-slate-500"
   x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></p>
```

O bloco do card de veículo ficará:

```html
<div class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 space-y-1">
  <div class="flex items-center gap-2">
    <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="v.placa"></span>
    <span x-show="v.tipo" class="text-xs text-slate-500 bg-slate-700 px-2 py-0.5 rounded" x-text="v.tipo"></span>
  </div>
  <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
     x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
  <p x-show="v.criado_em" class="text-xs text-slate-500"
     x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></p>
  <div x-show="vinculoPorVeiculo[v.placa]" class="flex items-center gap-1 pt-0.5">
    ...
  </div>
</div>
```

**Step 2: Verificar no browser**

Buscar por uma placa e confirmar que "Cadastrado em DD/MM/AAAA" aparece no card.

**Step 3: Commit**

```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(frontend): exibir data de cadastro do veículo nos resultados"
```

---

### Task 3: Novo schema `PessoaComEnderecoRead`

**Files:**
- Modify: `app/schemas/consulta.py`

**Step 1: Adicionar schema ao arquivo**

Em `app/schemas/consulta.py`, adicionar imports e o novo schema:

```python
from datetime import datetime

from app.schemas.pessoa import PessoaRead


class PessoaComEnderecoRead(PessoaRead):
    """Pessoa com data de cadastro do endereço que gerou o match na busca.

    Estende PessoaRead com o campo endereco_criado_em, preenchido apenas
    quando a busca é feita por filtro de endereço (bairro/cidade/estado).

    Attributes:
        endereco_criado_em: Data de cadastro do endereço que originou o resultado.
    """

    endereco_criado_em: datetime | None = None
```

E atualizar `ConsultaUnificadaResponse` para usar o novo schema:

```python
class ConsultaUnificadaResponse(BaseModel):
    """..."""

    pessoas: list[PessoaComEnderecoRead] = []
    veiculos: list[VeiculoRead] = []
    abordagens: list[AbordagemRead] = []
    total_resultados: int = 0
```

`PessoaComEnderecoRead` é retrocompatível com `PessoaRead` — `endereco_criado_em` é `None` por padrão nas buscas por nome/CPF.

**Step 2: Verificar que não quebrou imports**

```bash
python -c "from app.schemas.consulta import ConsultaUnificadaResponse, PessoaComEnderecoRead; print('OK')"
```

Esperado: `OK`

**Step 3: Commit**

```bash
git add app/schemas/consulta.py
git commit -m "feat(schema): adicionar PessoaComEnderecoRead com endereco_criado_em"
```

---

### Task 4: Novo método no repositório com `criado_em` do endereço

**Files:**
- Modify: `app/repositories/pessoa_repo.py`
- Test: `tests/integration/test_api_consulta.py`

**Step 1: Escrever o teste de integração primeiro**

No arquivo `tests/integration/test_api_consulta.py`, adicionar ao final da classe `TestConsultaUnificada`:

```python
async def test_consulta_por_bairro_retorna_endereco_criado_em(
    self, client: AsyncClient, auth_headers: dict, db_session: AsyncSession, guarnicao: Guarnicao
):
    """Testa que busca por bairro retorna endereco_criado_em nos resultados.

    Args:
        client: Cliente HTTP assincrónico.
        auth_headers: Headers com Bearer token válido.
        db_session: Sessão do banco de dados de teste.
        guarnicao: Guarnição de teste.
    """
    from app.models.endereco import EnderecoPessoa
    from app.models.pessoa import Pessoa

    # Criar pessoa com endereço
    pessoa = Pessoa(nome="Teste Bairro", guarnicao_id=guarnicao.id)
    db_session.add(pessoa)
    await db_session.flush()

    endereco = EnderecoPessoa(
        pessoa_id=pessoa.id,
        endereco="Rua A, 1",
        bairro="Asa Norte",
        cidade="Brasília",
        estado="DF",
    )
    db_session.add(endereco)
    await db_session.commit()

    response = await client.get(
        "/api/v1/consultas/?q=a&tipo=pessoa&bairro=Asa+Norte",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["pessoas"]) >= 1
    pessoa_data = next(p for p in data["pessoas"] if p["nome"] == "Teste Bairro")
    assert pessoa_data["endereco_criado_em"] is not None
```

**Step 2: Rodar o teste para confirmar falha**

```bash
pytest tests/integration/test_api_consulta.py::TestConsultaUnificada::test_consulta_por_bairro_retorna_endereco_criado_em -v
```

Esperado: FAIL — `endereco_criado_em` será `null` pois o método ainda não existe.

**Step 3: Implementar o novo método no repositório**

Em `app/repositories/pessoa_repo.py`, adicionar após `search_by_bairro_cidade` (linha ~139):

```python
async def search_by_bairro_cidade_com_endereco(
    self,
    bairro: str | None,
    cidade: str | None,
    estado: str | None,
    guarnicao_id: int | None,
    skip: int = 0,
    limit: int = 20,
) -> list[tuple]:
    """Busca pessoas por bairro/cidade/estado retornando tuplas com criado_em do endereço.

    Idêntico a search_by_bairro_cidade, mas retorna também o criado_em
    do EnderecoPessoa que gerou o match, para exibição no frontend.

    Args:
        bairro: Bairro para filtrar (parcial, opcional).
        cidade: Cidade para filtrar (parcial, opcional).
        estado: Sigla UF para filtrar (parcial, opcional).
        guarnicao_id: ID da guarnição para filtro multi-tenant.
        skip: Número de registros a pular.
        limit: Número máximo de resultados.

    Returns:
        Lista de tuplas (Pessoa, endereco_criado_em: datetime).
    """
    query = (
        select(Pessoa, EnderecoPessoa.criado_em)
        .join(EnderecoPessoa, EnderecoPessoa.pessoa_id == Pessoa.id)
        .where(
            Pessoa.ativo == True,  # noqa: E712
            EnderecoPessoa.ativo == True,  # noqa: E712
        )
    )
    if bairro:
        query = query.where(EnderecoPessoa.bairro.ilike(f"%{bairro}%"))
    if cidade:
        query = query.where(EnderecoPessoa.cidade.ilike(f"%{cidade}%"))
    if estado:
        query = query.where(EnderecoPessoa.estado.ilike(f"%{estado}%"))
    if guarnicao_id is not None:
        query = query.where(Pessoa.guarnicao_id == guarnicao_id)

    query = query.distinct(Pessoa.id).offset(skip).limit(limit)
    result = await self.db.execute(query)
    return list(result.all())
```

**Step 4: Rodar o teste novamente — ainda deve falhar**

O repositório está pronto mas o endpoint ainda usa o método antigo. Esperado: FAIL — `endereco_criado_em` ainda `null`.

---

### Task 5: Atualizar endpoint de consulta para usar o novo método

**Files:**
- Modify: `app/services/consulta_service.py`
- Modify: `app/api/v1/consultas.py`

**Step 1: Atualizar `ConsultaService.busca_unificada` para usar novo método**

Em `app/services/consulta_service.py`, no bloco `if filtro_local:` (linha ~92), trocar:

```python
# ANTES
pessoas = list(
    await self.pessoa_repo.search_by_bairro_cidade(
        bairro=bairro,
        cidade=cidade,
        estado=estado,
        guarnicao_id=guarnicao_id,
        skip=skip,
        limit=limit,
    )
)
```

Por:

```python
# DEPOIS
pessoas = await self.pessoa_repo.search_by_bairro_cidade_com_endereco(
    bairro=bairro,
    cidade=cidade,
    estado=estado,
    guarnicao_id=guarnicao_id,
    skip=skip,
    limit=limit,
)
```

E no dicionário de retorno, adicionar uma flag para identificar que são tuplas:

```python
return {
    "pessoas": pessoas,
    "veiculos": veiculos,
    "abordagens": abordagens,
    "total_resultados": len(pessoas) + len(veiculos) + len(abordagens),
    "pessoas_com_endereco": filtro_local,  # True quando são tuplas (Pessoa, criado_em)
}
```

**Step 2: Atualizar o endpoint para mapear `PessoaComEnderecoRead`**

Em `app/api/v1/consultas.py`, atualizar o import do schema:

```python
from app.schemas.consulta import ConsultaUnificadaResponse, PessoaComEnderecoRead
```

E substituir o bloco de mapeamento de pessoas (linhas ~102-117):

```python
pessoas_read = []
pessoas_com_endereco = resultados.get("pessoas_com_endereco", False)

for item in resultados["pessoas"]:
    if pessoas_com_endereco:
        p, endereco_criado_em = item
    else:
        p, endereco_criado_em = item, None

    pessoas_read.append(
        PessoaComEnderecoRead(
            id=p.id,
            nome=p.nome,
            cpf_masked=PessoaService.mask_cpf(p) if p.cpf_encrypted else None,
            data_nascimento=p.data_nascimento,
            apelido=p.apelido,
            foto_principal_url=p.foto_principal_url,
            observacoes=p.observacoes,
            guarnicao_id=p.guarnicao_id,
            criado_em=p.criado_em,
            atualizado_em=p.atualizado_em,
            endereco_criado_em=endereco_criado_em,
        )
    )
```

**Step 3: Rodar o teste e confirmar que passa**

```bash
pytest tests/integration/test_api_consulta.py::TestConsultaUnificada::test_consulta_por_bairro_retorna_endereco_criado_em -v
```

Esperado: PASS

**Step 4: Rodar todos os testes de consulta**

```bash
pytest tests/integration/test_api_consulta.py -v
```

Esperado: todos PASS

**Step 5: Commit**

```bash
git add app/repositories/pessoa_repo.py app/services/consulta_service.py app/api/v1/consultas.py tests/integration/test_api_consulta.py
git commit -m "feat(consulta): retornar data de cadastro do endereço na busca por localidade"
```

---

### Task 6: Exibir data de cadastro do endereço nos resultados de consulta

**Files:**
- Modify: `frontend/js/pages/consulta.js:92-109`

**Step 1: Adicionar linha de data no card de pessoa por endereço**

Em [consulta.js:100-103](frontend/js/pages/consulta.js#L100-L103), após a linha de `cpf_masked` e `apelido`, adicionar:

```html
<p x-show="p.endereco_criado_em" class="text-xs text-slate-500"
   x-text="'Endereço cadastrado em ' + new Date(p.endereco_criado_em).toLocaleDateString('pt-BR')"></p>
```

O bloco completo do card ficará:

```html
<div @click="viewPessoa(p.id)" class="bg-slate-800/50 border border-slate-700 rounded-lg p-3 cursor-pointer hover:border-blue-500 transition-colors">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-sm font-medium text-slate-200" x-text="p.nome"></p>
      <p x-show="p.cpf_masked" class="text-xs text-slate-400" x-text="'CPF: ' + p.cpf_masked"></p>
      <p x-show="p.apelido" class="text-xs text-slate-400" x-text="'Vulgo: ' + p.apelido"></p>
      <p x-show="p.endereco_criado_em" class="text-xs text-slate-500"
         x-text="'Endereço cadastrado em ' + new Date(p.endereco_criado_em).toLocaleDateString('pt-BR')"></p>
    </div>
    <svg class="w-4 h-4 text-slate-500 shrink-0" ...>
      ...
    </svg>
  </div>
</div>
```

**Step 2: Verificar no browser**

Buscar por bairro ou cidade e confirmar que cada card de pessoa exibe "Endereço cadastrado em DD/MM/AAAA".

**Step 3: Rodar suite completa de testes**

```bash
make test
```

Esperado: todos PASS

**Step 4: Commit final**

```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(frontend): exibir data de cadastro do endereço nos resultados por localidade"
```

---

## Resumo de arquivos modificados

| Arquivo | Tipo | Tarefa |
|---------|------|--------|
| `frontend/js/pages/pessoa-detalhe.js` | Frontend | Task 1 |
| `frontend/js/pages/consulta.js` | Frontend | Tasks 2 e 6 |
| `app/schemas/consulta.py` | Schema | Task 3 |
| `app/repositories/pessoa_repo.py` | Repositório | Task 4 |
| `app/services/consulta_service.py` | Serviço | Task 5 |
| `app/api/v1/consultas.py` | Router | Task 5 |
| `tests/integration/test_api_consulta.py` | Teste | Task 4/5 |

## Verificação final

```bash
make lint   # ruff + mypy
make test   # pytest completo
```
