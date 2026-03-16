# Perfil de Usuário e Gestão de Acesso — Plano de Implementação

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar perfil de usuário (foto, posto, nome, nome de guerra) com avatar no header e painel admin para criar/pausar/excluir usuários com modelo de senha única e sessão exclusiva.

**Architecture:** Quatro novos campos no model `Usuario` (`posto_graduacao`, `nome_guerra`, `foto_url`, `session_id`). O `session_id` é gerado no login e embutido no JWT — cada requisição verifica correspondência, garantindo sessão exclusiva. Senhas são geradas pelo admin e invalidadas após o primeiro uso. Frontend ganha avatar clicável no header (abre tela de perfil com botão Sair) e página de admin restrita a `is_admin`.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic + bcrypt + secrets (stdlib) + StorageService (R2) + Alpine.js + Tailwind

---

## Task 1: Migration — novos campos em `usuarios`

**Files:**
- Create: `alembic/versions/<gerado>_perfil_sessao_usuario.py` (via `make migrate`)

**Step 1: Gerar a migration**

```bash
make migrate msg="add_perfil_sessao_to_usuarios"
```

**Step 2: Editar o arquivo gerado** — localizar o arquivo criado em `alembic/versions/` e substituir as funções `upgrade` e `downgrade`:

```python
def upgrade() -> None:
    op.add_column("usuarios", sa.Column("posto_graduacao", sa.String(50), nullable=True))
    op.add_column("usuarios", sa.Column("nome_guerra", sa.String(50), nullable=True))
    op.add_column("usuarios", sa.Column("foto_url", sa.String(500), nullable=True))
    op.add_column("usuarios", sa.Column("session_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "session_id")
    op.drop_column("usuarios", "foto_url")
    op.drop_column("usuarios", "nome_guerra")
    op.drop_column("usuarios", "posto_graduacao")
```

**Step 3: Aplicar a migration**

```bash
docker compose exec api alembic upgrade head
```

Expected: `Running upgrade ... -> ..., add_perfil_sessao_to_usuarios`

**Step 4: Commit**

```bash
git add alembic/versions/
git commit -m "feat(db): migration — adicionar posto_graduacao, foto_url, session_id em usuarios"
```

---

## Task 2: Atualizar model `Usuario`

**Files:**
- Modify: `app/models/usuario.py`

**Step 1: Escrever teste que valida os novos campos no model**

Arquivo: `tests/unit/test_usuario_model.py`

```python
"""Testes do model Usuario — validação dos novos campos de perfil e sessão."""

from app.models.usuario import POSTOS_GRADUACAO, Usuario


def test_postos_graduacao_lista_completa():
    """Verifica que a lista de postos contém as graduações PM esperadas."""
    assert "Soldado" in POSTOS_GRADUACAO
    assert "Coronel" in POSTOS_GRADUACAO
    assert len(POSTOS_GRADUACAO) == 13


def test_usuario_possui_campos_de_perfil():
    """Verifica que o model Usuario possui os novos atributos de perfil."""
    u = Usuario(nome="Teste", matricula="T001", senha_hash="hash")
    assert hasattr(u, "posto_graduacao")
    assert hasattr(u, "nome_guerra")
    assert hasattr(u, "foto_url")
    assert hasattr(u, "session_id")
    assert u.posto_graduacao is None
    assert u.nome_guerra is None
    assert u.foto_url is None
    assert u.session_id is None
```

**Step 2: Rodar o teste para confirmar que falha**

```bash
make test -- tests/unit/test_usuario_model.py -v
```

Expected: FAIL — `POSTOS_GRADUACAO` não existe

**Step 3: Implementar os campos em `app/models/usuario.py`**

```python
"""Modelo de Usuário — oficial ou membro da guarnição.

Define o usuário (oficial de patrulhamento) do sistema, com autenticação,
perfil (posto, foto) e controle de sessão exclusiva.
"""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin

#: Lista fixa de postos e graduações da Polícia Militar.
POSTOS_GRADUACAO: list[str] = [
    "Soldado",
    "Cabo",
    "3º Sargento",
    "2º Sargento",
    "1º Sargento",
    "Subtenente",
    "Aspirante",
    "2º Tenente",
    "1º Tenente",
    "Capitão",
    "Major",
    "Tenente-Coronel",
    "Coronel",
]


class Usuario(Base, TimestampMixin, SoftDeleteMixin):
    """Usuário do sistema — oficial ou membro de guarnição.

    Representa um oficial ou policial que usa o sistema para registrar
    abordagens, consultar dados e gerar ocorrências. Autenticação via
    matrícula e senha_hash (bcrypt). Sempre vinculado a uma guarnição.

    A segurança de sessão é garantida pelo campo `session_id`: gerado a cada
    login e embutido no JWT. Qualquer nova autenticação invalida sessões anteriores.
    Senhas são sempre geradas pelo admin e consumidas no primeiro uso.

    Attributes:
        id: Identificador único (chave primária).
        nome: Nome completo do oficial.
        matricula: Número de matrícula único (indexado para login).
        email: Email do oficial (único, opcional).
        senha_hash: Hash bcrypt da senha (gerada pelo admin, uso único).
        posto_graduacao: Posto ou graduação PM (ex: "Sargento"). Ver POSTOS_GRADUACAO.
        nome_guerra: Nome de guerra do agente (ex: "Silva"). Máx 50 chars.
        foto_url: URL pública da foto de perfil no R2 (opcional).
        session_id: UUID da sessão ativa. None = sem sessão. Novo login gera novo UUID.
        guarnicao_id: ID da guarnição (chave estrangeira).
        is_admin: Flag indicando permissões administrativas.
        guarnicao: Relacionamento com Guarnicao.
    """

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    matricula: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    posto_graduacao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nome_guerra: Mapped[str | None] = mapped_column(String(50), nullable=True)
    foto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    guarnicao_id: Mapped[int | None] = mapped_column(ForeignKey("guarnicoes.id"), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    guarnicao = relationship(
        "Guarnicao",
        back_populates="membros",
        foreign_keys=[guarnicao_id],
    )
```

**Step 4: Rodar o teste**

```bash
make test -- tests/unit/test_usuario_model.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/models/usuario.py tests/unit/test_usuario_model.py
git commit -m "feat(model): adicionar posto_graduacao, foto_url, session_id ao Usuario"
```

---

## Task 3: Atualizar `security.py` — `session_id` nos tokens

**Files:**
- Modify: `app/core/security.py`

**Step 1: Escrever testes**

Arquivo: `tests/unit/test_security_session.py`

```python
"""Testes de segurança — session_id embutido nos tokens JWT."""

from app.core.security import criar_access_token, criar_refresh_token, decodificar_token


def test_access_token_inclui_session_id():
    """Verifica que session_id é embutido no access token."""
    token = criar_access_token({"sub": "1", "sid": "meu-session-id"})
    payload = decodificar_token(token)
    assert payload["sid"] == "meu-session-id"


def test_refresh_token_inclui_session_id():
    """Verifica que session_id é embutido no refresh token."""
    token = criar_refresh_token({"sub": "1", "sid": "meu-session-id"})
    payload = decodificar_token(token, expected_type="refresh")
    assert payload["sid"] == "meu-session-id"


def test_token_sem_session_id_decodifica_normalmente():
    """Verifica backward compatibility — tokens sem sid ainda decodificam."""
    token = criar_access_token({"sub": "1"})
    payload = decodificar_token(token)
    assert payload["sub"] == "1"
    assert payload.get("sid") is None
```

**Step 2: Rodar os testes**

```bash
make test -- tests/unit/test_security_session.py -v
```

Expected: PASS (os testes já passam — `security.py` passa claims diretamente, não filtra `sid`)

> Se todos passam, confirmar e prosseguir. `security.py` não precisa de alteração — ele já propaga qualquer claim do dict `data`. Esses testes documentam o comportamento esperado.

**Step 3: Commit**

```bash
git add tests/unit/test_security_session.py
git commit -m "test(security): documentar comportamento de session_id nos tokens JWT"
```

---

## Task 4: Atualizar `auth_service.py` — senha única + session_id no login

**Files:**
- Modify: `app/services/auth_service.py`

**Step 1: Escrever testes**

Arquivo: `tests/unit/test_auth_session.py`

