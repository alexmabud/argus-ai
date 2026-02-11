"""Gerenciamento de sessões do banco de dados com SQLAlchemy async.

Cria engine async PostgreSQL com pool de conexões e factory de sessões.
Fornece dependency injection para obter sessões em routers.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

#: Engine async do PostgreSQL com asyncpg como driver.
#: Pool é configurável via DATABASE_POOL_SIZE e DATABASE_MAX_OVERFLOW.
#: Echo de SQL é habilitado em modo DEBUG.
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

#: Factory de sessões async com expire_on_commit=False para permitir
#: acesso a atributos após commit sem necessidade de refresh.
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency para obter sessão do banco de dados.

    Cria uma nova sessão, gerencia transação e cleanup automático.
    Em caso de erro, faz rollback e propaga exceção. Sessão é commitada
    automaticamente ao término sem erros.

    Yields:
        AsyncSession: Sessão async para ser injetada em routers/serviços.

    Raises:
        Propaga qualquer exceção ocorrida durante processamento.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
