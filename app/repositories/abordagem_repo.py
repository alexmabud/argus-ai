"""Repositório especializado para Abordagem com PostGIS e eager loading.

Estende BaseRepository com busca por raio geográfico (ST_DWithin),
carregamento eager de relacionamentos e deduplicação por client_id.
"""

from collections.abc import Sequence

from geoalchemy2 import func as geo_func
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.abordagem import (
    Abordagem,
    AbordagemPassagem,
    AbordagemPessoa,
    AbordagemVeiculo,
)
from app.repositories.base import BaseRepository


class AbordagemRepository(BaseRepository[Abordagem]):
    """Repositório para operações de Abordagem.

    Estende BaseRepository com busca geoespacial por raio (PostGIS),
    carregamento eager de pessoas/veículos/fotos/passagens/ocorrências,
    e suporte a deduplicação offline via client_id.

    Attributes:
        model: Classe Abordagem.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório de Abordagem.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(Abordagem, db)

    async def get_detail(self, id: int, guarnicao_id: int) -> Abordagem | None:
        """Obtém abordagem com todos os relacionamentos carregados.

        Carrega pessoas, veículos, fotos, passagens e ocorrências
        em uma única query (eager load).

        Args:
            id: Identificador da abordagem.
            guarnicao_id: ID da guarnição para filtro multi-tenant.

        Returns:
            Abordagem com relacionamentos carregados ou None.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.passagens).selectinload(AbordagemPassagem.passagem),
                selectinload(Abordagem.ocorrencias),
            )
            .where(
                Abordagem.id == id,
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.ativo == True,  # noqa: E712
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_guarnicao(
        self,
        guarnicao_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Abordagem]:
        """Lista abordagens de uma guarnição ordenadas por data/hora.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Abordagens ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.ativo == True,  # noqa: E712
            )
            .order_by(Abordagem.data_hora.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_radius(
        self,
        lat: float,
        lon: float,
        raio_metros: int,
        guarnicao_id: int,
        limit: int = 50,
    ) -> Sequence[Abordagem]:
        """Busca abordagens por raio geográfico usando PostGIS ST_DWithin.

        Args:
            lat: Latitude do ponto central.
            lon: Longitude do ponto central.
            raio_metros: Raio de busca em metros.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            limit: Número máximo de resultados (padrão 50).

        Returns:
            Sequência de Abordagens dentro do raio, ordenadas por data_hora.
        """
        point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
        query = (
            select(Abordagem)
            .where(
                Abordagem.ativo == True,  # noqa: E712
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.localizacao.isnot(None),
                geo_func.ST_DWithin(
                    Abordagem.localizacao,
                    point,
                    raio_metros,
                ),
            )
            .order_by(Abordagem.data_hora.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_client_id(self, client_id: str) -> Abordagem | None:
        """Busca abordagem por client_id para deduplicação offline.

        Args:
            client_id: ID único do cliente (gerado no frontend offline).

        Returns:
            Abordagem existente com este client_id ou None.
        """
        query = select(Abordagem).where(Abordagem.client_id == client_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
