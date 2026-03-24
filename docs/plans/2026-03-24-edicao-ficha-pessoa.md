# Edição de Ficha de Pessoa — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Permitir edição de dados pessoais e endereços na ficha de pessoa em Consultas, via modais.

**Architecture:** Dois novos endpoints PATCH no backend (pessoa + endereço) expondo lógica já existente no service. Frontend ganha dois modais (dados pessoais + endereço) com formulários pré-preenchidos. Modal de endereço reutilizado para criação e edição.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, Alpine.js, vanilla JS

---

### Task 1: Schema EnderecoUpdate

**Files:**
- Modify: `app/schemas/pessoa.py:90-111`

**Step 1: Adicionar schema EnderecoUpdate após EnderecoCreate**

No arquivo `app/schemas/pessoa.py`, adicionar após a classe `EnderecoCreate` (linha ~111):

```python
class EnderecoUpdate(BaseModel):
    """Requisição de atualização parcial de endereço.

    Todos os campos são opcionais. Apenas os campos enviados serão atualizados.

    Attributes:
        endereco: Logradouro e número atualizado.
        bairro: Bairro atualizado.
        cidade: Cidade atualizada.
        estado: Sigla UF atualizada.
        latitude: Latitude GPS atualizada.
        longitude: Longitude GPS atualizada.
        data_inicio: Data de início atualizada.
        data_fim: Data de fim atualizada.
    """

    endereco: str | None = Field(None, min_length=1, max_length=500)
    bairro: str | None = Field(None, max_length=200)
    cidade: str | None = Field(None, max_length=200)
    estado: str | None = Field(None, max_length=2)
    latitude: float | None = None
    longitude: float | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
```

**Step 2: Commit**

```bash
git add app/schemas/pessoa.py
git commit -m "feat(schemas): adicionar EnderecoUpdate para edição parcial de endereço"
```

---

### Task 2: Método atualizar_endereco no PessoaService

**Files:**
- Modify: `app/services/pessoa_service.py`
- Modify: `app/schemas/pessoa.py` (import no service)

**Step 1: Adicionar import de EnderecoUpdate no service**

No arquivo `app/services/pessoa_service.py`, atualizar o import (linha 22):

```python
from app.schemas.pessoa import EnderecoCreate, EnderecoUpdate, PessoaCreate, PessoaUpdate
```

**Step 2: Adicionar método atualizar_endereco após adicionar_endereco**

No arquivo `app/services/pessoa_service.py`, adicionar após o método `adicionar_endereco` (após linha ~344):

```python
    async def atualizar_endereco(
        self,
        pessoa_id: int,
        endereco_id: int,
        data: EnderecoUpdate,
        user: Usuario,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> EnderecoPessoa:
        """Atualiza endereço existente de uma pessoa.

        Se latitude e longitude forem informadas, atualiza o ponto PostGIS.
        Registra auditoria com campos alterados.

        Args:
            pessoa_id: ID da pessoa dona do endereço.
            endereco_id: ID do endereço a atualizar.
            data: Dados de atualização parcial.
            user: Usuário autenticado (para verificação de tenant).
            ip_address: Endereço IP da requisição (opcional).
            user_agent: User-Agent do cliente (opcional).

        Returns:
            Endereço atualizado.

        Raises:
            NaoEncontradoError: Se pessoa ou endereço não existe.
            AcessoNegadoError: Se pessoa pertence a outra guarnição.
        """
        pessoa = await self.repo.get(pessoa_id)
        if not pessoa:
            raise NaoEncontradoError("Pessoa")
        TenantFilter.check_ownership(pessoa, user)

        result = await self.db.execute(
            select(EnderecoPessoa).where(
                EnderecoPessoa.id == endereco_id,
                EnderecoPessoa.pessoa_id == pessoa_id,
                EnderecoPessoa.ativo == True,  # noqa: E712
            )
        )
        endereco = result.scalar_one_or_none()
        if not endereco:
            raise NaoEncontradoError("Endereço")

        update_data = data.model_dump(exclude_unset=True)

        # Atualizar geometria PostGIS se coordenadas mudaram
        lat = update_data.pop("latitude", None)
        lng = update_data.pop("longitude", None)
        if lat is not None and lng is not None:
            endereco.localizacao = f"POINT({lng} {lat})"

        for field, value in update_data.items():
            setattr(endereco, field, value)

        await self.db.flush()

        await self.audit.log(
            usuario_id=user.id,
            acao="UPDATE",
            recurso="endereco",
            recurso_id=endereco.id,
            detalhes={"campos_alterados": list(data.model_dump(exclude_unset=True).keys())},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return endereco
```

