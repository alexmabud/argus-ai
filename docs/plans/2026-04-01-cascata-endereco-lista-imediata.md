# Cascata Endereço — Lista Imediata + Filtro ao Digitar

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ao selecionar o estado no form de cadastro de pessoa, listar imediatamente todas as cidades cadastradas (sem precisar digitar); ao selecionar a cidade, listar todos os bairros cadastrados. Digitar filtra a lista (a partir de 1 caractere).

**Architecture:** Tornar `q` opcional no endpoint `/localidades`. Quando ausente, retorna todos os filhos do `parent_id`. No frontend, disparar a busca imediatamente ao selecionar estado/cidade, sem aguardar digitação.

**Tech Stack:** FastAPI, SQLAlchemy async, Alpine.js

---

### Task 1: Backend — `q` opcional no repository

**Files:**
- Modify: `app/repositories/localidade_repo.py:41-73`

**Step 1: Escrever o teste que falha**

Em `tests/unit/test_localidade_repo.py` (ou criar se não existir), adicionar:

```python
async def test_autocomplete_sem_q_retorna_todos(db_session, estado_seed):
    """Sem q, retorna todos os filhos do parent_id."""
    # Criar 3 cidades no estado
    from app.models.localidade import Localidade
    for nome in ["alfa", "beta", "gamma"]:
        db_session.add(Localidade(nome=nome, nome_exibicao=nome.capitalize(), tipo="cidade", parent_id=estado_seed.id))
    await db_session.commit()

    from app.repositories.localidade_repo import LocalidadeRepository
    repo = LocalidadeRepository(db_session)
    result = await repo.autocomplete(tipo="cidade", parent_id=estado_seed.id, q=None)
    assert len(result) == 3
```

**Step 2: Rodar e confirmar falha**

```bash
make test
```
Esperado: FAIL — `autocomplete` não aceita `q=None`.

**Step 3: Implementar**

Em `app/repositories/localidade_repo.py`, alterar a assinatura e o body do método `autocomplete`:

```python
async def autocomplete(
    self,
    tipo: str,
    parent_id: int,
    q: str | None = None,
    limit: int = 200,
) -> list[Localidade]:
    """Retorna localidades filtradas por texto ou todas as filhas do parent.

    Quando q é None ou vazio, retorna todos os filhos do parent_id (até limit).
    Quando q é fornecido, filtra por nome com ILIKE.

    Args:
        tipo: Tipo da localidade ('cidade' ou 'bairro').
        parent_id: ID da localidade pai.
        q: Texto de busca opcional (sem mínimo de caracteres).
        limit: Número máximo de resultados (padrão: 200).

    Returns:
        Lista de localidades ordenadas por nome_exibicao.
    """
    query = select(Localidade).where(
        Localidade.tipo == tipo,
        Localidade.parent_id == parent_id,
        Localidade.ativo.is_(True),
    )
    if q:
        query = query.where(Localidade.nome.ilike(f"%{q}%"))
    query = query.order_by(Localidade.nome_exibicao).limit(limit)
    result = await self.db.execute(query)
    return list(result.scalars().all())
```

**Step 4: Rodar e confirmar passou**

```bash
make test
```
Esperado: PASS.

**Step 5: Commit**

```bash
git add app/repositories/localidade_repo.py tests/
git commit -m "feat(localidade): q opcional no autocomplete — lista todos quando ausente"
```

---

### Task 2: Backend — `q` opcional no service e router

**Files:**
- Modify: `app/services/localidade_service.py:60-76`
- Modify: `app/api/v1/localidades.py:19-56`

**Step 1: Alterar o service**

Em `app/services/localidade_service.py`, método `autocomplete`:

```python
async def autocomplete(
    self,
    tipo: str,
    parent_id: int,
    q: str | None = None,
) -> list[Localidade]:
    """Autocomplete de cidades ou bairros, com ou sem filtro de texto.

    Quando q é None, retorna todas as localidades do parent_id.
    Quando q é fornecido, normaliza e filtra por texto.

    Args:
        tipo: 'cidade' ou 'bairro'.
        parent_id: ID do estado (para cidades) ou cidade (para bairros).
        q: Texto opcional para filtrar.

    Returns:
        Lista de localidades correspondentes.
    """
    q_normalizado = _normalizar(q) if q else None
    return await self.repo.autocomplete(tipo=tipo, parent_id=parent_id, q=q_normalizado)
```

**Step 2: Alterar o router**

Em `app/api/v1/localidades.py`, endpoint `listar_localidades`:

- Remover `min_length=2` do parâmetro `q`
- Remover a validação que rejeita quando `q is None`
- Manter obrigatoriedade de `parent_id` para cidade/bairro

