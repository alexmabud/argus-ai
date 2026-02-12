"""Repositório especializado para Passagem com busca por lei/artigo.

Estende BaseRepository com métodos de busca por combinação lei+artigo
e busca textual por nome de crime.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.passagem import Passagem
from app.repositories.base import BaseRepository


class PassagemRepository(BaseRepository[Passagem]):
    """Repositório para operações de Passagem (tipo penal).

    Estende BaseRepository com busca exata por lei+artigo e
    busca textual por nome de crime.

    Attributes:
        model: Classe Passagem.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório de Passagem.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(Passagem, db)

    async def get_by_lei_artigo(self, lei: str, artigo: str) -> Passagem | None:
        """Busca passagem por combinação exata de lei e artigo.

        Args:
            lei: Lei ou código penal (ex: "CP", "LCP").
            artigo: Número do artigo (ex: "121", "33").

        Returns:
            Passagem encontrada ou None.
        """
        query = select(Passagem).where(
            Passagem.lei == lei,
            Passagem.artigo == artigo,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search(
        self,
        lei: str | None = None,
        artigo: str | None = None,
        nome_crime: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Passagem]:
        """Busca passagens com filtros combinados.

        Todos os filtros são opcionais e combinados com AND quando informados.
        Nome de crime usa ILIKE para busca parcial.

        Args:
            lei: Filtro por lei (busca exata).
            artigo: Filtro por artigo (busca exata).
            nome_crime: Filtro por nome do crime (busca parcial ILIKE).
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Passagens que satisfazem os filtros.
        """
        query = select(Passagem)

        if lei:
            query = query.where(Passagem.lei == lei)
        if artigo:
            query = query.where(Passagem.artigo == artigo)
        if nome_crime:
            query = query.where(Passagem.nome_crime.ilike(f"%{nome_crime}%"))

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
