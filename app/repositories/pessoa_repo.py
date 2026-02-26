"""Repositório especializado para Pessoa com busca fuzzy e CPF criptografado.

Estende BaseRepository com métodos de busca por nome (pg_trgm fuzzy),
CPF hash (SHA-256) e carregamento eager de relacionamentos.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.pessoa import Pessoa
from app.repositories.base import BaseRepository


class PessoaRepository(BaseRepository[Pessoa]):
    """Repositório para operações de Pessoa.

    Estende BaseRepository com busca fuzzy por nome (pg_trgm),
    busca por hash de CPF e carregamento eager de relacionamentos
    para views de detalhe.

    Attributes:
        model: Classe Pessoa.
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa repositório de Pessoa.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        super().__init__(Pessoa, db)

    async def search_by_nome_fuzzy(
        self,
        nome: str,
        guarnicao_id: int | None,
        threshold: float = 0.3,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Pessoa]:
        """Busca pessoas por nome usando pg_trgm (busca fuzzy).

        Utiliza a função similarity() do PostgreSQL para encontrar nomes
        similares, tolerando erros de digitação e variações.

        Args:
            nome: Termo de busca (nome ou parte do nome).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            threshold: Limite mínimo de similaridade (0.0 a 1.0, padrão 0.3).
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Pessoas ordenadas por similaridade decrescente.
        """
        query = select(Pessoa).where(
            Pessoa.ativo == True,  # noqa: E712
            func.similarity(Pessoa.nome, nome) > threshold,
        )
        if guarnicao_id is not None:
            query = query.where(Pessoa.guarnicao_id == guarnicao_id)

        query = query.order_by(func.similarity(Pessoa.nome, nome).desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_cpf_hash(self, cpf_hash: str, guarnicao_id: int | None) -> Pessoa | None:
        """Busca pessoa por hash SHA-256 do CPF.

        Permite busca exata por CPF sem necessidade de descriptografia,
        mantendo segurança LGPD.

        Args:
            cpf_hash: Hash SHA-256 do CPF normalizado.
            guarnicao_id: ID da guarnição para filtro multi-tenant.

        Returns:
            Pessoa encontrada ou None.
        """
        query = select(Pessoa).where(
            Pessoa.cpf_hash == cpf_hash,
            Pessoa.ativo == True,  # noqa: E712
        )
        if guarnicao_id is not None:
            query = query.where(Pessoa.guarnicao_id == guarnicao_id)

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_detail(self, id: int, guarnicao_id: int) -> Pessoa | None:
        """Obtém pessoa com todos os relacionamentos carregados (eager load).

        Carrega endereços, fotos e relacionamentos em uma única query
        para evitar N+1 queries.

        Args:
            id: Identificador da pessoa.
            guarnicao_id: ID da guarnição para filtro multi-tenant.

        Returns:
            Pessoa com relacionamentos carregados ou None.
        """
        query = (
            select(Pessoa)
            .options(
                selectinload(Pessoa.enderecos),
                selectinload(Pessoa.fotos),
                selectinload(Pessoa.relacionamentos_como_a),
                selectinload(Pessoa.relacionamentos_como_b),
            )
            .where(
                Pessoa.id == id,
                Pessoa.guarnicao_id == guarnicao_id,
                Pessoa.ativo == True,  # noqa: E712
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
