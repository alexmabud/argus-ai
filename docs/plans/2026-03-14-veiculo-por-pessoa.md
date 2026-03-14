# Vínculo Veículo por Pessoa em Abordagem — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Persistir o vínculo veículo → pessoa específica na abordagem, de modo que na ficha do abordado apareçam apenas os veículos que foram efetivamente ligados a ele.

**Architecture:** Adicionar `pessoa_id` (nullable FK) em `AbordagemVeiculo`. O campo é nullable para compatibilidade com abordagens antigas (sem vínculo por pessoa). O frontend já captura `veiculoPorPessoa` — agora passará esse mapa no payload. O endpoint `GET /pessoas/{id}/abordagens` filtrará os veículos pelo `pessoa_id`, retornando apenas os do abordado consultado. Abordagens antigas (pessoa_id NULL) mostram todos os veículos para todos os abordados.

**Tech Stack:** Alembic migration, SQLAlchemy 2.0 async, Pydantic v2, Alpine.js, FastAPI

---

## Contexto do Código

- **Model:** `app/models/abordagem.py` — `AbordagemVeiculo` (linha ~123)
- **Schema:** `app/schemas/abordagem.py` — `AbordagemCreate` (linha ~32)
- **Service:** `app/services/abordagem_service.py` — step 6 `# Vincular veículos` (linha ~140)
- **API endpoint de abordagens por pessoa:** `app/api/v1/pessoas.py` — `listar_abordagens_pessoa` (linha ~307), step de veículos (linha ~350): `veiculos = [VeiculoRead.model_validate(av.veiculo) for av in ab.veiculos]`
- **Frontend payload:** `frontend/js/pages/abordagem-nova.js` linha ~685 — objeto `payload`; `veiculoPorPessoa` está no estado (linha ~403) como `{ [veiculo_id]: pessoa_id }`
- **Frontend detalhe:** `frontend/js/pages/pessoa-detalhe.js` — `carregarAbordagens()` linha ~303, coleta veículos de `ab.veiculos`
- **Migration padrão:** `alembic/versions/` — ver `1862e349651c_adicionar_bairro...py` como referência de formato
- **Gerar migration:** `python -m alembic revision --autogenerate -m "msg"` (o `make migrate-create` usa a variável `msg=`)

> ⚠️ Não há testes automatizados para frontend. Validação de frontend é manual no browser.

---

### Task 1: Migration — adicionar `pessoa_id` em `abordagem_veiculos`

**Files:**
- Create: `alembic/versions/<hash>_veiculo_pessoa_id.py` (gerado pelo alembic)

**Step 1: Gerar migration**

```bash
cd c:/projetos/argus_ai
python -m alembic revision --autogenerate -m "adicionar pessoa_id em abordagem_veiculos"
```

Isso cria um arquivo em `alembic/versions/`. Mas como o modelo ainda não foi alterado, o autogenerate pode não detectar nada. Usar migration manual:

```bash
python -m alembic revision -m "adicionar pessoa_id em abordagem_veiculos"
```

**Step 2: Editar o arquivo de migration gerado**

Abrir o arquivo criado e preencher `upgrade()` e `downgrade()`:

```python
import sqlalchemy as sa
from alembic import op

def upgrade() -> None:
    op.add_column(
        "abordagem_veiculos",
        sa.Column(
            "pessoa_id",
            sa.Integer(),
            sa.ForeignKey("pessoas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_abordagem_veiculo_pessoa",
        "abordagem_veiculos",
        ["pessoa_id"],
    )

def downgrade() -> None:
    op.drop_index("idx_abordagem_veiculo_pessoa", table_name="abordagem_veiculos")
    op.drop_column("abordagem_veiculos", "pessoa_id")
```

**Step 3: Rodar a migration**

```bash
python -m alembic upgrade head
```

Expected: sem erros, migration aplicada.

**Step 4: Verificar no banco**

```bash
docker compose exec db psql -U argus -d argus -c "\d abordagem_veiculos"
```

Expected: coluna `pessoa_id integer` aparece na lista.

**Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat(migration): adicionar pessoa_id em abordagem_veiculos"
```

---

### Task 2: Model — adicionar `pessoa_id` e `pessoa` em `AbordagemVeiculo`

**Files:**
- Modify: `app/models/abordagem.py` (classe `AbordagemVeiculo`, ~linha 123)

**Step 1: Abrir o arquivo e localizar `AbordagemVeiculo`**

```python
class AbordagemVeiculo(Base):
    __tablename__ = "abordagem_veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id", ondelete="CASCADE"))
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculos.id", ondelete="CASCADE"))

    abordagem = relationship("Abordagem", back_populates="veiculos")
    veiculo = relationship("Veiculo")

    __table_args__ = (Index("uq_abordagem_veiculo", "abordagem_id", "veiculo_id", unique=True),)