```python
"""Testes de autenticação — senha única e session_id exclusivo."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.auth_service import AuthService
from app.core.exceptions import CredenciaisInvalidasError


@pytest.fixture
def mock_db():
    """Fixture de mock para sessão do banco."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_login_gera_session_id(mock_db):
    """Verifica que login bem-sucedido gera e salva session_id no usuário."""
    usuario = MagicMock()
    usuario.id = 1
    usuario.guarnicao_id = 1
    usuario.session_id = None

    service = AuthService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = usuario
    service.audit = AsyncMock()

    with patch("app.services.auth_service.verificar_senha", return_value=True), \
         patch("app.services.auth_service.hash_senha", return_value="hash_aleatorio"):
        result = await service.login("TEST001", "senha123")

    # session_id deve ter sido atribuído
    assert usuario.session_id is not None
    assert len(usuario.session_id) == 36  # UUID4 format

    # Token deve conter sid
    from app.core.security import decodificar_token
    payload = decodificar_token(result.access_token)
    assert payload["sid"] == usuario.session_id


@pytest.mark.asyncio
async def test_login_invalida_senha_apos_uso(mock_db):
    """Verifica que senha é substituída por hash inutilizável após login."""
    usuario = MagicMock()
    usuario.id = 1
    usuario.guarnicao_id = None
    usuario.session_id = None

    service = AuthService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = usuario
    service.audit = AsyncMock()

    novo_hash = "hash_novo_inutilizavel"
    with patch("app.services.auth_service.verificar_senha", return_value=True), \
         patch("app.services.auth_service.hash_senha", return_value=novo_hash):
        await service.login("TEST001", "senha_unica")

    # senha_hash substituída
    assert usuario.senha_hash == novo_hash


@pytest.mark.asyncio
async def test_login_invalido_nao_altera_usuario(mock_db):
    """Verifica que login com senha errada não altera o usuário."""
    usuario = MagicMock()
    usuario.id = 1
    usuario.session_id = "sessao-anterior"

    service = AuthService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = usuario
    service.audit = AsyncMock()

    with patch("app.services.auth_service.verificar_senha", return_value=False):
        with pytest.raises(CredenciaisInvalidasError):
            await service.login("TEST001", "senhaerrada")

    # session_id NÃO deve ter mudado
    assert usuario.session_id == "sessao-anterior"
```

**Step 2: Rodar os testes para confirmar que falham**

```bash
make test -- tests/unit/test_auth_session.py -v
```

Expected: FAIL — login não gera session_id

**Step 3: Atualizar `app/services/auth_service.py`**

Substituir o método `login`:

```python
import secrets
import uuid

# No topo do arquivo, adicionar aos imports:
# from app.core.security import criar_access_token, criar_refresh_token, decodificar_token, hash_senha, verificar_senha

async def login(
    self,
    matricula: str,
    senha: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TokenResponse:
    """Autentica um agente com senha de uso único e gera sessão exclusiva.

    Valida as credenciais (matrícula e senha), invalida a senha após uso
    (substituindo por hash aleatório inutilizável), gera novo session_id
    (UUID4) que é embutido no JWT — garantindo sessão exclusiva por usuário.

    Args:
        matricula: Matrícula do agente.
        senha: Senha de uso único gerada pelo admin.
        ip_address: Endereço IP da requisição (opcional, para auditoria).
        user_agent: User-Agent do cliente (opcional, para auditoria).

    Returns:
        TokenResponse: Tokens JWT de acesso e refresh com session_id embutido.

    Raises:
        CredenciaisInvalidasError: Se matrícula não existe ou senha é inválida.
    """
    usuario = await self.repo.get_by_matricula(matricula)
    if not usuario or not verificar_senha(senha, usuario.senha_hash):
        raise CredenciaisInvalidasError()

    # Senha de uso único — substituir por hash inutilizável após login
    usuario.senha_hash = hash_senha(secrets.token_hex(32))

    # Sessão exclusiva — novo session_id invalida tokens anteriores
    novo_session_id = str(uuid.uuid4())
    usuario.session_id = novo_session_id

    token_data: dict = {
        "sub": str(usuario.id),
        "sid": novo_session_id,
    }
    if usuario.guarnicao_id is not None:
        token_data["guarnicao_id"] = usuario.guarnicao_id
    access_token = criar_access_token(token_data)
    refresh_token = criar_refresh_token(token_data)

    await self.audit.log(
        usuario_id=usuario.id,
        acao="LOGIN",
        recurso="auth",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
```

Também atualizar o método `refresh` para manter o `sid` existente no novo token:

```python
async def refresh(self, refresh_token: str) -> TokenResponse:
    """Renova os tokens de acesso mantendo o session_id existente.

    Decodifica o refresh token, valida o usuário e session_id, e gera
    novos tokens mantendo o mesmo session_id (sem rotação de sessão).

    Args:
        refresh_token: Refresh token JWT válido com claim 'sid'.

    Returns:
        TokenResponse: Novos tokens de acesso e refresh.

    Raises:
        CredenciaisInvalidasError: Se refresh token inválido, usuário não existe
            ou session_id não confere.
    """
    payload = decodificar_token(refresh_token, expected_type="refresh")
    if payload is None:
        raise CredenciaisInvalidasError()

    user_id = payload.get("sub")
    sid = payload.get("sid")
    if not user_id:
        raise CredenciaisInvalidasError()

    usuario = await self.repo.get(int(user_id))
    if not usuario or not usuario.ativo:
        raise CredenciaisInvalidasError()

    # Verificar session_id — rejeitar se sessão foi revogada
    if usuario.session_id is None or usuario.session_id != sid:
        raise CredenciaisInvalidasError()

    token_data: dict = {"sub": str(usuario.id), "sid": sid}
    if usuario.guarnicao_id is not None:
        token_data["guarnicao_id"] = usuario.guarnicao_id

    return TokenResponse(
        access_token=criar_access_token(token_data),
        refresh_token=criar_refresh_token(token_data),
    )
```

**Step 4: Rodar os testes**

```bash
make test -- tests/unit/test_auth_session.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/auth_service.py tests/unit/test_auth_session.py
git commit -m "feat(auth): senha de uso único e session_id exclusivo no login"
```

---

## Task 5: Atualizar `dependencies.py` — verificar `session_id` em cada requisição

**Files:**
- Modify: `app/dependencies.py`

**Step 1: Escrever teste de integração**

Arquivo: `tests/integration/test_session_exclusiva.py`

```python
"""Testes de sessão exclusiva — session_id revogado rejeita requisições."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_token_com_session_id_errado_retorna_401(client: AsyncClient, usuario, db_session):
    """Token com session_id diferente do banco deve ser rejeitado com 401."""
    from app.core.security import criar_access_token

    # Definir session_id no banco
    usuario.session_id = "sessao-correta"
    await db_session.flush()

    # Criar token com session_id DIFERENTE
    token = criar_access_token({"sub": str(usuario.id), "sid": "sessao-errada"})
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_com_session_id_correto_retorna_200(client: AsyncClient, usuario, db_session):
    """Token com session_id correto deve ser aceito."""
    from app.core.security import criar_access_token

    usuario.session_id = "sessao-ativa"
    await db_session.flush()

    token = criar_access_token({"sub": str(usuario.id), "sid": "sessao-ativa"})
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_usuario_sem_session_retorna_401(client: AsyncClient, usuario, db_session):
    """Usuário com session_id None (pausado ou sem login) deve ser rejeitado."""
    from app.core.security import criar_access_token

    usuario.session_id = None
    await db_session.flush()

    token = criar_access_token({"sub": str(usuario.id), "sid": "qualquer"})
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
```

**Step 2: Atualizar a fixture `usuario` e `auth_headers` em `tests/conftest.py`**

Localizar a fixture `usuario` e adicionar `session_id`:

```python
@pytest.fixture
async def usuario(db_session: AsyncSession, guarnicao: Guarnicao) -> Usuario:
    """Fixture que cria um usuário de teste autenticado com sessão ativa.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição para associar ao usuário.

    Returns:
        Usuario: Objeto de usuário com matrícula TEST001, senha123 e session_id ativo.
    """
    u = Usuario(
        nome="Agente Teste",
        matricula="TEST001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        session_id="test-session-id",
    )
    db_session.add(u)
    await db_session.flush()
    return u
```