**Step 3: Commit**

```bash
git add app/services/pessoa_service.py
git commit -m "feat(service): adicionar atualizar_endereco com PostGIS e audit"
```

---

### Task 3: Endpoints PATCH no router

**Files:**
- Modify: `app/api/v1/pessoas.py`

**Step 1: Atualizar imports**

No arquivo `app/api/v1/pessoas.py`, atualizar o import de schemas (linha 16-23):

```python
from app.schemas.pessoa import (
    EnderecoCreate,
    EnderecoRead,
    EnderecoUpdate,
    PessoaCreate,
    PessoaDetail,
    PessoaRead,
    PessoaUpdate,
    VinculoRead,
)
```

**Step 2: Adicionar endpoint PATCH pessoa**

Adicionar após o endpoint `detalhe_pessoa` (após linha ~226) e antes do `deletar_pessoa`:

```python
@router.patch("/{pessoa_id}", response_model=PessoaRead)
@limiter.limit("30/minute")
async def atualizar_pessoa(
    request: Request,
    pessoa_id: int,
    data: PessoaUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PessoaRead:
    """Atualiza dados de uma pessoa existente.

    Permite atualização parcial (PATCH). Se CPF alterado, re-criptografa
    com Fernet e recalcula hash SHA-256.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa a atualizar.
        data: Dados de atualização parcial.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PessoaRead com dados atualizados.

    Raises:
        NaoEncontradoError: Se pessoa não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.
        ConflitoDadosError: Se novo CPF já cadastrado.

    Status Code:
        200: Pessoa atualizada com sucesso.
        404: Pessoa não encontrada.
        409: CPF duplicado.
        429: Rate limit (30/min).
    """
    service = PessoaService(db)
    pessoa = await service.atualizar(
        pessoa_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return _to_pessoa_read(pessoa, service)
```

**Step 3: Adicionar endpoint PATCH endereço**

Adicionar após o endpoint `adicionar_endereco` (após linha ~292):

```python
@router.patch(
    "/{pessoa_id}/enderecos/{endereco_id}",
    response_model=EnderecoRead,
)
@limiter.limit("30/minute")
async def atualizar_endereco(
    request: Request,
    pessoa_id: int,
    endereco_id: int,
    data: EnderecoUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> EnderecoRead:
    """Atualiza endereço existente de uma pessoa.

    Permite atualização parcial de campos do endereço. Se coordenadas
    informadas, atualiza ponto PostGIS.

    Args:
        request: Objeto Request do FastAPI.
        pessoa_id: ID da pessoa dona do endereço.
        endereco_id: ID do endereço a atualizar.
        data: Dados de atualização parcial.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        EnderecoRead com dados atualizados.

    Raises:
        NaoEncontradoError: Se pessoa ou endereço não existe.
        AcessoNegadoError: Se pessoa de outra guarnição.

    Status Code:
        200: Endereço atualizado.
        404: Pessoa ou endereço não encontrado.
        429: Rate limit (30/min).
    """
    service = PessoaService(db)
    endereco = await service.atualizar_endereco(
        pessoa_id,
        endereco_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return EnderecoRead.model_validate(endereco)
```

**Step 4: Commit**

```bash
git add app/api/v1/pessoas.py
git commit -m "feat(api): expor PATCH /pessoas/{id} e PATCH /pessoas/{id}/enderecos/{id}"
```

---

### Task 4: Frontend — Modal Editar Dados Pessoais

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Step 1: Adicionar variáveis de estado no Alpine data**

No objeto retornado por `pessoaDetalhePage(pessoaId)` (linha ~578), adicionar após `novaPessoaForm` (linha ~607):

```javascript
    // Edição de dados pessoais
    modalEditarPessoa: false,
    editPessoaForm: { nome: '', cpf: '', data_nascimento: '', apelido: '', observacoes: '' },
    salvandoPessoa: false,

    // Edição de endereço
    modalEditarEndereco: false,
    editEnderecoForm: { id: null, endereco: '', bairro: '', cidade: '', estado: '' },
    salvandoEndereco: false,
    modoEndereco: 'criar', // 'criar' ou 'editar'
```

**Step 2: Adicionar botão lápis no card Dados Pessoais**

No HTML do card "Dados Pessoais" (linha ~33-34), substituir o `<h3>` por um div com flex para incluir o botão:

Substituir:
```html
            <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">Dados Pessoais</h3>
```

