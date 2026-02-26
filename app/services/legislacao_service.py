"""Serviço de domínio para Legislação.

Gerencia CRUD de artigos de legislação e busca semântica via pgvector.
Legislação é dado global (sem multi-tenancy), acessível por todas as
guarnições.
"""

import logging
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.models.legislacao import Legislacao
from app.repositories.legislacao_repo import LegislacaoRepository
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("argus")


class LegislacaoService:
    """Serviço de domínio para gerenciamento de legislação.

    Orquestra CRUD de artigos de lei e busca semântica via embeddings.
    Legislação é dado global compartilhado entre todas as guarnições.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
        repo: Repositório de legislação com busca semântica.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa serviço com repositório.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db
        self.repo = LegislacaoRepository(db)

    async def criar(self, lei: str, artigo: str, texto: str, nome: str | None = None) -> Legislacao:
        """Cria novo artigo de legislação.

        Args:
            lei: Designação da lei (ex: "CP", "Lei 11343/06").
            artigo: Número do artigo (ex: "121").
            texto: Texto integral do artigo.
            nome: Nome resumido do tipo penal (opcional).

        Returns:
            Legislação criada.
        """
        legislacao = Legislacao(
            lei=lei,
            artigo=artigo,
            nome=nome,
            texto=texto,
        )
        return await self.repo.create(legislacao)

    async def buscar_por_id(self, legislacao_id: int) -> Legislacao:
        """Busca legislação por ID.

        Args:
            legislacao_id: ID da legislação.

        Returns:
            Legislação encontrada.

        Raises:
            NaoEncontradoError: Se legislação não existe ou está inativa.
        """
        legislacao = await self.repo.get(legislacao_id)
        if legislacao is None or not legislacao.ativo:
            raise NaoEncontradoError("Legislação não encontrada")
        return legislacao

    async def listar(self, skip: int = 0, limit: int = 100) -> Sequence[Legislacao]:
        """Lista artigos de legislação com paginação.

        Args:
            skip: Registros a pular.
            limit: Máximo de registros.

        Returns:
            Sequência de legislações ativas.
        """
        return await self.repo.get_all(skip=skip, limit=limit)

    async def buscar_semantica(
        self,
        query: str,
        embedding_service: EmbeddingService,
        top_k: int = 3,
    ) -> list[dict]:
        """Busca legislação por similaridade semântica.

        Gera embedding da query e busca artigos de lei semanticamente
        similares via pgvector (cosine distance).

        Args:
            query: Texto de busca em linguagem natural.
            embedding_service: Serviço de embedding para gerar vetor.
            top_k: Número máximo de resultados.

        Returns:
            Lista de dicionários com legislação e score de similaridade.
        """
        embedding = await embedding_service.gerar_embedding_cached(query)
        results = await self.repo.search_semantic(embedding, top_k=top_k)

        return [
            {
                "legislacao": row[0],
                "similaridade": round(float(row[1]), 4),
            }
            for row in results
        ]
