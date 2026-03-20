"""Repositório especializado para Pessoa com busca fuzzy e CPF criptografado.

Estende BaseRepository com métodos de busca por nome (pg_trgm fuzzy),
CPF hash (SHA-256) e carregamento eager de relacionamentos.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.endereco import EnderecoPessoa
from app.models.pessoa import Pessoa
from app.models.relacionamento import RelacionamentoPessoa
from app.repositories.base import BaseRepository
from app.services.text_utils import escape_like


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

    async def search_by_bairro_cidade(
        self,
        bairro: str | None,
        cidade: str | None,
        estado: str | None,
        guarnicao_id: int | None,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Pessoa]:
        """Busca pessoas pelo bairro, cidade ou estado dos endereços cadastrados.

        Realiza JOIN com enderecos_pessoa filtrando por bairro, cidade e/ou estado
        via ILIKE (busca parcial case-insensitive).

        Args:
            bairro: Bairro para filtrar (parcial, opcional).
            cidade: Cidade para filtrar (parcial, opcional).
            estado: Sigla UF para filtrar (parcial, opcional).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Pessoas com endereço no bairro/cidade/estado informados.
        """
        query = (
            select(Pessoa)
            .join(EnderecoPessoa, EnderecoPessoa.pessoa_id == Pessoa.id)
            .where(
                Pessoa.ativo == True,  # noqa: E712
                EnderecoPessoa.ativo == True,  # noqa: E712
            )
        )
        if bairro:
            query = query.where(EnderecoPessoa.bairro.ilike(f"%{escape_like(bairro)}%"))
        if cidade:
            query = query.where(EnderecoPessoa.cidade.ilike(f"%{escape_like(cidade)}%"))
        if estado:
            query = query.where(EnderecoPessoa.estado.ilike(f"%{escape_like(estado)}%"))
        if guarnicao_id is not None:
            query = query.where(Pessoa.guarnicao_id == guarnicao_id)

        query = query.distinct().offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_bairro_cidade_com_endereco(
        self,
        bairro: str | None,
        cidade: str | None,
        estado: str | None,
        guarnicao_id: int | None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[tuple[Pessoa, datetime]]:
        """Busca pessoas por bairro/cidade/estado retornando tuplas com criado_em do endereço.

        Idêntico a search_by_bairro_cidade, mas retorna também o criado_em
        do EnderecoPessoa que gerou o match, para exibição no frontend.

        Args:
            bairro: Bairro para filtrar (parcial, opcional).
            cidade: Cidade para filtrar (parcial, opcional).
            estado: Sigla UF para filtrar (parcial, opcional).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Lista de tuplas (Pessoa, endereco_criado_em: datetime). Quando a pessoa
            tem múltiplos endereços no bairro/cidade/estado filtrado, retorna o
            endereço cadastrado mais recentemente (criado_em DESC).
        """
        query = (
            select(Pessoa, EnderecoPessoa.criado_em)
            .join(EnderecoPessoa, EnderecoPessoa.pessoa_id == Pessoa.id)
            .where(
                Pessoa.ativo == True,  # noqa: E712
                EnderecoPessoa.ativo == True,  # noqa: E712
            )
        )
        if bairro:
            query = query.where(EnderecoPessoa.bairro.ilike(f"%{escape_like(bairro)}%"))
        if cidade:
            query = query.where(EnderecoPessoa.cidade.ilike(f"%{escape_like(cidade)}%"))
        if estado:
            query = query.where(EnderecoPessoa.estado.ilike(f"%{escape_like(estado)}%"))
        if guarnicao_id is not None:
            query = query.where(Pessoa.guarnicao_id == guarnicao_id)

        query = (
            query.order_by(Pessoa.id, EnderecoPessoa.criado_em.desc())
            .distinct(Pessoa.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.all())

    async def get_localidades(self, guarnicao_id: int | None) -> dict:
        """Retorna valores distintos de bairro, cidade e estado cadastrados.

        Utilizado para popular autocomplete/datalist no frontend. Filtra
        registros ativos e com valor não nulo, ordenando alfabeticamente.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.

        Returns:
            Dicionário com chaves "bairros", "cidades" e "estados",
            cada uma contendo lista de strings distintas ordenadas.
        """
        base_filter = [EnderecoPessoa.ativo == True]  # noqa: E712

        q_bairros = (
            select(func.distinct(EnderecoPessoa.bairro))
            .where(*base_filter, EnderecoPessoa.bairro.isnot(None))
            .order_by(EnderecoPessoa.bairro)
        )
        q_cidades = (
            select(func.distinct(EnderecoPessoa.cidade))
            .where(*base_filter, EnderecoPessoa.cidade.isnot(None))
            .order_by(EnderecoPessoa.cidade)
        )
        q_estados = (
            select(func.distinct(EnderecoPessoa.estado))
            .where(*base_filter, EnderecoPessoa.estado.isnot(None))
            .order_by(EnderecoPessoa.estado)
        )

        if guarnicao_id is not None:
            join_clause = EnderecoPessoa.pessoa_id == Pessoa.id
            tenant_filter = Pessoa.guarnicao_id == guarnicao_id
            q_bairros = q_bairros.join(Pessoa, join_clause).where(tenant_filter)
            q_cidades = q_cidades.join(Pessoa, join_clause).where(tenant_filter)
            q_estados = q_estados.join(Pessoa, join_clause).where(tenant_filter)

        bairros = list((await self.db.execute(q_bairros)).scalars().all())
        cidades = list((await self.db.execute(q_cidades)).scalars().all())
        estados = list((await self.db.execute(q_estados)).scalars().all())

        return {"bairros": bairros, "cidades": cidades, "estados": estados}

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
                selectinload(Pessoa.relacionamentos_como_a).selectinload(
                    RelacionamentoPessoa.pessoa_b
                ),
                selectinload(Pessoa.relacionamentos_como_b).selectinload(
                    RelacionamentoPessoa.pessoa_a
                ),
            )
            .where(
                Pessoa.id == id,
                Pessoa.guarnicao_id == guarnicao_id,
                Pessoa.ativo == True,  # noqa: E712
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
