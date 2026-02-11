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
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession):
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
    token = criar_access_token(
        {
            "sub": str(usuario.id),
            "guarnicao_id": usuario.guarnicao_id,
        }
    )
    return {"Authorization": f"Bearer {token}"}
