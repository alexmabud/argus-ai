# Policial no Card de Abordagem — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir `posto_graduacao` + `nome_guerra` do policial no canto direito da linha de data/hora de cada card de abordagem na página de relatórios.

**Architecture:** Adicionar schema `UsuarioResumoRead` em `auth.py`, incluir campo `usuario` no `AbordagemDetail`, adicionar `relationship("Usuario", lazy="selectin")` no model `Abordagem` (sem migration — FK já existe), e ajustar a linha de data/hora no frontend para flex com nome à direita.

**Tech Stack:** Python/Pydantic (schemas), SQLAlchemy async (model relationship), Alpine.js (frontend)

---

### Task 1: Schema `UsuarioResumoRead`

**Files:**
- Modify: `app/schemas/auth.py:109` (adicionar após `UsuarioRead`)
- Test: `tests/unit/test_schemas_abordagem.py`

**Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/unit/test_schemas_abordagem.py`:

```python
class TestUsuarioResumoRead:
    """Testes do schema UsuarioResumoRead."""

    def test_campos_existem(self):
        """Testa que UsuarioResumoRead tem id, posto_graduacao e nome_guerra."""
        from app.schemas.auth import UsuarioResumoRead

        fields = UsuarioResumoRead.model_fields
        assert "id" in fields
        assert "posto_graduacao" in fields
        assert "nome_guerra" in fields

    def test_serializa_de_dict(self):
        """Testa que UsuarioResumoRead serializa corretamente."""
        from app.schemas.auth import UsuarioResumoRead

        schema = UsuarioResumoRead(id=1, posto_graduacao="SD", nome_guerra="Silva")
        assert schema.id == 1
        assert schema.posto_graduacao == "SD"
        assert schema.nome_guerra == "Silva"

    def test_campos_opcionais_aceitam_none(self):
        """Testa que posto_graduacao e nome_guerra aceitam None."""
        from app.schemas.auth import UsuarioResumoRead

        schema = UsuarioResumoRead(id=1, posto_graduacao=None, nome_guerra=None)
        assert schema.posto_graduacao is None
        assert schema.nome_guerra is None
```

**Step 2: Rodar o teste para confirmar que falha**

```bash
pytest tests/unit/test_schemas_abordagem.py::TestUsuarioResumoRead -v
```

Esperado: `FAILED` com `ImportError: cannot import name 'UsuarioResumoRead'`

**Step 3: Implementar o schema**

Em `app/schemas/auth.py`, adicionar após a classe `UsuarioRead` (linha ~141), antes de `GuarnicaoRead`:

```python
class UsuarioResumoRead(BaseModel):
    """Dados mínimos de usuário para exibição em cards de abordagem.

    Versão compacta de UsuarioRead com apenas os campos necessários
    para identificar o policial em listas e relatórios.

    Attributes:
        id: Identificador único do usuário.
        posto_graduacao: Posto ou graduação abreviado (ex: "SD", "CB", "3SGT").
        nome_guerra: Nome de guerra do agente (ex: "Silva").
    """

    id: int
    posto_graduacao: str | None = None
    nome_guerra: str | None = None

    model_config = {"from_attributes": True}
```

**Step 4: Rodar o teste para confirmar que passa**

```bash
pytest tests/unit/test_schemas_abordagem.py::TestUsuarioResumoRead -v
```

Esperado: `3 passed`

**Step 5: Commit**

```bash
git add app/schemas/auth.py tests/unit/test_schemas_abordagem.py
git commit -m "feat(schemas): adicionar UsuarioResumoRead para exibição em cards"
```

---

### Task 2: Campo `usuario` no `AbordagemDetail` + relationship no model

**Files:**
- Modify: `app/schemas/abordagem.py:130` (classe `AbordagemDetail`)
- Modify: `app/models/abordagem.py:73` (após `ocorrencias` relationship)
- Test: `tests/unit/test_schemas_abordagem.py`

**Step 1: Escrever o teste que falha**

Adicionar ao final de `TestAbordagemDetail` em `tests/unit/test_schemas_abordagem.py`:

```python
    def test_usuario_field_existe(self):
        """Testa que AbordagemDetail tem o campo usuario."""
        from app.schemas.auth import UsuarioResumoRead

        fields = AbordagemDetail.model_fields
        assert "usuario" in fields
        # campo deve ser opcional (None quando usuário não carregado)
        field = fields["usuario"]
        assert field.default is None
