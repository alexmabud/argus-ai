"""Repositório especializado para Veículo com busca por placa.

Estende BaseRepository com métodos de busca exata e parcial por placa,
com filtros multi-tenant e soft delete.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import AbordagemPessoa, AbordagemVeiculo
from app.models.pessoa import Pessoa
from app.models.veiculo import Veiculo
from app.repositories.base import BaseRepository


class VeiculoRepository(BaseRepository[Veiculo]):
    """Repositório para operações de Veículo.

    Estende BaseRepository com busca por placa (exata e parcial)
    e verificação de unicidade.

    Attributes:
        model: Classe Veiculo.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório de Veículo.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(Veiculo, db)

    async def get_by_placa(self, placa: str) -> Veiculo | None:
        """Busca veículo por placa exata.

        Args:
            placa: Placa veicular normalizada (uppercase, sem traços).

        Returns:
            Veículo encontrado ou None.
        """
        query = select(Veiculo).where(
            Veiculo.placa == placa.upper().replace("-", "").replace(" ", ""),
            Veiculo.ativo == True,  # noqa: E712
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search_by_placa_partial(
        self,
        placa_partial: str,
        guarnicao_id: int | None,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Veiculo]:
        """Busca veículos por placa parcial (ILIKE).

        Args:
            placa_partial: Parte da placa para busca parcial.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Veículos que contêm a placa parcial.
        """
        normalized = placa_partial.upper().replace("-", "").replace(" ", "")
        query = select(Veiculo).where(
            Veiculo.ativo == True,  # noqa: E712
            Veiculo.placa.ilike(f"%{normalized}%"),
        )
        if guarnicao_id is not None:
            query = query.where(Veiculo.guarnicao_id == guarnicao_id)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_localidades(self, guarnicao_id: int | None) -> dict:
        """Retorna valores distintos de modelo e cor cadastrados.

        Utilizado pelo frontend para popular datalists de autocomplete nos
        campos de modelo e cor do formulário de veículo. Filtra por guarnição.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant (None = sem filtro).

        Returns:
            Dicionário com "modelos" e "cores" — listas de strings distintas
            ordenadas alfabeticamente.
        """
        q_modelos = select(func.distinct(Veiculo.modelo)).where(
            Veiculo.ativo == True,  # noqa: E712
            Veiculo.modelo.isnot(None),
        )
        q_cores = select(func.distinct(Veiculo.cor)).where(
            Veiculo.ativo == True,  # noqa: E712
            Veiculo.cor.isnot(None),
        )

        if guarnicao_id is not None:
            q_modelos = q_modelos.where(Veiculo.guarnicao_id == guarnicao_id)
            q_cores = q_cores.where(Veiculo.guarnicao_id == guarnicao_id)

        q_modelos = q_modelos.order_by(Veiculo.modelo)
        q_cores = q_cores.order_by(Veiculo.cor)

        res_modelos = await self.db.execute(q_modelos)
        res_cores = await self.db.execute(q_cores)

        return {
            "modelos": [r[0] for r in res_modelos.all() if r[0]],
            "cores": [r[0] for r in res_cores.all() if r[0]],
        }

    async def get_pessoas_por_veiculo(
        self,
        placa: str | None,
        modelo: str | None,
        cor: str | None,
        guarnicao_id: int | None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[tuple]:
        """Busca pessoas vinculadas a veículos via abordagens.

        Resolve a cadeia Veiculo → AbordagemVeiculo → AbordagemPessoa → Pessoa
        para encontrar todos os abordados que tiveram relação com o veículo
        buscado. Deduplicação é feita via DISTINCT na query.

        Args:
            placa: Placa parcial para busca ILIKE (opcional).
            modelo: Modelo parcial para busca ILIKE (opcional).
            cor: Cor parcial para busca ILIKE (opcional).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Lista de tuplas (Pessoa, Veiculo) sem duplicatas.
        """
        query = (
            select(Pessoa, Veiculo)
            .join(AbordagemPessoa, AbordagemPessoa.pessoa_id == Pessoa.id)
            .join(AbordagemVeiculo, AbordagemVeiculo.abordagem_id == AbordagemPessoa.abordagem_id)
            .join(Veiculo, Veiculo.id == AbordagemVeiculo.veiculo_id)
            .where(
                Pessoa.ativo == True,  # noqa: E712
                Veiculo.ativo == True,  # noqa: E712
            )
        )

        if placa:
            normalized = placa.upper().replace("-", "").replace(" ", "")
            query = query.where(Veiculo.placa.ilike(f"%{normalized}%"))
        if modelo:
            query = query.where(Veiculo.modelo.ilike(f"%{modelo}%"))
        if cor:
            query = query.where(Veiculo.cor.ilike(f"%{cor}%"))
        if guarnicao_id is not None:
            query = query.where(Pessoa.guarnicao_id == guarnicao_id)

        query = query.distinct().offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.all())