```

**Step 2: Adicionar `pessoa_id` e `pessoa` relationship**

```python
class AbordagemVeiculo(Base):
    """Associação M:N entre abordagem e veículo, com vínculo opcional por pessoa.

    Tabela de junção que materializa a relação entre uma abordagem
    e os veículos envolvidos nela. O campo pessoa_id registra qual
    abordado estava associado a este veículo (nullable para compatibilidade
    com abordagens anteriores sem esse vínculo).

    Attributes:
        id: Identificador único (chave primária).
        abordagem_id: ID da abordagem (FK, CASCADE delete).
        veiculo_id: ID do veículo (FK, CASCADE delete).
        pessoa_id: ID do abordado associado ao veículo (FK, SET NULL, nullable).
        abordagem: Relacionamento com Abordagem.
        veiculo: Relacionamento com Veiculo.
        pessoa: Relacionamento com Pessoa (opcional).

    Nota:
        - Índice único (abordagem_id, veiculo_id) evita duplicatas.
        - pessoa_id NULL = veículo sem vínculo por pessoa (abordagens antigas).
    """

    __tablename__ = "abordagem_veiculos"

    id: Mapped[int] = mapped_column(primary_key=True)
    abordagem_id: Mapped[int] = mapped_column(ForeignKey("abordagens.id", ondelete="CASCADE"))
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculos.id", ondelete="CASCADE"))
    pessoa_id: Mapped[int | None] = mapped_column(
        ForeignKey("pessoas.id", ondelete="SET NULL"), nullable=True, index=True
    )

    abordagem = relationship("Abordagem", back_populates="veiculos")
    veiculo = relationship("Veiculo")
    pessoa = relationship("Pessoa")

    __table_args__ = (Index("uq_abordagem_veiculo", "abordagem_id", "veiculo_id", unique=True),)
```

**Step 3: Verificar que o import de `ForeignKey` já existe** (já existe no arquivo — não adicionar novamente)

**Step 4: Commit**

```bash
git add app/models/abordagem.py
git commit -m "feat(model): adicionar pessoa_id em AbordagemVeiculo"
```

---

### Task 3: Schema — adicionar `veiculo_por_pessoa` em `AbordagemCreate`

**Files:**
- Modify: `app/schemas/abordagem.py` (classe `AbordagemCreate`, ~linha 32)

**Step 1: Localizar `AbordagemCreate` e adicionar o campo**

Antes:
```python
    pessoa_ids: list[int] = []
    veiculo_ids: list[int] = []
    passagens: list[PassagemVinculoCreate] = []
```

Depois:
```python
    pessoa_ids: list[int] = []
    veiculo_ids: list[int] = []
    veiculo_por_pessoa: dict[int, int] = {}
    passagens: list[PassagemVinculoCreate] = []
```

> `veiculo_por_pessoa` é um dicionário `{ veiculo_id: pessoa_id }`. Campo opcional com default `{}` para manter compatibilidade com clientes antigos (offline sync).

**Step 2: Atualizar docstring do campo em `AbordagemCreate`**

Adicionar na seção `Attributes:`:
```
        veiculo_por_pessoa: Mapeamento de veículo para pessoa abordada (dict veiculo_id → pessoa_id). Opcional.
```

**Step 3: Commit**

```bash
git add app/schemas/abordagem.py
git commit -m "feat(schema): adicionar veiculo_por_pessoa em AbordagemCreate"
```

---

### Task 4: Service — usar `veiculo_por_pessoa` ao vincular veículos

**Files:**
- Modify: `app/services/abordagem_service.py` (~linha 140, step 6)

**Step 1: Localizar o step 6 de vinculação de veículos**

```python
        # 6. Vincular veículos (AbordagemVeiculo)
        for veiculo_id in data.veiculo_ids:
            self.db.add(
                AbordagemVeiculo(
                    abordagem_id=abordagem.id,
                    veiculo_id=veiculo_id,
                )
            )
```

**Step 2: Substituir para incluir `pessoa_id` do mapa**

```python
        # 6. Vincular veículos (AbordagemVeiculo) com vínculo por pessoa se informado
        for veiculo_id in data.veiculo_ids:
            self.db.add(
                AbordagemVeiculo(
                    abordagem_id=abordagem.id,
                    veiculo_id=veiculo_id,
                    pessoa_id=data.veiculo_por_pessoa.get(veiculo_id),
                )
            )
```

> `data.veiculo_por_pessoa.get(veiculo_id)` retorna `None` se o veículo não tiver mapeamento — isso é correto para compatibilidade com abordagens antigas.

**Step 3: Verificar lint**

```bash
python -m ruff check app/services/abordagem_service.py
```

Expected: sem erros.

**Step 4: Commit**

```bash
git add app/services/abordagem_service.py
git commit -m "feat(service): salvar pessoa_id no vinculo veiculo-abordagem"
```

---

### Task 5: Frontend — enviar `veiculo_por_pessoa` no payload da abordagem

**Files:**
- Modify: `frontend/js/pages/abordagem-nova.js` (~linha 685, objeto `payload`)

**Step 1: Localizar o payload**

```js
      const payload = {
        data_hora: new Date().toISOString(),
        ...
        pessoa_ids: this.pessoaIds,
        veiculo_ids: this.veiculoIds,
        passagens: [],
      };
