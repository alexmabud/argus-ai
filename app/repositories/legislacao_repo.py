"""Repositório de Legislação com busca semântica pgvector.

Estende BaseRepository com queries de busca vetorial por similaridade
cosseno para artigos de legislação. Dados globais (sem multi-tenancy).
"""

from collections.abc import Sequence
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legislacao import Legislacao
from app.repositories.base import BaseRepository


class LegislacaoRepository(BaseRepository[Legislacao]):
    """Repositório de acesso a dados de legislação.

    Estende BaseRepository com busca semântica via pgvector (cosine distance)
    e busca por lei+artigo. Legislação é dado global, portanto NÃO aplica
    filtro multi-tenant (guarnicao_id).

    Attributes:
        model: Classe Legislacao.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório vinculado ao modelo Legislacao.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(Legislacao, db)

    async def search_semantic(
        self,
        embedding: list[float],
        top_k: int = 3,
        threshold: float = 0.3,
    ) -> Sequence[tuple[Legislacao, float]]:
        """Busca legislação por similaridade semântica via pgvector.

        Usa distância cosseno (operador <=>) para encontrar artigos de
        legislação semanticamente similares ao embedding fornecido.
        Sem filtro multi-tenant (legislação é dado global).

        Args:
            embedding: Vetor de embedding 384-dimensional da query.
            top_k: Número máximo de resultados (padrão: 3).
            threshold: Limiar mínimo de similaridade 0-1 (padrão: 0.3).

        Returns:
            Sequência de tuplas (Legislacao, similaridade) ordenadas
            por similaridade decrescente.
        """
        similarity = 1 - Legislacao.embedding.cosine_distance(embedding)

        query = (
            select(Legislacao, similarity.label("similaridade"))
            .where(
                Legislacao.ativo == True,  # noqa: E712
                Legislacao.embedding.isnot(None),
                similarity >= threshold,
            )
            .order_by(similarity.desc())
            .limit(top_k)
        )

        result = await self.db.execute(query)
        return cast(Sequence[tuple[Legislacao, float]], result.all())

    async def get_by_lei_artigo(self, lei: str, artigo: str) -> Legislacao | None:
        """Busca legislação por combinação lei + artigo.

        Args:
            lei: Designação da lei (ex: "CP", "Lei 11343/06").
            artigo: Número do artigo (ex: "121", "33").

        Returns:
            Legislação encontrada ou None.
        """
        result = await self.db.execute(
            select(Legislacao).where(
                Legislacao.lei == lei,
                Legislacao.artigo == artigo,
                Legislacao.ativo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