Por:
```html
            <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">Dados Pessoais</h3>
              <button @click="abrirModalEditarPessoa()"
                      style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); padding: 0.125rem; transition: color 0.15s;"
                      onmouseover="this.style.color='var(--color-primary)'" onmouseout="this.style.color='var(--color-text-dim)'"
                      title="Editar dados pessoais">
                <svg style="width: 0.875rem; height: 0.875rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"/>
                </svg>
              </button>
            </div>
```

**Step 3: Adicionar HTML do modal de edição de dados pessoais**

Após o modal de foto ampliada (após linha ~125, antes do modal preview de pessoa coabordada), inserir:

```html
          <!-- Modal editar dados pessoais -->
          <div x-cloak
               @click.self="modalEditarPessoa = false"
               :style="modalEditarPessoa ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.7);z-index:50;align-items:center;justify-content:center;padding:1rem;' : 'display:none;'">
            <div class="glass-card"
                 style="border: 1px solid var(--color-border); padding: 1.25rem; width: 100%; max-width: 24rem; display: flex; flex-direction: column; gap: 0.75rem;"
                 @click.stop>
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="font-family: var(--font-display); font-size: 1rem; font-weight: 600; color: var(--color-text); margin: 0;">Editar Dados Pessoais</h3>
                <button @click="modalEditarPessoa = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
              </div>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Nome <span style="color: var(--color-danger)">*</span></label>
                  <input type="text" x-model="editPessoaForm.nome"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">CPF</label>
                  <input type="text" x-model="editPessoaForm.cpf"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Data de Nascimento</label>
                  <input type="text" x-model="editPessoaForm.data_nascimento"
                         @input="editPessoaForm.data_nascimento = formatarData($event.target.value)"
                         placeholder="DD/MM/AAAA" maxlength="10"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Apelido</label>
                  <input type="text" x-model="editPessoaForm.apelido"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Observações</label>
                  <textarea x-model="editPessoaForm.observacoes" rows="2"
                            style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); resize: none; box-sizing: border-box;"
                            onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'"></textarea>
                </div>
              </div>
              <div style="display: flex; gap: 0.5rem; padding-top: 0.25rem;">
                <button @click="modalEditarPessoa = false"
                        style="flex: 1; background: var(--color-surface-hover); color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; cursor: pointer;">Cancelar</button>
                <button @click="salvarEditPessoa()"
                        :disabled="!editPessoaForm.nome.trim() || salvandoPessoa"
                        class="btn btn-primary"
                        style="flex: 2; border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; font-weight: 500;">
                  <span x-show="!salvandoPessoa">Salvar</span>
                  <span x-show="salvandoPessoa" class="spinner"></span>
                </button>
              </div>
            </div>
          </div>
```

**Step 4: Adicionar métodos Alpine para modal dados pessoais**

Após o método `removerVinculo` (linha ~888), adicionar:

```javascript
    // ------- Edição de Dados Pessoais -------

    abrirModalEditarPessoa() {
      const p = this.pessoa;
      this.editPessoaForm = {
        nome: p.nome || '',
        cpf: p.cpf || '',
        data_nascimento: p.data_nascimento
          ? new Date(p.data_nascimento + 'T00:00:00').toLocaleDateString('pt-BR')
          : '',
        apelido: p.apelido || '',
        observacoes: p.observacoes || '',
      };
      this.modalEditarPessoa = true;
    },

    async salvarEditPessoa() {
      if (!this.editPessoaForm.nome.trim()) return;
      this.salvandoPessoa = true;
      try {
        const body = {};
        const f = this.editPessoaForm;
        if (f.nome.trim() !== (this.pessoa.nome || '')) body.nome = f.nome.trim();
        if (f.cpf.trim() !== (this.pessoa.cpf || '')) body.cpf = f.cpf.trim() || null;
        if (f.apelido.trim() !== (this.pessoa.apelido || '')) body.apelido = f.apelido.trim() || null;
        if (f.observacoes.trim() !== (this.pessoa.observacoes || '')) body.observacoes = f.observacoes.trim() || null;

        const dataParsed = parseDateBR(f.data_nascimento);
        const dataAtual = this.pessoa.data_nascimento || null;
        if (dataParsed !== dataAtual) body.data_nascimento = dataParsed || null;

        if (Object.keys(body).length === 0) {
          this.modalEditarPessoa = false;
          return;
        }

        await api.patch(`/pessoas/${pessoaId}`, body);

        // Recarregar dados atualizados
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);
        this.modalEditarPessoa = false;
        showToast('Dados atualizados com sucesso!', 'success');
      } catch (err) {
        showToast(err?.message || 'Erro ao atualizar dados.', 'error');
      } finally {
        this.salvandoPessoa = false;
      }
    },
```

