"""Repositório de Ocorrência com busca semântica pgvector.

Estende BaseRepository com queries de busca vetorial por similaridade
cosseno para ocorrências policiais, com filtros multi-tenant e threshold.
"""

from collections.abc import Sequence
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocorrencia import Ocorrencia
from app.repositories.base import BaseRepository


class OcorrenciaRepository(BaseRepository[Ocorrencia]):
    """Repositório de acesso a dados de ocorrências policiais.

    Estende BaseRepository com busca semântica via pgvector (cosine distance)
    e busca por número de ocorrência. Aplica filtros multi-tenant
    (guarnicao_id), soft delete (ativo=True) e processada=True.

    Attributes:
        model: Classe Ocorrencia.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório vinculado ao modelo Ocorrencia.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(Ocorrencia, db)

    async def search_semantic(
        self,
        embedding: list[float],
        guarnicao_id: int,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> Sequence[tuple[Ocorrencia, float]]:
        """Busca ocorrências por similaridade semântica via pgvector.

        Usa distância cosseno (operador <=>) para encontrar ocorrências
        semanticamente similares ao embedding fornecido. Aplica filtros
        de multi-tenancy, soft delete e processamento completo.

        Args:
            embedding: Vetor de embedding 384-dimensional da query.
            guarnicao_id: ID da guarnição para isolamento multi-tenant.
            top_k: Número máximo de resultados (padrão: 5).
            threshold: Limiar mínimo de similaridade 0-1 (padrão: 0.3).

        Returns:
            Sequência de tuplas (Ocorrencia, similaridade) ordenadas
            por similaridade decrescente.
        """
        similarity = 1 - Ocorrencia.embedding.cosine_distance(embedding)

        query = (
            select(Ocorrencia, similarity.label("similaridade"))
            .where(
                Ocorrencia.guarnicao_id == guarnicao_id,
                Ocorrencia.ativo == True,  # noqa: E712
                Ocorrencia.processada == True,  # noqa: E712
                Ocorrencia.embedding.isnot(None),
                similarity >= threshold,
            )
            .order_by(similarity.desc())
            .limit(top_k)
        )

        result = await self.db.execute(query)
        return cast(Sequence[tuple[Ocorrencia, float]], result.all())

    async def get_by_numero(self, numero_ocorrencia: str) -> Ocorrencia | None:
        """Busca ocorrência por número único do BO.

        Args:
            numero_ocorrencia: Número do boletim de ocorrência.

        Returns:
            Ocorrência encontrada ou None.
        """
        result = await self.db.execute(
            select(Ocorrencia).where(
                Ocorrencia.numero_ocorrencia == numero_ocorrencia,
                Ocorrencia.ativo == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