```

**Step 2: Rodar o teste para confirmar que falha**

```bash
pytest tests/unit/test_schemas_abordagem.py::TestAbordagemDetail::test_usuario_field_existe -v
```

Esperado: `FAILED` com `AssertionError: 'usuario' not in fields`

**Step 3: Adicionar import e campo no schema**

Em `app/schemas/abordagem.py`:

1. Adicionar import no topo (após os imports existentes):
```python
from app.schemas.auth import UsuarioResumoRead
```

2. Adicionar campo `usuario` na classe `AbordagemDetail` e atualizar docstring:

```python
class AbordagemDetail(AbordagemRead):
    """Dados detalhados de uma abordagem com todos os relacionamentos.

    Estende AbordagemRead com pessoas, veículos, fotos, ocorrências vinculadas
    e dados resumidos do policial que realizou a abordagem.

    Attributes:
        pessoas: Lista de pessoas abordadas (versão compacta).
        veiculos: Lista de veículos envolvidos com pessoa associada.
        fotos: Lista de fotos registradas (inclui mídias).
        ocorrencias: Lista de ocorrências (RAPs) vinculadas.
        usuario: Dados resumidos do policial (posto_graduacao, nome_guerra).
    """

    pessoas: list[PessoaAbordagemRead] = []
    veiculos: list[VeiculoAbordagemRead] = []
    fotos: list[FotoRead] = []
    ocorrencias: list[OcorrenciaRead] = []
    usuario: UsuarioResumoRead | None = None
```

**Step 4: Adicionar relationship no model `Abordagem`**

Em `app/models/abordagem.py`, adicionar após a linha `ocorrencias = relationship(...)` (linha 73):

```python
    usuario = relationship("Usuario", lazy="selectin", foreign_keys=[usuario_id])
```

Atualizar também o docstring da classe `Abordagem` — adicionar na seção `Attributes`:
```
        usuario: Relacionamento com Usuario (policial que realizou).
```

**Step 5: Rodar o teste para confirmar que passa**

```bash
pytest tests/unit/test_schemas_abordagem.py -v
```

Esperado: todos os testes passando, incluindo `test_usuario_field_existe`

**Step 6: Rodar suite completa de testes**

```bash
pytest tests/ -x -q
```

Esperado: nenhum teste novo falhando

**Step 7: Commit**

```bash
git add app/schemas/abordagem.py app/models/abordagem.py tests/unit/test_schemas_abordagem.py
git commit -m "feat(abordagem): incluir policial (usuario) no AbordagemDetail"
```

---

### Task 3: Frontend — nome do policial na linha de data/hora

**Files:**
- Modify: `frontend/js/pages/ocorrencias.js:130-132`

**Step 1: Localizar o trecho exato**

No arquivo `frontend/js/pages/ocorrencias.js`, o bloco de info (linha ~130) é:

```html
<!-- Info -->
<div style="flex:1;min-width:0;">
  <div style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);letter-spacing:0.08em;"
       x-text="formatarDataHora(ab.data_hora)"></div>
```

**Step 2: Substituir a div de data/hora por flex row**

Trocar as linhas 131-132 (a div de data/hora) por:

```html
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-family:var(--font-display);font-size:10px;color:var(--color-primary);letter-spacing:0.08em;"
                      x-text="formatarDataHora(ab.data_hora)"></span>
                <span x-show="ab.usuario && ab.usuario.nome_guerra"
                      style="font-family:var(--font-display);font-size:10px;color:rgba(255,255,255,0.45);letter-spacing:0.06em;"
                      x-text="(ab.usuario && ab.usuario.posto_graduacao ? ab.usuario.posto_graduacao + ' ' : '') + (ab.usuario && ab.usuario.nome_guerra ? ab.usuario.nome_guerra : '')"></span>
              </div>
```

**Step 3: Verificar visualmente**

Com o servidor rodando (`make dev`), abrir a página de relatórios, selecionar um dia com abordagens e confirmar:
- Data/hora aparece em azul à esquerda
- `SD João Silva` (ou o nome do policial) aparece em branco suave à direita
- Cards sem `usuario.nome_guerra` preenchido não mostram nada à direita
- Clicar no card ainda abre o detalhe normalmente

**Step 4: Commit**

```bash
git add frontend/js/pages/ocorrencias.js
git commit -m "feat(relatorios): exibir policial no card de abordagem"
```
