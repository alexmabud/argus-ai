"""Repositório especializado para Foto com busca facial pgvector.

Estende BaseRepository com métodos de busca por pessoa, abordagem
e busca por similaridade facial via pgvector (cosine distance 512-dim).
"""

from collections.abc import Sequence
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.foto import Foto
from app.repositories.base import BaseRepository


class FotoRepository(BaseRepository[Foto]):
    """Repositório para operações de Foto com busca facial pgvector.

    Estende BaseRepository com busca por pessoa, abordagem e
    busca por similaridade facial via pgvector (cosine distance).

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

    async def get_by_pessoa(self, pessoa_id: int, skip: int = 0, limit: int = 50) -> Sequence[Foto]:
        """Lista fotos associadas a uma pessoa (paginado no banco).

        Args:
            pessoa_id: ID da pessoa.
            skip: Registros a pular (OFFSET).
            limit: Máximo de resultados (LIMIT) — evita carregar tudo em memória.

        Returns:
            Sequência de Fotos da pessoa, ordenadas por data/hora decrescente.
        """
        query = (
            select(Foto)
            .where(Foto.pessoa_id == pessoa_id, Foto.ativo == True)  # noqa: E712
            .order_by(Foto.data_hora.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_abordagem(self, abordagem_id: int) -> int:
        """Conta fotos ativas vinculadas a uma abordagem.

        Usado pelo enforcement de QUOTA_FOTOS_POR_ABORDAGEM no upload.

        Args:
            abordagem_id: ID da abordagem.

        Returns:
            Numero de fotos ativas (nao soft-deleted).
        """
        query = select(func.count(Foto.id)).where(
            Foto.abordagem_id == abordagem_id,
            Foto.ativo == True,  # noqa: E712
        )
        result = await self.db.execute(query)
        return int(result.scalar_one())

    async def get_by_abordagem(
        self, abordagem_id: int, skip: int = 0, limit: int = 50
    ) -> Sequence[Foto]:
        """Lista fotos associadas a uma abordagem (paginado no banco).

        Args:
            abordagem_id: ID da abordagem.
            skip: Registros a pular (OFFSET).
            limit: Máximo de resultados (LIMIT) — evita carregar tudo em memória.

        Returns:
            Sequência de Fotos da abordagem, ordenadas por data/hora decrescente.
        """
        query = (
            select(Foto)
            .where(Foto.abordagem_id == abordagem_id, Foto.ativo == True)  # noqa: E712
            .order_by(Foto.data_hora.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def buscar_por_similaridade_facial(
        self,
        embedding: list[float],
        top_k: int = 5,
        threshold: float = 0.6,
    ) -> Sequence[tuple[Foto, float]]:
        """Busca fotos por similaridade facial via pgvector.

        Usa distância cosseno (operador <=>) nos embeddings faciais
        de 512 dimensões (InsightFace) para encontrar rostos similares.

        Args:
            embedding: Vetor de embedding facial 512-dimensional.
            top_k: Número máximo de resultados (padrão: 5).
            threshold: Limiar mínimo de similaridade 0-1 (padrão: 0.6).

        Returns:
            Sequência de tuplas (Foto, similaridade) ordenadas
            por similaridade decrescente.
        """
        similarity = 1 - Foto.embedding_face.cosine_distance(embedding)

        query = (
            select(Foto, similarity.label("similaridade"))
            .where(
                Foto.ativo == True,  # noqa: E712
                Foto.face_processada == True,  # noqa: E712
                Foto.embedding_face.isnot(None),
                similarity >= threshold,
            )
            .order_by(similarity.desc())
            .limit(top_k)
        )

        result = await self.db.execute(query)
        return cast(Sequence[tuple[Foto, float]], result.all())
