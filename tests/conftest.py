"""Configurações e fixtures pytest para testes da aplicação.

Fornece fixtures para:
- Configuração do banco de dados de testes
- Cliente HTTP assincrónico para testes de API
- Dados de teste (guarnição, usuário, pessoa, veículo, abordagem, passagem)
- Headers com autenticação JWT
"""

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.security import criar_access_token, hash_senha
from app.database.session import get_db
from app.main import create_app
from app.models.abordagem import Abordagem
from app.models.base import Base
from app.models.guarnicao import Guarnicao
from app.models.passagem import Passagem
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.models.veiculo import Veiculo

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


@pytest.fixture
async def pessoa(db_session: AsyncSession, guarnicao: Guarnicao) -> Pessoa:
    """Fixture que cria uma pessoa de teste.

    Insere uma pessoa no banco com dados básicos para uso em
    testes de CRUD, busca e relacionamentos.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição para associar à pessoa.

    Returns:
        Pessoa: Objeto de pessoa com nome "João da Silva".
    """
    p = Pessoa(
        nome="João da Silva",
        apelido="Joãozinho",
        guarnicao_id=guarnicao.id,
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest.fixture
async def veiculo(db_session: AsyncSession, guarnicao: Guarnicao) -> Veiculo:
    """Fixture que cria um veículo de teste.

    Insere um veículo no banco com placa Mercosul para uso em
    testes de CRUD e busca por placa.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição para associar ao veículo.

    Returns:
        Veiculo: Objeto de veículo com placa "ABC1D23".
    """
    v = Veiculo(
        placa="ABC1D23",
        modelo="Gol",
        cor="Branco",
        ano=2020,
        tipo="Carro",
        guarnicao_id=guarnicao.id,
    )
    db_session.add(v)
    await db_session.flush()
    return v


@pytest.fixture
async def abordagem(db_session: AsyncSession, guarnicao: Guarnicao, usuario: Usuario) -> Abordagem:
    """Fixture que cria uma abordagem de teste.

    Insere uma abordagem no banco com coordenadas do Rio de Janeiro
    para uso em testes de CRUD e busca geoespacial.

    Args:
        db_session: Sessão do banco de testes.
        guarnicao: Fixture de guarnição para associar à abordagem.
        usuario: Fixture de usuário que realizou a abordagem.

    Returns:
        Abordagem: Objeto de abordagem com coordenadas do Rio de Janeiro.
    """
    a = Abordagem(
        data_hora=datetime.now(UTC),
        latitude=-22.9068,
        longitude=-43.1729,
        endereco_texto="Av. Brasil, 1000 - Centro, Rio de Janeiro",
        usuario_id=usuario.id,
        guarnicao_id=guarnicao.id,
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest.fixture
async def passagem(db_session: AsyncSession) -> Passagem:
    """Fixture que cria uma passagem criminal de teste.

    Insere uma passagem do Código Penal para uso em testes
    de catálogo e vinculação com abordagens.

    Args:
        db_session: Sessão do banco de testes.

    Returns:
        Passagem: Objeto de passagem — Art. 121 CP (Homicídio Simples).
    """
    p = Passagem(
        lei="CP",
        artigo="121",
        nome_crime="Homicídio Simples",
    )
    db_session.add(p)
    await db_session.flush()
    return p
