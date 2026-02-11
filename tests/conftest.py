"""Configurações e fixtures pytest para testes da aplicação.

Fornece fixtures para:
- Configuração do banco de dados de testes
- Cliente HTTP assincrónico para testes de API
- Dados de teste (guarnição, usuário, headers com autenticação)
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import criar_access_token, hash_senha
from app.database.session import get_db
from app.main import create_app
from app.models.base import Base
from app.models.guarnicao import Guarnicao
from app.models.usuario import Usuario

test_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    """Fixture que prepara e limpa o banco de dados para cada teste.

    Cria todas as tabelas antes do teste e remove tudo após, garantindo
    isolamento entre testes. Executa automaticamente para cada teste.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    """Fixture que fornece uma sessão do banco de dados para testes.

    Returns:
        AsyncSession: Sessão assincrónica do SQLAlchemy para testes.
    """
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession):
    """Fixture que fornece um cliente HTTP assincrónico para testes de API.

    Cria uma instância da aplicação com a dependência de banco de dados
    substituída pela sessão de teste.

    Args:
        db_session: Sessão do banco de dados fornecida pela fixture db_session.

    Returns:
        AsyncClient: Cliente HTTP assincrónico para fazer requisições aos endpoints.
    """
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def guarnicao(db_session: AsyncSession) -> Guarnicao:
    """Fixture que cria uma guarnição de teste.

    Insere uma guarnição no banco de dados com valores padrão para uso
    em testes que requerem contexto de guarnição.

    Args:
        db_session: Sessão do banco de testes.

    Returns:
        Guarnicao: Objeto de guarnição com valores padrão (3a Cia - GU 01).
    """
    g = Guarnicao(
        nome="3a Cia - GU 01",
        unidade="3o BPM",
        codigo="3BPM-3CIA-GU01",
    )
    db_session.add(g)
    await db_session.flush()
    return g


@pytest.fixture
async def usuario(db_session: AsyncSession, guarnicao: Guarnicao) -> Usuario:
    """Fixture que cria um usuário de teste autenticado.

    Insere um usuário no banco de dados associado a uma guarnição,
    com credenciais padrão para testes de autenticação e autorização.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição para associar ao usuário.

    Returns:
        Usuario: Objeto de usuário com matrícula TEST001 e senha123.
    """
    u = Usuario(
        nome="Agente Teste",
        matricula="TEST001",
        senha_hash=hash_senha("senha123"),
        guarnicao_id=guarnicao.id,
    )
    db_session.add(u)
    await db_session.flush()
    return u


@pytest.fixture
def auth_headers(usuario: Usuario) -> dict:
    """Fixture que gera headers com token de autenticação válido.

    Cria um token JWT de acesso válido para o usuário de teste e
    o formata como header Authorization para requisições autenticadas.

    Args:
        usuario: Fixture de usuário para gerar token.

    Returns:
        dict: Dicionário com header Authorization contendo Bearer token válido.
    """
    token = criar_access_token(
        {
            "sub": str(usuario.id),
            "guarnicao_id": usuario.guarnicao_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}