```python
@router.get("", response_model=list[LocalidadeRead])
async def listar_localidades(
    tipo: str = Query(..., pattern="^(estado|cidade|bairro)$"),
    parent_id: int | None = Query(None),
    q: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
) -> list[LocalidadeRead]:
    """Lista estados ou retorna cidades/bairros com filtro opcional.

    Para tipo='estado': retorna todos os 27 estados.
    Para tipo='cidade' ou 'bairro': retorna filhos do parent_id.
      - Sem q: retorna todos (até 200).
      - Com q: filtra por texto (1+ caractere).

    Args:
        tipo: Nível hierárquico — 'estado', 'cidade' ou 'bairro'.
        parent_id: ID da localidade pai (obrigatório para cidade e bairro).
        q: Texto de busca opcional.
        db: Sessão do banco de dados.
        _: Usuário autenticado.

    Returns:
        Lista de localidades correspondentes.

    Raises:
        HTTPException 400: Quando parent_id ausente para cidade/bairro.
    """
    service = LocalidadeService(db)

    if tipo == "estado":
        return await service.listar_estados()

    if parent_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parent_id é obrigatório para cidade e bairro.",
        )

    return await service.autocomplete(tipo=tipo, parent_id=parent_id, q=q)
```

**Step 3: Rodar testes**

```bash
make test
```
Esperado: todos passando.

**Step 4: Commit**

```bash
git add app/services/localidade_service.py app/api/v1/localidades.py
git commit -m "feat(localidade): q opcional no service e router"
```

---

### Task 3: Frontend — disparar busca imediata ao selecionar estado/cidade

**Files:**
- Modify: `frontend/js/pages/consulta.js`

**Step 1: Alterar `cpBuscarCidades` para não exigir 2 chars**

Localizar a função `cpBuscarCidades` (linha ~900) e substituir:

```js
async cpBuscarCidades() {
  const q = this.cpCidadeTexto.trim();
  if (!this.cpEstadoId) { this.cpCidadeSugestoes = []; this.cpCidadeCadastrarNovo = false; return; }
  try {
    const url = q.length >= 1
      ? `/localidades?tipo=cidade&parent_id=${this.cpEstadoId}&q=${encodeURIComponent(q)}`
      : `/localidades?tipo=cidade&parent_id=${this.cpEstadoId}`;
    const r = await api.get(url);
    this.cpCidadeSugestoes = r;
    this.cpCidadeCadastrarNovo = q.length >= 1 && r.length === 0;
  } catch (e) { console.error(e); }
},
```

**Step 2: Alterar `cpBuscarBairros` para não exigir 2 chars**

Localizar a função `cpBuscarBairros` (linha ~909) e substituir:

```js
async cpBuscarBairros() {
  const q = this.cpBairroTexto.trim();
  if (!this.cpCidadeId) { this.cpBairroSugestoes = []; this.cpBairroCadastrarNovo = false; return; }
  try {
    const url = q.length >= 1
      ? `/localidades?tipo=bairro&parent_id=${this.cpCidadeId}&q=${encodeURIComponent(q)}`
      : `/localidades?tipo=bairro&parent_id=${this.cpCidadeId}`;
    const r = await api.get(url);
    this.cpBairroSugestoes = r;
    this.cpBairroCadastrarNovo = q.length >= 1 && r.length === 0;
  } catch (e) { console.error(e); }
},
```

**Step 3: Disparar busca imediata ao selecionar estado**

No `<select>` de estado (linha ~223 do template), o `@change` já limpa cidade/bairro. Adicionar chamada a `cpBuscarCidades()` no final:

```
@change="cpCidadeId=null;cpCidadeTexto='';cpBairroId=null;cpBairroTexto='';cpCidadeSugestoes=[];cpBairroSugestoes=[];cpBuscarCidades()"
```

**Step 4: Disparar busca imediata ao selecionar cidade**

Em `cpSelecionarCidade` (linha ~918), adicionar chamada para pré-carregar bairros:

```js
cpSelecionarCidade(cidade) {
  this.cpCidadeId = cidade.id; this.cpCidadeTexto = cidade.nome_exibicao;
  this.cpCidadeSugestoes = []; this.cpCidadeCadastrarNovo = false;
  this.cpBairroId = null; this.cpBairroTexto = '';
  this.cpBuscarBairros();
},
```

**Step 5: Mostrar sugestões ao focar nos campos (sem precisar digitar)**

No campo de cidade (linha ~234), adicionar `@focus="cpBuscarCidades()"`:

```html
<input type="text" x-model="cpCidadeTexto" :disabled="!cpEstadoId"
       @focus="cpBuscarCidades()"
       @input.debounce.300ms="cpBuscarCidades()"
       @blur.debounce.200ms="cpCidadeSugestoes=[]"
```

No campo de bairro (linha ~257), adicionar `@focus="cpBuscarBairros()"`:

```html
<input type="text" x-model="cpBairroTexto" :disabled="!cpCidadeId"
       @focus="cpBuscarBairros()"
       @input.debounce.300ms="cpBuscarBairros()"
       @blur.debounce.200ms="cpBairroSugestoes=[]"
```

**Step 6: Commit**

```bash
git add frontend/js/pages/consulta.js
git commit -m "feat(frontend): lista imediata de cidades e bairros ao selecionar estado/cidade"
```

---

### Task 4: Verificação manual

1. Abrir o form de cadastro de pessoa em `/consultas`
2. Selecionar um estado → lista de cidades deve aparecer imediatamente
3. Digitar uma letra → lista filtra
4. Selecionar uma cidade → lista de bairros aparece imediatamente
5. Digitar uma letra → lista filtra
6. Tentar cadastrar cidade inexistente → opção "+ Cadastrar" aparece
7. Verificar que estados sem cidade cadastrada mostram lista vazia (não erro)
