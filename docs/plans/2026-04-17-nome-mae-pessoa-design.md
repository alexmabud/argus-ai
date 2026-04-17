# Design — Campo `nome_mae` em Pessoa

**Data:** 2026-04-17
**Escopo:** Adicionar nome da mãe no cadastro de pessoa nova (formulário em Abordagem Nova + formulário em Consulta IA).

## Motivação

Identificação operacional de pessoas é significativamente mais precisa com o nome da mãe (evita homônimos e confirma identidade em abordagens). Hoje o cadastro só guarda nome, CPF, data de nascimento, apelido e endereço.

## Decisões

- **Opcional + buscável:** campo `nullable=True`, com índice GIN `gin_trgm_ops` preparado para busca fuzzy futura.
- **UI:** exibida em detalhes e resultados (ex: "Mãe: X" junto com "Vulgo: X"), mas a busca textual da consulta **não** dispara por nome da mãe neste momento (o índice fica preparado).
- **Ordem do formulário:** Nome → CPF → Data de Nascimento → Vulgo → **Nome da Mãe** → Endereço.

## Alterações

### Backend

**1. Model** — `app/models/pessoa.py`
- Novo campo:
  ```python
  nome_mae: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
  ```
- Novo índice GIN trgm em `__table_args__`:
  ```python
  Index(
      "idx_pessoa_nome_mae_trgm",
      "nome_mae",
      postgresql_using="gin",
      postgresql_ops={"nome_mae": "gin_trgm_ops"},
  )
  ```
- Atualizar docstring da classe para incluir o novo atributo.

**2. Schema Pydantic** — `app/schemas/pessoa.py`
- Adicionar `nome_mae: str | None = Field(None, max_length=300)` em:
  - `PessoaCreate`
  - `PessoaUpdate`
  - `PessoaResponse`
- Atualizar docstrings.

**3. Migration Alembic**
- Nova migration idempotente:
  - `ALTER TABLE pessoas ADD COLUMN IF NOT EXISTS nome_mae VARCHAR(300)`
  - `CREATE INDEX IF NOT EXISTS idx_pessoa_nome_mae_trgm ON pessoas USING gin (nome_mae gin_trgm_ops)`
- Downgrade: drop index + drop column.

### Frontend

**4. `frontend/js/pages/abordagem-nova.js`**
- Novo `<input type="text">` para `novaPessoa.nome_mae` abaixo do campo de apelido, placeholder "Nome da mãe".
- Adicionar `nome_mae: ""` em:
  - Estado inicial `novaPessoa`
  - Resets em `@click` de fechar modal (2 botões)
  - Reset após cadastro bem-sucedido
  - Reset em qualquer outro ponto onde `novaPessoa` é reinicializado (linhas 518, 609, 611, 721, 996)
- Incluir no POST: `if (this.novaPessoa.nome_mae.trim()) pessoaData.nome_mae = this.novaPessoa.nome_mae.trim();`
- Bumpar cache buster do script (padrão do projeto em fixes de frontend).

**5. `frontend/js/pages/consulta.js`**
- Mesmo input abaixo do apelido no formulário "Cadastro Pessoa".
- Adicionar `nome_mae: ""` em todos os resets do estado `novaPessoa` (linhas 26, 187, 678, 991).
- Incluir no POST: `if (this.novaPessoa.nome_mae.trim()) pessoaData.nome_mae = this.novaPessoa.nome_mae.trim();`
- Exibir nos cards de resultado (onde hoje aparece "Vulgo: X" nas linhas 110, 140, 380, 463), adicionar linha análoga:
  ```html
  <p x-show="p.nome_mae" style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);" x-text="'Mãe: ' + p.nome_mae"></p>
  ```
- Bumpar cache buster.

## Fora de escopo

- Busca textual por nome da mãe na consulta (índice fica preparado, mas implementação da query fica para outro ciclo).
- Edição de `nome_mae` em formulários de edição existentes (somente criação por enquanto).
- Exibição em `abordagem-detalhe.js` e outras telas (pode ser adicionado depois).

## Testes

- Unit: `PessoaCreate` aceita `nome_mae` vazio e preenchido respeitando `max_length=300`.
- Repository/Service: cadastro persiste `nome_mae` corretamente.
- Manual: criar pessoa nos dois formulários com/sem nome da mãe, verificar persistência e exibição em `consulta.js`.

## Riscos

- **Baixo:** coluna nullable, não quebra registros existentes.
- Migration precisa ser idempotente (padrão do projeto já adotado, ver `f300170`).