```

**Step 2: Adicionar `veiculo_por_pessoa`**

```js
      const payload = {
        data_hora: new Date().toISOString(),
        latitude: this.latitude,
        longitude: this.longitude,
        endereco_texto: this.endereco || null,
        observacao: obsTexto || null,
        origem: navigator.onLine ? "online" : "offline",
        client_id: this.clientId,
        pessoa_ids: this.pessoaIds,
        veiculo_ids: this.veiculoIds,
        veiculo_por_pessoa: Object.fromEntries(
          Object.entries(this.veiculoPorPessoa).filter(([, v]) => v !== null)
        ),
        passagens: [],
      };
```

> `Object.fromEntries(Object.entries(...).filter(...))` remove entradas com valor `null` (veículo desmarcado pelo usuário) antes de enviar ao backend.

**Step 3: Verificar no browser**

1. Criar nova abordagem com 2+ pessoas e 2 veículos
2. Abrir DevTools → Network → requisição POST `/abordagens`
3. Verificar que o payload contém `"veiculo_por_pessoa": {"1": 2, "3": 4}` (ids corretos)

**Step 4: Commit**

```bash
git add frontend/js/pages/abordagem-nova.js
git commit -m "feat(frontend): enviar veiculo_por_pessoa no payload de abordagem"
```

---

### Task 6: API — filtrar veículos por pessoa em `listar_abordagens_pessoa`

**Files:**
- Modify: `app/api/v1/pessoas.py` (~linha 350, dentro de `listar_abordagens_pessoa`)

**Step 1: Localizar o trecho de montagem de veículos**

```python
        veiculos = [VeiculoRead.model_validate(av.veiculo) for av in ab.veiculos]
```

**Step 2: Substituir para filtrar por `pessoa_id`**

A lógica: mostrar veículo se `av.pessoa_id == pessoa_id` (vinculado a esta pessoa) OU se `av.pessoa_id is None` (abordagem antiga, sem vínculo — mostrar para todos).

```python
        veiculos = [
            VeiculoRead.model_validate(av.veiculo)
            for av in ab.veiculos
            if av.pessoa_id is None or av.pessoa_id == pessoa_id
        ]
```

> **Atenção:** `av.veiculo` usa lazy load do relacionamento `AbordagemVeiculo.veiculo`. Como `Abordagem.veiculos` é carregado com `lazy="selectin"` e o `veiculo` do `AbordagemVeiculo` é lazy por padrão, pode ocorrer `MissingGreenlet`. Verificar se funciona ou se precisa de `selectinload` adicional (ver Task 6b abaixo).

**Step 3: Reiniciar a API e testar**

```bash
docker compose restart api
```

Abrir a ficha de uma pessoa que foi abordada junto com outra, cada uma com seu veículo. Verificar que apenas o veículo dela aparece em "Veículos Vinculados ao Abordado".

**Step 4: Se `MissingGreenlet` ocorrer** — adicionar selectinload no `listar_por_pessoa` do `AbordagemRepository`:

Localizar em `app/repositories/abordagem_repo.py` o método `listar_por_pessoa`. Verificar se `AbordagemVeiculo.veiculo` é carregado com selectin. Se não, adicionar:

```python
selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo)
```

(similar ao fix anterior em `pessoa_repo.py` para `RelacionamentoPessoa.pessoa_b`)

**Step 5: Commit**

```bash
git add app/api/v1/pessoas.py
git commit -m "fix(pessoas): filtrar veiculos por pessoa_id em listar_abordagens_pessoa"
```

---

## Verificação Final

1. Criar abordagem com 3 pessoas + 2 veículos, cada veículo vinculado a uma pessoa diferente
2. Abrir ficha da Pessoa A → "Veículos Vinculados ao Abordado" deve mostrar apenas o veículo dela
3. Abrir ficha da Pessoa B → deve mostrar apenas o veículo dela
4. Abrir ficha da Pessoa C (sem veículo vinculado) → não deve mostrar nenhum veículo
5. Abordagens antigas (sem `pessoa_id`) → todos os veículos aparecem para todos os abordados (comportamento legado OK)

---

## Checklist de Qualidade

- [ ] `pessoa_id` é nullable — compatibilidade com abordagens antigas garantida
- [ ] Frontend não envia `pessoa_id: null` no mapa (filtrado pelo `Object.fromEntries`)
- [ ] Sem `MissingGreenlet` ao acessar `av.veiculo`
- [ ] Sem erros de lint (`ruff`)
- [ ] Migration tem `downgrade()` funcional
