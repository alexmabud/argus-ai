"""Repositório especializado para Foto com busca por pessoa e abordagem.

Estende BaseRepository com métodos de busca por pessoa e abordagem
associadas às fotos.
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.foto import Foto
from app.repositories.base import BaseRepository


class FotoRepository(BaseRepository[Foto]):
    """Repositório para operações de Foto.

    Estende BaseRepository com busca por pessoa e abordagem,
    e listagem de fotos pendentes de processamento facial.

    Attributes:
        model: Classe Foto.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório de Foto.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(Foto, db)

    async def get_by_pessoa(self, pessoa_id: int) -> Sequence[Foto]:
        """Lista fotos associadas a uma pessoa.

        Args:
            pessoa_id: ID da pessoa.

        Returns:
            Sequência de Fotos da pessoa, ordenadas por data/hora decrescente.
        """
        query = select(Foto).where(Foto.pessoa_id == pessoa_id).order_by(Foto.data_hora.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_abordagem(self, abordagem_id: int) -> Sequence[Foto]:
        """Lista fotos associadas a uma abordagem.

        Args:
            abordagem_id: ID da abordagem.

        Returns:
            Sequência de Fotos da abordagem, ordenadas por data/hora decrescente.
        """
        query = (
            select(Foto).where(Foto.abordagem_id == abordagem_id).order_by(Foto.data_hora.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()