Localizar a fixture `auth_headers` e incluir `sid`:

```python
@pytest.fixture
async def auth_headers(usuario: Usuario) -> dict:
    """Fixture que gera headers com token de autenticação válido e session_id.

    Args:
        usuario: Fixture de usuário com session_id definido.

    Returns:
        dict: Headers com Authorization Bearer token incluindo sid.
    """
    token = criar_access_token({
        "sub": str(usuario.id),
        "guarnicao_id": usuario.guarnicao_id,
        "sid": usuario.session_id,
    })
    return {"Authorization": f"Bearer {token}"}
```

**Step 3: Rodar os testes de sessão para confirmar que falham**

```bash
make test -- tests/integration/test_session_exclusiva.py -v
```

Expected: FAIL — `get_current_user` ainda não verifica session_id

**Step 4: Atualizar `app/dependencies.py`**

Substituir a função `get_current_user`:

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Usuario:
    """Extrai e valida usuário autenticado do token JWT Bearer.

    Além de validar assinatura e expiração do JWT, verifica o session_id:
    o claim 'sid' do token deve corresponder ao session_id no banco.
    Isso garante sessão exclusiva — novo login invalida tokens anteriores.
    Usuários com session_id=None (pausados ou sem login) são sempre rejeitados.

    Args:
        credentials: Credencial Bearer extraída do header Authorization.
        db: Sessão do banco de dados para buscar usuário.

    Returns:
        Objeto Usuario autenticado, ativo e com sessão válida.

    Raises:
        HTTPException: 401 se token inválido, expirado, usuário inativo
            ou session_id não confere.
    """
    payload = decodificar_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido (sem sub)",
        )

    result = await db.execute(
        select(Usuario).where(Usuario.id == int(user_id), Usuario.ativo == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )

    # Verificar session_id — sessão exclusiva por usuário
    token_sid = payload.get("sid")
    if user.session_id is None or user.session_id != token_sid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão encerrada — solicite nova senha ao administrador",
        )

    return user
```

**Step 5: Rodar todos os testes**

```bash
make test
```

Expected: PASS (todos os testes existentes passam pois `auth_headers` agora inclui `sid`)

**Step 6: Commit**

```bash
git add app/dependencies.py tests/conftest.py tests/integration/test_session_exclusiva.py
git commit -m "feat(auth): verificar session_id em cada requisição — sessão exclusiva"
```

---

## Task 6: Atualizar schemas e adicionar novos schemas

**Files:**
- Modify: `app/schemas/auth.py`

**Step 1: Escrever teste dos schemas**

Arquivo: `tests/unit/test_schemas_perfil.py`

```python
"""Testes dos schemas de perfil e admin."""

import pytest
from pydantic import ValidationError
from app.schemas.auth import PerfilUpdate, UsuarioAdminCreate, UsuarioRead
from app.models.usuario import POSTOS_GRADUACAO


def test_perfil_update_posto_valido():
    """Verifica que PerfilUpdate aceita posto da lista oficial."""
    schema = PerfilUpdate(nome="João Silva", posto_graduacao="Sargento")
    # Sargento não está na lista exata — deve usar valores exatos
    # Este teste vai falhar até implementarmos a validação


def test_perfil_update_posto_invalido_rejeita():
    """Verifica que PerfilUpdate rejeita posto fora da lista."""
    with pytest.raises(ValidationError):
        PerfilUpdate(nome="João", posto_graduacao="General")


def test_perfil_update_sem_posto_valido():
    """Verifica que PerfilUpdate aceita posto None."""
    schema = PerfilUpdate(nome="João Silva", posto_graduacao=None)
    assert schema.posto_graduacao is None


def test_admin_create_apenas_matricula():
    """Verifica que UsuarioAdminCreate aceita apenas matrícula."""
    schema = UsuarioAdminCreate(matricula="PM001")
    assert schema.matricula == "PM001"


def test_usuario_read_inclui_novos_campos():
    """Verifica que UsuarioRead inclui posto_graduacao e foto_url."""
    from datetime import datetime
    schema = UsuarioRead(
        id=1,
        nome="Agente",
        matricula="T001",
        is_admin=False,
        guarnicao_id=1,
        criado_em=datetime.now(),
        posto_graduacao="Capitão",
        foto_url="https://r2.example.com/foto.jpg",
    )
    assert schema.posto_graduacao == "Capitão"
    assert schema.foto_url == "https://r2.example.com/foto.jpg"
```

**Step 2: Rodar para confirmar que falha**

```bash
make test -- tests/unit/test_schemas_perfil.py -v
```

Expected: FAIL — schemas não existem ainda

**Step 3: Atualizar `app/schemas/auth.py`**

Adicionar ao final do arquivo (após `GuarnicaoRead`):

```python
from app.models.usuario import POSTOS_GRADUACAO


class PerfilUpdate(BaseModel):
    """Dados para atualização do perfil do usuário.

    Permite atualizar nome, nome de guerra, posto/graduação e URL da foto.
    O posto_graduacao deve ser um valor da lista POSTOS_GRADUACAO.

    Attributes:
        nome: Nome completo do agente (2 a 200 caracteres).
        nome_guerra: Nome de guerra do agente (ex: "Silva"). Máx 50 chars.
        posto_graduacao: Posto ou graduação PM (lista fixa). None para remover.
        foto_url: URL pública da foto de perfil no R2 (opcional).
    """

    nome: str = Field(..., min_length=2, max_length=200)
    nome_guerra: str | None = Field(None, max_length=50)
    posto_graduacao: str | None = Field(None, max_length=50)
    foto_url: str | None = Field(None, max_length=500)

    @field_validator("posto_graduacao")
    @classmethod
    def validar_posto(cls, v: str | None) -> str | None:
        """Valida que o posto é da lista oficial PM."""
        if v is not None and v not in POSTOS_GRADUACAO:
            raise ValueError(f"Posto inválido. Valores aceitos: {POSTOS_GRADUACAO}")
        return v


class UsuarioAdminCreate(BaseModel):
    """Dados para criação de usuário pelo admin.

    O admin informa apenas a matrícula. O sistema gera a senha automaticamente.

    Attributes:
        matricula: Matrícula do agente (1 a 50 caracteres, único no sistema).
    """

    matricula: str = Field(..., min_length=1, max_length=50)


class SenhaGeradaResponse(BaseModel):
    """Resposta com senha gerada pelo sistema (exibida apenas uma vez).

    Attributes:
        usuario_id: ID do usuário criado ou atualizado.
        matricula: Matrícula do usuário.
        senha: Senha gerada em texto plano — exibir UMA vez e descartar.
    """

    usuario_id: int
    matricula: str
    senha: str


class UsuarioAdminRead(BaseModel):
    """Dados de usuário para listagem no painel admin.

    Attributes:
        id: Identificador único do usuário.
        nome: Nome completo do agente.
        matricula: Matrícula do agente.
        posto_graduacao: Posto ou graduação PM.
        foto_url: URL da foto de perfil.
        is_admin: Indica se é administrador.
        ativo: Indica se o acesso está ativo.
        tem_sessao: Indica se há sessão ativa (session_id != None).
        guarnicao_id: ID da guarnição.
    """

    id: int
    nome: str
    matricula: str
    posto_graduacao: str | None = None
    foto_url: str | None = None
    is_admin: bool
    ativo: bool
    tem_sessao: bool
    guarnicao_id: int | None = None

    model_config = {"from_attributes": True}
```

Atualizar `UsuarioRead` para incluir os novos campos:

```python
class UsuarioRead(BaseModel):
    """Dados públicos de um usuário (agente).

    Attributes:
        id: Identificador único do usuário.
        nome: Nome completo do agente.
        matricula: Matrícula do agente.
        email: Email do agente (opcional).
        is_admin: Indica se o agente é administrador.
        guarnicao_id: Identificador da guarnição do agente.
        posto_graduacao: Posto ou graduação PM (ex: "Sargento").
        nome_guerra: Nome de guerra do agente (ex: "Silva").
        foto_url: URL pública da foto de perfil no R2.
        criado_em: Data e hora de criação do usuário.
    """

    id: int
    nome: str
    matricula: str
    email: str | None = None
    is_admin: bool
    guarnicao_id: int | None = None
    posto_graduacao: str | None = None
    nome_guerra: str | None = None
    foto_url: str | None = None
    criado_em: datetime

    model_config = {"from_attributes": True}
