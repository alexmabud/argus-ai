"""Repositório de Ocorrência com busca semântica pgvector.

Estende BaseRepository com queries de busca vetorial por similaridade
cosseno para ocorrências policiais, com filtros multi-tenant e threshold.
"""

from collections.abc import Sequence
from datetime import date
from typing import cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ocorrencia import Ocorrencia
from app.repositories.base import BaseRepository
from app.services.text_utils import escape_like as _escape_like


class OcorrenciaRepository(BaseRepository[Ocorrencia]):
    """Repositório de acesso a dados de ocorrências policiais.

    Estende BaseRepository com busca semântica via pgvector (cosine distance)
    e busca por número de ocorrência. Aplica filtros multi-tenant
    (guarnicao_id) e soft delete (ativo=True). Busca semântica adiciona
    filtro processada=True.

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

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        guarnicao_id: int | None = None,
    ) -> Sequence[Ocorrencia]:
        """Obtém todas as ocorrências ordenadas por data_ocorrencia DESC.

        Sobrescreve o método base para garantir ordenação pela data do fato
        ocorrido, do mais recente para o mais antigo.

        Args:
            skip: Número de registros a pular (padrão: 0).
            limit: Número máximo de registros a retornar (padrão: 100).
            guarnicao_id: Identificador da guarnição para filtro multi-tenant.

        Returns:
            Sequência de ocorrências ordenadas por data_ocorrencia DESC.
        """
        query = select(Ocorrencia).where(Ocorrencia.ativo == True)  # noqa: E712

        if guarnicao_id is not None:
            query = query.where(Ocorrencia.guarnicao_id == guarnicao_id)

        query = query.order_by(Ocorrencia.data_ocorrencia.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

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

    async def buscar(
        self,
        guarnicao_id: int,
        nome: str | None = None,
        rap: str | None = None,
        data: date | None = None,
        limit: int = 20,
    ) -> list[Ocorrencia]:
        """Busca ocorrências por nome no texto extraído, número RAP ou data.

        Aplica filtros opcionais combinados com AND. Usa ILIKE para buscas
        parciais case-insensitive, beneficiando índice pg_trgm GIN se existir.
        Busca por nome requer processada=True (texto disponível).

        Args:
            guarnicao_id: ID da guarnição para isolamento multi-tenant.
            nome: Trecho do nome a buscar no texto extraído do PDF ou nos nomes dos envolvidos.
            rap: Trecho do número RAP para busca parcial.
            data: Data exata do fato ocorrido.
            limit: Número máximo de resultados (padrão: 20).

        Returns:
            Lista de ocorrências ordenadas por data de criação decrescente.
        """
        query = select(Ocorrencia).where(
            Ocorrencia.guarnicao_id == guarnicao_id,
            Ocorrencia.ativo == True,  # noqa: E712
        )
        if nome:
            nome_escaped = _escape_like(nome)
            query = query.where(
                or_(
                    Ocorrencia.texto_extraido.ilike(f"%{nome_escaped}%"),
                    Ocorrencia.nomes_envolvidos.ilike(f"%{nome_escaped}%"),
                )
            )
        if rap:
            query = query.where(Ocorrencia.numero_ocorrencia.ilike(f"%{_escape_like(rap)}%"))
        if data:
            query = query.where(Ocorrencia.data_ocorrencia == data)

        query = query.order_by(Ocorrencia.criado_em.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

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