**Step 5: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): modal de edição de dados pessoais na ficha"
```

---

### Task 5: Frontend — Modal Editar/Criar Endereço

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Step 1: Atualizar header da seção Endereços com botões**

Na seção de endereços (linha ~298-301), substituir o `<h3>` e ajustar para mostrar mesmo sem endereços. Substituir:

```html
          <div x-show="pessoa.enderecos?.length > 0" class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">
              Endereços (<span x-text="pessoa.enderecos.length"></span>)
            </h3>
```

Por:

```html
          <div class="glass-card card-led-blue" style="padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 0.5rem; border-bottom: 1px solid var(--color-border);">
              <h3 style="font-family: var(--font-data); font-size: 0.8rem; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin: 0;">
                Endereços (<span x-text="pessoa.enderecos?.length || 0"></span>)
              </h3>
              <button @click="abrirModalNovoEndereco()"
                      style="background: none; border: none; cursor: pointer; color: var(--color-primary); font-size: 0.75rem; font-family: var(--font-data); font-weight: 600; letter-spacing: 0.05em; padding: 0; opacity: 0.85; transition: opacity 0.15s;"
                      onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.85'">
                + Novo Endereço
              </button>
            </div>
```

**Step 2: Adicionar botão lápis em cada card de endereço**

No template do endereço (linha ~304-318), adicionar botão de edição. Substituir:

```html
                <div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;">
                  <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem;">
                    <p style="font-size: 0.875rem; color: var(--color-text-muted); margin: 0;" x-text="formatEndereco(end)"></p>
                    <span x-show="end.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim); flex-shrink: 0;"
                          x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
                  </div>
```

Por:

```html
                <div class="card-led-purple" style="border: 1px solid rgba(167,139,250,0.2); border-radius: 4px; padding: 0.75rem;">
                  <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem;">
                    <p style="font-size: 0.875rem; color: var(--color-text-muted); margin: 0; flex: 1;" x-text="formatEndereco(end)"></p>
                    <div style="display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0;">
                      <button @click="abrirModalEditarEndereco(end)"
                              style="background: none; border: none; cursor: pointer; color: var(--color-text-dim); padding: 0.125rem; transition: color 0.15s;"
                              onmouseover="this.style.color='var(--color-primary)'" onmouseout="this.style.color='var(--color-text-dim)'"
                              title="Editar endereço">
                        <svg style="width: 0.75rem; height: 0.75rem;" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"/>
                        </svg>
                      </button>
                      <span x-show="end.criado_em" style="font-size: 0.75rem; color: var(--color-text-dim);"
                            x-text="'Cadastrado em ' + new Date(end.criado_em).toLocaleDateString('pt-BR')"></span>
                    </div>
                  </div>
```

**Step 3: Adicionar estado vazio para endereços**

Antes do `</div>` de fechamento da seção endereços (após o template x-for dos endereços), adicionar:

```html
            <p x-show="!pessoa.enderecos?.length" style="font-size: 0.75rem; color: var(--color-text-dim); text-align: center; margin: 0;">
              Nenhum endereço cadastrado
            </p>