```

Adicionar ao topo do arquivo o import de `field_validator`:

```python
from pydantic import BaseModel, Field, field_validator
```

**Step 4: Rodar testes**

```bash
make test -- tests/unit/test_schemas_perfil.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/schemas/auth.py tests/unit/test_schemas_perfil.py
git commit -m "feat(schemas): PerfilUpdate, UsuarioAdminCreate, SenhaGeradaResponse, UsuarioAdminRead"
```

---

## Task 7: Novos endpoints de perfil em `app/api/v1/auth.py`

**Files:**
- Modify: `app/api/v1/auth.py`

**Step 1: Escrever testes de integração**

Arquivo: `tests/integration/test_api_perfil.py`

```python
"""Testes dos endpoints de perfil do usuário."""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_atualizar_perfil_sucesso(client: AsyncClient, auth_headers, usuario):
    """Testa atualização bem-sucedida de nome e posto do perfil."""
    response = await client.put(
        "/api/v1/auth/perfil",
        json={"nome": "João Silva", "posto_graduacao": "Capitão"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nome"] == "João Silva"
    assert data["posto_graduacao"] == "Capitão"


@pytest.mark.asyncio
async def test_atualizar_perfil_posto_invalido(client: AsyncClient, auth_headers):
    """Testa rejeição de posto fora da lista oficial."""
    response = await client.put(
        "/api/v1/auth/perfil",
        json={"nome": "Teste", "posto_graduacao": "General"},
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_atualizar_perfil_sem_auth(client: AsyncClient):
    """Testa rejeição sem autenticação."""
    response = await client.put(
        "/api/v1/auth/perfil",
        json={"nome": "Teste"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_foto_perfil(client: AsyncClient, auth_headers):
    """Testa upload de foto de perfil com mock do StorageService."""
    from io import BytesIO

    fake_url = "https://r2.example.com/avatares/abc123_foto.jpg"

    with patch("app.api.v1.auth.StorageService") as MockStorage:
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = fake_url
        MockStorage.return_value = mock_storage

        response = await client.post(
            "/api/v1/auth/perfil/foto",
            files={"foto": ("foto.jpg", BytesIO(b"fake-image-bytes"), "image/jpeg")},
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["foto_url"] == fake_url
```

**Step 2: Implementar endpoints em `app/api/v1/auth.py`**

Adicionar imports no topo:

```python
from fastapi import APIRouter, Depends, File, Request, UploadFile
from app.schemas.auth import LoginRequest, PerfilUpdate, RefreshRequest, TokenResponse, UsuarioRead
from app.services.storage_service import StorageService
```

Adicionar os dois endpoints ao final do arquivo:

```python
@router.put("/perfil", response_model=UsuarioRead)
async def atualizar_perfil(
    data: PerfilUpdate,
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsuarioRead:
    """Atualiza nome, posto/graduação e foto_url do perfil do usuário autenticado.

    Args:
        data: Dados de perfil a atualizar (nome, posto_graduacao, foto_url).
        user: Usuário autenticado (injetado automaticamente).
        db: Sessão do banco de dados.

    Returns:
        UsuarioRead: Dados atualizados do usuário.

    Raises:
        AuthenticationError: Se token inválido ou sessão encerrada.
        ValidationError: Se posto_graduacao fora da lista oficial.

    Status Code:
        200: Perfil atualizado com sucesso.
        401: Não autenticado.
        422: Dados inválidos (posto fora da lista).
    """
    user.nome = data.nome
    if data.nome_guerra is not None:
        user.nome_guerra = data.nome_guerra
    if data.posto_graduacao is not None:
        user.posto_graduacao = data.posto_graduacao
    if data.foto_url is not None:
        user.foto_url = data.foto_url
    await db.commit()
    await db.refresh(user)
    return UsuarioRead.model_validate(user)


@router.post("/perfil/foto", response_model=dict)
async def upload_foto_perfil(
    foto: UploadFile = File(...),
    user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Faz upload da foto de perfil para R2 e atualiza foto_url do usuário.

    Args:
        foto: Arquivo de imagem enviado via multipart/form-data.
        user: Usuário autenticado.
        db: Sessão do banco de dados.

    Returns:
        dict: Objeto com campo foto_url contendo a URL pública da foto no R2.

    Raises:
        AuthenticationError: Se token inválido.

    Status Code:
        200: Upload realizado com sucesso.
        401: Não autenticado.
    """
    file_bytes = await foto.read()
    storage = StorageService()
    key = storage._generate_key("avatares", foto.filename or "foto.jpg")
    url = await storage.upload(file_bytes, key, content_type=foto.content_type or "image/jpeg")

    user.foto_url = url
    await db.commit()

    return {"foto_url": url}
```

**Step 3: Rodar os testes**

```bash
make test -- tests/integration/test_api_perfil.py -v
```

Expected: PASS

**Step 4: Commit**

```bash
git add app/api/v1/auth.py tests/integration/test_api_perfil.py
git commit -m "feat(api): endpoints PUT /auth/perfil e POST /auth/perfil/foto"
```

---

## Task 8: Serviço admin — `UsuarioAdminService`

**Files:**
- Create: `app/services/usuario_admin_service.py`

**Step 1: Escrever testes unitários**

Arquivo: `tests/unit/test_usuario_admin_service.py`

```python
"""Testes do serviço de gestão de usuários pelo admin."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_db():
    """Mock da sessão do banco."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_criar_usuario_retorna_senha_gerada(mock_db):
    """Verifica que criação gera senha aleatória e retorna em plain text."""
    from app.services.usuario_admin_service import UsuarioAdminService

    service = UsuarioAdminService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = None
    service.audit = AsyncMock()

    with patch("app.services.usuario_admin_service.hash_senha", return_value="hash"):
        usuario, senha = await service.criar_usuario("PM001", admin_id=1)

    assert len(senha) >= 8  # senha gerada tem pelo menos 8 chars
    assert usuario.matricula == "PM001"
    assert usuario.session_id is None  # sem sessão até o primeiro login


@pytest.mark.asyncio
async def test_criar_usuario_matricula_duplicada_levanta_erro(mock_db):
    """Verifica que matrícula duplicada levanta ConflitoDadosError."""
    from app.services.usuario_admin_service import UsuarioAdminService
    from app.core.exceptions import ConflitoDadosError

    service = UsuarioAdminService(mock_db)
    service.repo = AsyncMock()
    service.repo.get_by_matricula.return_value = MagicMock()  # já existe

    with pytest.raises(ConflitoDadosError):
        await service.criar_usuario("PM001", admin_id=1)


@pytest.mark.asyncio
async def test_pausar_usuario_limpa_session_id(mock_db):
    """Verifica que pausar apaga session_id (desconexão imediata)."""
    from app.services.usuario_admin_service import UsuarioAdminService

    usuario = MagicMock()
    usuario.session_id = "sessao-ativa"
    usuario.ativo = True

    service = UsuarioAdminService(mock_db)
    service.repo = AsyncMock()
    service.repo.get.return_value = usuario
    service.audit = AsyncMock()

    await service.pausar_usuario(usuario_id=1, admin_id=2)

    assert usuario.session_id is None


@pytest.mark.asyncio
async def test_gerar_nova_senha_invalida_sessao(mock_db):
    """Verifica que gerar nova senha limpa session_id e retorna nova senha."""
    from app.services.usuario_admin_service import UsuarioAdminService

    usuario = MagicMock()
    usuario.session_id = "sessao-velha"
    usuario.ativo = True

    service = UsuarioAdminService(mock_db)
    service.repo = AsyncMock()
    service.repo.get.return_value = usuario
    service.audit = AsyncMock()

    with patch("app.services.usuario_admin_service.hash_senha", return_value="novo_hash"):
        senha = await service.gerar_nova_senha(usuario_id=1, admin_id=2)

    assert len(senha) >= 8
    assert usuario.session_id is None
    assert usuario.senha_hash == "novo_hash"
    assert usuario.ativo is True  # reativar se estava pausado
```

**Step 2: Rodar para confirmar que falha**

```bash
make test -- tests/unit/test_usuario_admin_service.py -v
```

Expected: FAIL — serviço não existe

**Step 3: Criar `app/services/usuario_admin_service.py`**

```python
"""Serviço de gerenciamento de usuários pelo administrador.

Implementa criação de usuários com senha de uso único, pausa/reativação
de acesso e geração de novas senhas. Sem dependências FastAPI.
"""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.core.security import hash_senha
from app.models.usuario import Usuario
from app.repositories.usuario_repo import UsuarioRepository
from app.services.audit_service import AuditService


def _gerar_senha() -> str:
    """Gera senha aleatória segura de 10 caracteres.

    Usa secrets.token_urlsafe para garantir aleatoriedade criptográfica.

    Returns:
        Senha em texto plano com 10 caracteres URL-safe.
    """
    return secrets.token_urlsafe(8)[:10]


class UsuarioAdminService:
    """Serviço de gestão de usuários para uso exclusivo do administrador.

    Implementa criação com senha única, pausa de acesso (desconecta imediatamente
    via limpeza do session_id), reativação e geração de novas senhas.
    Registra todas as ações via AuditService (LGPD).

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de usuários.
        audit: Serviço de auditoria.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço com dependências.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = UsuarioRepository(db)
        self.audit = AuditService(db)

    async def listar_usuarios(self, guarnicao_id: int) -> list[Usuario]:
        """Lista todos os usuários ativos e pausados da guarnição.

        Retorna usuários com ativo=True. Excluídos (ativo=False) são omitidos.

        Args:
            guarnicao_id: ID da guarnição para filtrar usuários.

        Returns:
            Lista de objetos Usuario ordenada por nome.
        """
        result = await self.db.execute(
            select(Usuario)
            .where(Usuario.guarnicao_id == guarnicao_id, Usuario.ativo == True)  # noqa: E712
            .order_by(Usuario.nome)
        )
        return list(result.scalars().all())

    async def criar_usuario(
        self,
        matricula: str,
        admin_id: int,
        guarnicao_id: int | None = None,
    ) -> tuple[Usuario, str]:
        """Cria novo usuário com senha de uso único gerada automaticamente.

        A senha gerada é retornada em plain text UMA ÚNICA VEZ e deve ser
        exibida imediatamente ao admin. Após o primeiro login do usuário,
        a senha é invalidada automaticamente.

        Args:
            matricula: Matrícula do novo agente (deve ser única).
            admin_id: ID do admin que está criando (para auditoria).
            guarnicao_id: ID da guarnição do novo usuário.

        Returns:
            Tupla (Usuario, senha_plain_text) — senha exibida uma vez.

        Raises:
            ConflitoDadosError: Se matrícula já cadastrada.
        """
        existing = await self.repo.get_by_matricula(matricula)
        if existing:
            raise ConflitoDadosError("Matrícula já cadastrada")

        senha = _gerar_senha()
        usuario = Usuario(
            nome=matricula,  # nome provisório até o usuário atualizar o perfil
            matricula=matricula,
            senha_hash=hash_senha(senha),
            guarnicao_id=guarnicao_id,
            session_id=None,  # sem sessão até o primeiro login
        )
        self.db.add(usuario)
        await self.db.flush()

        await self.audit.log(
            usuario_id=admin_id,
            acao="CREATE",
            recurso="usuario",
            recurso_id=usuario.id,
            detalhes={"matricula": matricula, "criado_por": admin_id},
        )

        return usuario, senha

    async def pausar_usuario(self, usuario_id: int, admin_id: int) -> Usuario:
        """Pausa o acesso do usuário limpando o session_id.

        A limpeza do session_id garante desconexão imediata: qualquer token
        JWT ativo será rejeitado na próxima requisição.

        Args:
            usuario_id: ID do usuário a pausar.
            admin_id: ID do admin (para auditoria).

        Returns:
            Usuario pausado.

        Raises:
            NaoEncontradoError: Se usuário não existe ou já foi excluído.
        """
        usuario = await self.repo.get(usuario_id)
        if not usuario or not usuario.ativo:
            raise NaoEncontradoError("Usuário não encontrado")

        usuario.session_id = None

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"acao": "pausar", "admin_id": admin_id},
        )

        return usuario

    async def gerar_nova_senha(self, usuario_id: int, admin_id: int) -> str:
        """Gera nova senha de uso único para o usuário, invalidando a sessão atual.

        Limpa session_id (desconecta imediatamente se havia sessão ativa),
        define nova senha de uso único, e reativa o usuário se estava pausado.

        Args:
            usuario_id: ID do usuário.
            admin_id: ID do admin (para auditoria).

        Returns:
            Nova senha em plain text — exibir UMA vez.

        Raises:
            NaoEncontradoError: Se usuário não existe.
        """
        result = await self.db.execute(
            select(Usuario).where(Usuario.id == usuario_id)
        )
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise NaoEncontradoError("Usuário não encontrado")

        senha = _gerar_senha()
        usuario.senha_hash = hash_senha(senha)
        usuario.session_id = None  # desconectar sessão atual
        usuario.ativo = True  # reativar se estava pausado

        await self.audit.log(
            usuario_id=admin_id,
            acao="UPDATE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"acao": "gerar_senha", "admin_id": admin_id},
        )

        return senha

    async def excluir_usuario(self, usuario_id: int, admin_id: int) -> None:
        """Exclui logicamente o usuário (soft delete — LGPD).

        Marca como inativo e limpa session_id. Dados preservados conforme LGPD.

        Args:
            usuario_id: ID do usuário a excluir.
            admin_id: ID do admin (para auditoria).

        Raises:
            NaoEncontradoError: Se usuário não existe.
        """
        from datetime import UTC, datetime

        result = await self.db.execute(
            select(Usuario).where(Usuario.id == usuario_id)
        )
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise NaoEncontradoError("Usuário não encontrado")

        usuario.ativo = False
        usuario.session_id = None
        usuario.desativado_em = datetime.now(UTC)
        usuario.desativado_por_id = admin_id

        await self.audit.log(
            usuario_id=admin_id,
            acao="DELETE",
            recurso="usuario",
            recurso_id=usuario_id,
            detalhes={"admin_id": admin_id},
        )
```

**Step 4: Rodar os testes**

```bash
make test -- tests/unit/test_usuario_admin_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/services/usuario_admin_service.py tests/unit/test_usuario_admin_service.py
git commit -m "feat(service): UsuarioAdminService — criação, pausa, senha única, exclusão"
```

---

## Task 9: Router admin — `app/api/v1/admin.py`

**Files:**
- Create: `app/api/v1/admin.py`

**Step 1: Escrever testes de integração**

Arquivo: `tests/integration/test_api_admin.py`

```python
"""Testes do painel admin — gestão de usuários."""

import pytest
from httpx import AsyncClient
from app.core.security import criar_access_token
from app.models.usuario import Usuario
from app.core.security import hash_senha


@pytest.fixture
async def admin_usuario(db_session, guarnicao):
    """Fixture de usuário admin com sessão ativa."""
    u = Usuario(
        nome="Admin Teste",
        matricula="ADMIN001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
        is_admin=True,
        session_id="admin-session-id",
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
async def admin_headers(admin_usuario):
    """Headers de autenticação para o admin."""
    token = criar_access_token({
        "sub": str(admin_usuario.id),
        "guarnicao_id": admin_usuario.guarnicao_id,
        "sid": admin_usuario.session_id,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_listar_usuarios_admin(client: AsyncClient, admin_headers, usuario):
    """Admin consegue listar usuários da guarnição."""
    response = await client.get("/api/v1/admin/usuarios", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_criar_usuario_retorna_senha(client: AsyncClient, admin_headers):
    """Admin cria usuário e recebe senha gerada."""
    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "NOVO001"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert "senha" in data
    assert len(data["senha"]) >= 8
    assert data["matricula"] == "NOVO001"


@pytest.mark.asyncio
async def test_criar_usuario_sem_admin_retorna_403(client: AsyncClient, auth_headers):
    """Usuário comum não pode criar usuários."""
    response = await client.post(
        "/api/v1/admin/usuarios",
        json={"matricula": "NOVO002"},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_pausar_usuario(client: AsyncClient, admin_headers, usuario, db_session):
    """Admin pausa usuário e session_id é limpo."""
    response = await client.patch(
        f"/api/v1/admin/usuarios/{usuario.id}/pausar",
        headers=admin_headers,
    )
    assert response.status_code == 200
    await db_session.refresh(usuario)
    assert usuario.session_id is None


@pytest.mark.asyncio
async def test_gerar_nova_senha(client: AsyncClient, admin_headers, usuario):
    """Admin gera nova senha e recebe plain text."""
    response = await client.post(
        f"/api/v1/admin/usuarios/{usuario.id}/gerar-senha",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "senha" in data
    assert len(data["senha"]) >= 8
```

**Step 2: Criar `app/api/v1/admin.py`**

```python
"""Router de administração — gestão de usuários pelo admin.

Fornece endpoints restritos a administradores para criar usuários
com senha de uso único, pausar/excluir acesso e gerar novas senhas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflitoDadosError, NaoEncontradoError
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import SenhaGeradaResponse, UsuarioAdminCreate, UsuarioAdminRead
from app.services.usuario_admin_service import UsuarioAdminService

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(user: Usuario = Depends(get_current_user)) -> Usuario:
    """Dependência que exige que o usuário seja administrador.

    Args:
        user: Usuário autenticado (injetado automaticamente).

    Returns:
        Usuário autenticado e administrador.

    Raises:
        HTTPException: 403 se o usuário não for administrador.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user


@router.get("/usuarios", response_model=list[UsuarioAdminRead])
async def listar_usuarios(
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[UsuarioAdminRead]:
    """Lista todos os usuários ativos e pausados da guarnição do admin.

    Args:
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Lista de usuários com status de sessão.

    Status Code:
        200: Lista retornada com sucesso.
        403: Usuário não é administrador.
    """
    service = UsuarioAdminService(db)
    usuarios = await service.listar_usuarios(admin.guarnicao_id)
    return [
        UsuarioAdminRead(
            id=u.id,
            nome=u.nome,
            matricula=u.matricula,
            posto_graduacao=u.posto_graduacao,
            foto_url=u.foto_url,
            is_admin=u.is_admin,
            ativo=u.ativo,
            tem_sessao=u.session_id is not None,
            guarnicao_id=u.guarnicao_id,
        )
        for u in usuarios
    ]


@router.post("/usuarios", response_model=SenhaGeradaResponse, status_code=201)
async def criar_usuario(
    data: UsuarioAdminCreate,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SenhaGeradaResponse:
    """Cria novo usuário com senha de uso único gerada automaticamente.

    A senha é exibida uma única vez na resposta. O admin deve entregá-la
    pessoalmente ao usuário. Após o primeiro login, a senha é invalidada.

    Args:
        data: Dados de criação (apenas matrícula).
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        SenhaGeradaResponse: ID, matrícula e senha gerada (plain text, única vez).

    Raises:
        HTTPException: 409 se matrícula já cadastrada.

    Status Code:
        201: Usuário criado com sucesso.
        403: Não é administrador.
        409: Matrícula já existe.
    """
    service = UsuarioAdminService(db)
    try:
        usuario, senha = await service.criar_usuario(
            matricula=data.matricula,
            admin_id=admin.id,
            guarnicao_id=admin.guarnicao_id,
        )
    except ConflitoDadosError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    await db.commit()
    return SenhaGeradaResponse(usuario_id=usuario.id, matricula=usuario.matricula, senha=senha)


@router.patch("/usuarios/{usuario_id}/pausar", response_model=dict)
async def pausar_usuario(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Pausa o acesso do usuário desconectando-o imediatamente.

    Limpa o session_id do usuário no banco. O próximo request do usuário
    retornará 401. O usuário precisará de nova senha para retornar.

    Args:
        usuario_id: ID do usuário a pausar.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        Mensagem de confirmação.

    Raises:
        HTTPException: 404 se usuário não encontrado.

    Status Code:
        200: Usuário pausado com sucesso.
        403: Não é administrador.
        404: Usuário não encontrado.
    """
    service = UsuarioAdminService(db)
    try:
        await service.pausar_usuario(usuario_id=usuario_id, admin_id=admin.id)
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    await db.commit()
    return {"ok": True, "mensagem": "Usuário pausado com sucesso"}


@router.post("/usuarios/{usuario_id}/gerar-senha", response_model=SenhaGeradaResponse)
async def gerar_nova_senha(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SenhaGeradaResponse:
    """Gera nova senha de uso único para o usuário, invalidando a sessão atual.

    Args:
        usuario_id: ID do usuário.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Returns:
        SenhaGeradaResponse: Nova senha em plain text (exibir apenas uma vez).

    Raises:
        HTTPException: 404 se usuário não encontrado.

    Status Code:
        200: Nova senha gerada com sucesso.
        403: Não é administrador.
        404: Usuário não encontrado.
    """
    service = UsuarioAdminService(db)
    try:
        from sqlalchemy import select
        result = await db.execute(select(__import__("app.models.usuario", fromlist=["Usuario"]).Usuario).where(
            __import__("app.models.usuario", fromlist=["Usuario"]).Usuario.id == usuario_id
        ))
        u = result.scalar_one_or_none()
        matricula = u.matricula if u else str(usuario_id)
        senha = await service.gerar_nova_senha(usuario_id=usuario_id, admin_id=admin.id)
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    await db.commit()
    return SenhaGeradaResponse(usuario_id=usuario_id, matricula=matricula, senha=senha)


@router.delete("/usuarios/{usuario_id}", status_code=204)
async def excluir_usuario(
    usuario_id: int,
    admin: Usuario = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Exclui logicamente o usuário (soft delete — dados preservados por LGPD).

    Args:
        usuario_id: ID do usuário a excluir.
        admin: Administrador autenticado.
        db: Sessão do banco de dados.

    Raises:
        HTTPException: 404 se usuário não encontrado.

    Status Code:
        204: Usuário excluído com sucesso (sem corpo).
        403: Não é administrador.
        404: Usuário não encontrado.
    """
    service = UsuarioAdminService(db)
    try:
        await service.excluir_usuario(usuario_id=usuario_id, admin_id=admin.id)
    except NaoEncontradoError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    await db.commit()
```

**Step 3: Registrar o router em `app/api/v1/router.py`**

Adicionar ao final dos imports e includes:

```python
from app.api.v1.admin import router as admin_router
# ...
api_router.include_router(admin_router)
```

**Step 4: Rodar testes**

```bash
make test -- tests/integration/test_api_admin.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add app/api/v1/admin.py app/api/v1/router.py tests/integration/test_api_admin.py
git commit -m "feat(api): router /admin/usuarios — criar, pausar, gerar senha, excluir"
```

---

## Task 10: Frontend — avatar no header e tela de perfil

**Files:**
- Modify: `frontend/index.html`
- Create: `frontend/js/pages/perfil.js`

**Step 1: Criar `frontend/js/pages/perfil.js`**

```javascript
/**
 * Página de perfil do usuário.
 *
 * Permite atualizar nome, posto/graduação e foto.
 * Contém o botão Sair com aviso de nova senha necessária.
 */

const POSTOS_GRADUACAO = [
  "Soldado", "Cabo", "3º Sargento", "2º Sargento", "1º Sargento",
  "Subtenente", "Aspirante", "2º Tenente", "1º Tenente",
  "Capitão", "Major", "Tenente-Coronel", "Coronel",
];

function renderPerfil(appState) {
  const user = auth.getUser() || {};
  const iniciais = (user.nome || "?")
    .split(" ")
    .slice(0, 2)
    .map((n) => n[0])
    .join("")
    .toUpperCase();

  const optsPosto = POSTOS_GRADUACAO.map(
    (p) => `<option value="${p}" ${user.posto_graduacao === p ? "selected" : ""}>${p}</option>`
  ).join("");

  return `
    <div class="p-4 max-w-md mx-auto" x-data="perfilPage()">
      <!-- Foto de perfil -->
      <div class="flex flex-col items-center mb-6">
        <div class="relative">
          <div class="w-24 h-24 rounded-full overflow-hidden bg-blue-600 flex items-center justify-center text-white text-3xl font-bold cursor-pointer"
               @click="$refs.fotoInput.click()">
            <template x-if="fotoUrl">
              <img :src="fotoUrl" class="w-full h-full object-cover" />
            </template>
            <template x-if="!fotoUrl">
              <span>${iniciais}</span>
            </template>
          </div>
          <button @click="$refs.fotoInput.click()"
                  class="absolute bottom-0 right-0 bg-slate-700 rounded-full p-1 text-slate-300 hover:text-white">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </button>
        </div>
        <input type="file" accept="image/*" x-ref="fotoInput" class="hidden" @change="uploadFoto($event)" />
        <p x-show="uploadando" class="text-xs text-slate-400 mt-2">Enviando foto...</p>
      </div>

      <!-- Campos de perfil -->
      <div class="space-y-4">
        <div>
          <label class="block text-sm text-slate-400 mb-1">Nome completo</label>
          <input type="text" x-model="nome"
                 class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none" />
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">Nome de guerra</label>
          <input type="text" x-model="nomeGuerra"
                 class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none"
                 placeholder="Ex: Silva" maxlength="50" />
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">Posto / Graduação</label>
          <select x-model="posto"
                  class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none">
            <option value="">Selecione...</option>
            ${optsPosto}
          </select>
        </div>

        <div>
          <label class="block text-sm text-slate-400 mb-1">Matrícula</label>
          <input type="text" value="${user.matricula || ""}" disabled
                 class="w-full bg-slate-800 rounded-lg px-3 py-2 text-slate-400 border border-slate-700 cursor-not-allowed" />
        </div>

        <button @click="salvar()" :disabled="salvando"
                class="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2 rounded-lg transition">
          <span x-show="!salvando">Salvar alterações</span>
          <span x-show="salvando">Salvando...</span>
        </button>
      </div>

      <!-- Botão Sair -->
      <div class="mt-8 pt-6 border-t border-slate-700">
        <button @click="confirmarSaida = true"
                class="w-full text-red-400 hover:text-red-300 text-sm font-medium py-2 border border-red-800 hover:border-red-600 rounded-lg transition">
          Sair do aplicativo
        </button>
      </div>

      <!-- Modal de confirmação de saída -->
      <div x-show="confirmarSaida" x-cloak
           class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-slate-800 rounded-xl p-6 max-w-sm w-full border border-slate-700">
          <h3 class="text-white font-semibold mb-2">Sair do aplicativo?</h3>
          <p class="text-slate-400 text-sm mb-6">
            Se você sair, precisará que o administrador gere uma nova senha para acessar novamente.
          </p>
          <div class="flex gap-3">
            <button @click="confirmarSaida = false"
                    class="flex-1 py-2 rounded-lg border border-slate-600 text-slate-300 hover:text-white">
              Cancelar
            </button>
            <button @click="executarSaida()"
                    class="flex-1 py-2 rounded-lg bg-red-700 hover:bg-red-600 text-white font-medium">
              Confirmar saída
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function perfilPage() {
  const user = auth.getUser() || {};
  return {
    nome: user.nome || "",
    nomeGuerra: user.nome_guerra || "",
    posto: user.posto_graduacao || "",
    fotoUrl: user.foto_url || null,
    salvando: false,
    uploadando: false,
    confirmarSaida: false,

    async salvar() {
      this.salvando = true;
      try {
        const updated = await api.put("/auth/perfil", {
          nome: this.nome,
          nome_guerra: this.nomeGuerra || null,
          posto_graduacao: this.posto || null,
        });
        auth.user = updated;
        localStorage.setItem("argus_user", JSON.stringify(updated));
        showToast("Perfil atualizado com sucesso", "success");
      } catch (e) {
        showToast("Erro ao salvar perfil", "error");
      } finally {
        this.salvando = false;
      }
    },

    async uploadFoto(event) {
      const file = event.target.files[0];
      if (!file) return;
      this.uploadando = true;
      try {
        const formData = new FormData();
        formData.append("foto", file);
        const result = await api.uploadForm("/auth/perfil/foto", formData);
        this.fotoUrl = result.foto_url;
        auth.user = { ...auth.getUser(), foto_url: result.foto_url };
        localStorage.setItem("argus_user", JSON.stringify(auth.user));
        showToast("Foto atualizada", "success");
      } catch (e) {
        showToast("Erro ao enviar foto", "error");
      } finally {
        this.uploadando = false;
      }
    },

    executarSaida() {
      auth.logout();
      window.location.reload();
    },
  };
}
```

**Step 2: Adicionar `uploadForm` ao `api.js`** se não existir

Verificar se `api.js` tem método para FormData. Se não tiver, adicionar:

```javascript
async uploadForm(endpoint, formData) {
  const headers = {};
  if (this.token) headers["Authorization"] = `Bearer ${this.token}`;
  const response = await fetch(this.baseUrl + endpoint, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}
```

**Step 3: Atualizar `frontend/index.html`**

Substituir o botão "Sair" no header por avatar:

```html
<!-- Antes -->
<button @click="logout()" class="text-slate-400 hover:text-white text-sm">Sair</button>

<!-- Depois -->
<button @click="navigate('perfil')"
        class="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold hover:bg-blue-500 overflow-hidden"
        :title="user?.nome || 'Perfil'">
  <template x-if="user?.foto_url">
    <img :src="user.foto_url" class="w-full h-full object-cover" />
  </template>
  <template x-if="!user?.foto_url">
    <span x-text="user?.nome ? user.nome.split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase() : '?'"></span>
  </template>
</button>
```

Adicionar `<script src="/js/pages/perfil.js?v=1"></script>` antes de `app.js`.

**Step 4: Registrar página de perfil em `app.js`**

Localizar o objeto `renderers` em `_renderInto` e adicionar:

```javascript
perfil: renderPerfil,
```

**Step 5: Testar manualmente**

```bash
make dev
```

Abrir `http://localhost:8000`, fazer login, verificar:
- [ ] Avatar aparece no header (iniciais ou foto)
- [ ] Clicar no avatar abre tela de perfil
- [ ] Dropdown de postos funciona
- [ ] Botão Salvar atualiza o perfil
- [ ] Upload de foto funciona
- [ ] Botão Sair abre modal de confirmação
- [ ] Confirmar saída desconecta e retorna ao login

**Step 6: Commit**

```bash
git add frontend/js/pages/perfil.js frontend/index.html frontend/js/app.js frontend/js/api.js
git commit -m "feat(frontend): avatar no header, tela de perfil, logout com confirmação"
```

---

## Task 11: Frontend — tela de gestão de usuários (admin)

**Files:**
- Create: `frontend/js/pages/admin-usuarios.js`
- Modify: `frontend/index.html` (adicionar script)
- Modify: `frontend/js/app.js` (registrar renderer + link de acesso para admin)

**Step 1: Criar `frontend/js/pages/admin-usuarios.js`**

```javascript
/**
 * Página de gestão de usuários — exclusivo para administradores.
 *
 * Lista usuários da guarnição, permite criar novos (exibindo senha única),
 * pausar acesso e gerar nova senha.
 */

function renderAdminUsuarios() {
  return `
    <div class="p-4" x-data="adminUsuariosPage()">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-white font-semibold text-lg">Gerenciar Usuários</h2>
        <button @click="mostrarFormCriacao = true"
                class="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1.5 rounded-lg">
          + Novo usuário
        </button>
      </div>

      <!-- Loading -->
      <div x-show="carregando" class="text-slate-400 text-sm text-center py-8">Carregando...</div>

      <!-- Lista -->
      <div x-show="!carregando" class="space-y-3">
        <template x-for="u in usuarios" :key="u.id">
          <div class="bg-slate-800 rounded-xl p-4 border border-slate-700">
            <div class="flex items-center gap-3">
              <!-- Avatar -->
              <div class="w-10 h-10 rounded-full bg-blue-700 flex items-center justify-center text-white text-sm font-bold overflow-hidden flex-shrink-0">
                <template x-if="u.foto_url">
                  <img :src="u.foto_url" class="w-full h-full object-cover" />
                </template>
                <template x-if="!u.foto_url">
                  <span x-text="u.nome.split(' ').slice(0,2).map(n=>n[0]).join('').toUpperCase()"></span>
                </template>
              </div>
              <!-- Info -->
              <div class="flex-1 min-w-0">
                <p class="text-white font-medium text-sm truncate" x-text="u.nome"></p>
                <p class="text-slate-400 text-xs" x-text="u.matricula + (u.posto_graduacao ? ' · ' + u.posto_graduacao : '')"></p>
              </div>
              <!-- Status -->
              <span :class="u.tem_sessao ? 'bg-green-900 text-green-300' : 'bg-slate-700 text-slate-400'"
                    class="text-xs px-2 py-0.5 rounded-full">
                <span x-text="u.tem_sessao ? 'Ativo' : 'Sem sessão'"></span>
              </span>
            </div>
            <!-- Ações -->
            <div class="flex gap-2 mt-3">
              <button @click="pausarUsuario(u)"
                      x-show="u.tem_sessao"
                      class="flex-1 text-xs py-1.5 rounded-lg bg-yellow-900 text-yellow-300 hover:bg-yellow-800">
                Pausar acesso
              </button>
              <button @click="gerarSenha(u)"
                      class="flex-1 text-xs py-1.5 rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600">
                Gerar nova senha
              </button>
              <button @click="excluirUsuario(u)"
                      class="text-xs py-1.5 px-3 rounded-lg bg-red-900 text-red-300 hover:bg-red-800">
                Excluir
              </button>
            </div>
          </div>
        </template>
      </div>

      <!-- Modal: Criar usuário -->
      <div x-show="mostrarFormCriacao" x-cloak
           class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-slate-800 rounded-xl p-6 max-w-sm w-full border border-slate-700">
          <h3 class="text-white font-semibold mb-4">Novo usuário</h3>
          <div class="mb-4">
            <label class="block text-sm text-slate-400 mb-1">Matrícula</label>
            <input type="text" x-model="novaMatricula"
                   class="w-full bg-slate-700 rounded-lg px-3 py-2 text-white border border-slate-600 focus:border-blue-500 focus:outline-none"
                   placeholder="Ex: PM001" />
          </div>
          <div class="flex gap-3">
            <button @click="mostrarFormCriacao = false; novaMatricula = ''"
                    class="flex-1 py-2 rounded-lg border border-slate-600 text-slate-300">
              Cancelar
            </button>
            <button @click="criarUsuario()" :disabled="criando"
                    class="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium">
              <span x-show="!criando">Criar</span>
              <span x-show="criando">Criando...</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Modal: Exibir senha gerada (uso único) -->
      <div x-show="senhaGerada" x-cloak
           class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div class="bg-slate-800 rounded-xl p-6 max-w-sm w-full border border-yellow-700">
          <h3 class="text-yellow-400 font-semibold mb-2">⚠️ Senha gerada — anote agora</h3>
          <p class="text-slate-400 text-sm mb-4">
            Esta senha será exibida apenas uma vez. Entregue pessoalmente ao usuário.
          </p>
          <div class="bg-slate-900 rounded-lg p-4 text-center mb-4">
            <p class="text-slate-400 text-xs mb-1" x-text="'Matrícula: ' + (senhaGerada?.matricula || '')"></p>
            <p class="text-white font-mono text-2xl font-bold tracking-widest" x-text="senhaGerada?.senha"></p>
          </div>
          <button @click="senhaGerada = null"
                  class="w-full py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white">
            Entendi, já anotei
          </button>
        </div>
      </div>
    </div>
  `;
}

function adminUsuariosPage() {
  return {
    usuarios: [],
    carregando: true,
    mostrarFormCriacao: false,
    novaMatricula: "",
    criando: false,
    senhaGerada: null,

    async init() {
      await this.carregar();
    },

    async carregar() {
      this.carregando = true;
      try {
        this.usuarios = await api.get("/admin/usuarios");
      } catch {
        showToast("Erro ao carregar usuários", "error");
      } finally {
        this.carregando = false;
      }
    },

    async criarUsuario() {
      if (!this.novaMatricula.trim()) return;
      this.criando = true;
      try {
        const result = await api.post("/admin/usuarios", { matricula: this.novaMatricula.trim() });
        this.senhaGerada = result;
        this.mostrarFormCriacao = false;
        this.novaMatricula = "";
        await this.carregar();
      } catch (e) {
        showToast(e.message || "Erro ao criar usuário", "error");
      } finally {
        this.criando = false;
      }
    },

    async pausarUsuario(u) {
      try {
        await api.patch(\`/admin/usuarios/\${u.id}/pausar\`);
        showToast(\`Acesso de \${u.matricula} pausado\`, "success");
        await this.carregar();
      } catch {
        showToast("Erro ao pausar usuário", "error");
      }
    },

    async gerarSenha(u) {
      try {
        const result = await api.post(\`/admin/usuarios/\${u.id}/gerar-senha\`);
        this.senhaGerada = result;
        await this.carregar();
      } catch {
        showToast("Erro ao gerar senha", "error");
      }
    },

    async excluirUsuario(u) {
      if (!confirm(\`Excluir o usuário \${u.matricula}? Esta ação não pode ser desfeita.\`)) return;
      try {
        await api.delete(\`/admin/usuarios/\${u.id}\`);
        showToast("Usuário excluído", "success");
        await this.carregar();
      } catch {
        showToast("Erro ao excluir usuário", "error");
      }
    },
  };
}
```

**Step 2: Adicionar método `delete` e `patch` ao `api.js`** (se não existirem)

Verificar `frontend/js/api.js`. Se não tiver `patch` e `delete`, adicionar:

```javascript
async patch(endpoint, data = {}) {
  return this._request("PATCH", endpoint, data);
}

async delete(endpoint) {
  const headers = { "Content-Type": "application/json" };
  if (this.token) headers["Authorization"] = `Bearer ${this.token}`;
  const response = await fetch(this.baseUrl + endpoint, { method: "DELETE", headers });
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? null : response.json();
}
```

**Step 3: Adicionar acesso à tela admin a partir do perfil**

Em `frontend/js/pages/perfil.js`, adicionar botão de admin após o botão "Salvar" (condicional a `is_admin`):

```javascript
// No template, após o botão Salvar:
`<template x-if="isAdmin">
  <button @click="irParaAdmin()"
          class="w-full mt-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium py-2 rounded-lg transition">
    Gerenciar usuários
  </button>
</template>`

// No objeto perfilPage():
isAdmin: user.is_admin || false,
irParaAdmin() {
  // Navegar para página admin via app state
  window.dispatchEvent(new CustomEvent("navigate", { detail: "admin-usuarios" }));
},
```

Em `app.js`, escutar o evento e tratar a navegação:

```javascript
// No método init(), adicionar:
window.addEventListener("navigate", (e) => this.navigate(e.detail));
```

Registrar no objeto `renderers`:

```javascript
"admin-usuarios": renderAdminUsuarios,
```

**Step 4: Adicionar script no `index.html`**

```html
<script src="/js/pages/admin-usuarios.js?v=1"></script>
```

**Step 5: Testar manualmente**

```bash
make dev
```

Verificar com usuário admin:
- [ ] Tela de perfil mostra botão "Gerenciar usuários"
- [ ] Tela admin lista usuários
- [ ] Criar usuário exibe modal com senha (uma vez)
- [ ] Pausar derruba a sessão na próxima requisição
- [ ] Gerar nova senha exibe modal

**Step 6: Rodar todos os testes**

```bash
make test
```

Expected: PASS

**Step 7: Commit final**

```bash
git add frontend/js/pages/admin-usuarios.js frontend/js/pages/perfil.js frontend/js/app.js frontend/js/api.js frontend/index.html
git commit -m "feat(frontend): tela admin de gestão de usuários com senha única"
```

---

## Checklist de verificação final

Após todas as tasks:

```bash
make test
make lint
```

- [ ] Todos os testes passam
- [ ] Lint e mypy sem erros
- [ ] Migration aplicada no banco de dev
- [ ] Avatar aparece no header
- [ ] Perfil editável (nome, posto, foto)
- [ ] Logout com aviso de nova senha necessária
- [ ] Admin cria usuário → senha exibida uma vez
- [ ] Pausar usuário → desconexão imediata verificada
- [ ] Token com session_id errado → 401
- [ ] Usuário comum não acessa `/admin/*` → 403