```

**Step 4: Adicionar HTML do modal de endereço (criar/editar)**

Após o modal de edição de dados pessoais, inserir:

```html
          <!-- Modal editar/criar endereço -->
          <div x-cloak
               @click.self="modalEditarEndereco = false"
               :style="modalEditarEndereco ? 'display:flex;position:fixed;inset:0;background:rgba(5,10,15,0.7);z-index:50;align-items:center;justify-content:center;padding:1rem;' : 'display:none;'">
            <div class="glass-card"
                 style="border: 1px solid var(--color-border); padding: 1.25rem; width: 100%; max-width: 24rem; display: flex; flex-direction: column; gap: 0.75rem;"
                 @click.stop>
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <h3 style="font-family: var(--font-display); font-size: 1rem; font-weight: 600; color: var(--color-text); margin: 0;"
                    x-text="modoEndereco === 'editar' ? 'Editar Endereço' : 'Novo Endereço'"></h3>
                <button @click="modalEditarEndereco = false" style="color: var(--color-text-muted); background: none; border: none; cursor: pointer; font-size: 1.125rem; line-height: 1;">&times;</button>
              </div>
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Logradouro <span style="color: var(--color-danger)">*</span></label>
                  <input type="text" x-model="editEnderecoForm.endereco"
                         placeholder="Rua, número..."
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div>
                  <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Bairro</label>
                  <input type="text" x-model="editEnderecoForm.bairro"
                         style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                         onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                </div>
                <div style="display: flex; gap: 0.5rem;">
                  <div style="flex: 2;">
                    <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">Cidade</label>
                    <input type="text" x-model="editEnderecoForm.cidade"
                           style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box;"
                           onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                  </div>
                  <div style="flex: 1;">
                    <label style="font-family: var(--font-data); font-size: 0.75rem; color: var(--color-text-muted); font-weight: 500; display: block; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em;">UF</label>
                    <input type="text" x-model="editEnderecoForm.estado" maxlength="2"
                           style="width: 100%; background: var(--color-surface-hover); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.5rem 0.75rem; font-size: 0.875rem; color: var(--color-text); font-family: var(--font-body); box-sizing: border-box; text-transform: uppercase;"
                           onfocus="this.style.borderColor='var(--color-primary)'" onblur="this.style.borderColor='var(--color-border)'">
                  </div>
                </div>
              </div>
              <div style="display: flex; gap: 0.5rem; padding-top: 0.25rem;">
                <button @click="modalEditarEndereco = false"
                        style="flex: 1; background: var(--color-surface-hover); color: var(--color-text-muted); border: 1px solid var(--color-border); border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; cursor: pointer;">Cancelar</button>
                <button @click="salvarEditEndereco()"
                        :disabled="!editEnderecoForm.endereco.trim() || salvandoEndereco"
                        class="btn btn-primary"
                        style="flex: 2; border-radius: 4px; padding: 0.625rem; font-size: 0.875rem; font-weight: 500;">
                  <span x-show="!salvandoEndereco">Salvar</span>
                  <span x-show="salvandoEndereco" class="spinner"></span>
                </button>
              </div>
            </div>
          </div>
```

**Step 5: Adicionar métodos Alpine para modal endereço**

Após o método `salvarEditPessoa`, adicionar:

```javascript
    // ------- Edição/Criação de Endereço -------

    abrirModalEditarEndereco(end) {
      this.modoEndereco = 'editar';
      this.editEnderecoForm = {
        id: end.id,
        endereco: end.endereco || '',
        bairro: end.bairro || '',
        cidade: end.cidade || '',
        estado: end.estado || '',
      };
      this.modalEditarEndereco = true;
    },

    abrirModalNovoEndereco() {
      this.modoEndereco = 'criar';
      this.editEnderecoForm = { id: null, endereco: '', bairro: '', cidade: '', estado: '' };
      this.modalEditarEndereco = true;
    },

    async salvarEditEndereco() {
      if (!this.editEnderecoForm.endereco.trim()) return;
      this.salvandoEndereco = true;
      try {
        const f = this.editEnderecoForm;
        const body = {
          endereco: f.endereco.trim(),
          bairro: f.bairro.trim() || null,
          cidade: f.cidade.trim() || null,
          estado: f.estado.trim().toUpperCase() || null,
        };

        if (this.modoEndereco === 'editar') {
          await api.patch(`/pessoas/${pessoaId}/enderecos/${f.id}`, body);
        } else {
          await api.post(`/pessoas/${pessoaId}/enderecos`, body);
        }

        // Recarregar dados atualizados
        this.pessoa = await api.get(`/pessoas/${pessoaId}`);
        this.modalEditarEndereco = false;
        showToast(
          this.modoEndereco === 'editar' ? 'Endereço atualizado!' : 'Endereço cadastrado!',
          'success'
        );
      } catch (err) {
        showToast(err?.message || 'Erro ao salvar endereço.', 'error');
      } finally {
        this.salvandoEndereco = false;
      }
    },
```

**Step 6: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): modal de edição/criação de endereço na ficha"
```

---

### Task 6: Teste manual end-to-end

**Step 1: Subir ambiente**

```bash
docker compose up -d --build
```

**Step 2: Testar no navegador**

1. Acessar app → Consulta → buscar uma pessoa
2. Na ficha, verificar:
   - Botão lápis no card "Dados Pessoais" → abre modal com dados preenchidos
   - Alterar nome → Salvar → verificar que atualizou na ficha
   - Botão lápis em cada endereço → abre modal em modo edição
   - Botão "+ Novo Endereço" → abre modal vazio em modo criação
   - Toasts de sucesso/erro funcionando
3. Verificar audit log no banco:
   ```sql
   SELECT * FROM audit_log ORDER BY criado_em DESC LIMIT 5;
   ```

**Step 3: Commit final (se ajustes necessários)**

```bash
git add -A
git commit -m "fix(frontend): ajustes finais na edição de ficha de pessoa"
```
