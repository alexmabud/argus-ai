"""Repositório especializado para Pessoa com busca fuzzy e CPF criptografado.

Estende BaseRepository com métodos de busca por nome (pg_trgm fuzzy),
CPF hash (SHA-256) e carregamento eager de relacionamentos.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import case, func, or_, select
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

    async def search_by_nome(
        self,
        nome: str,
        guarnicao_id: int | None,
        threshold: float = 0.3,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Pessoa]:
        """Busca pessoas por nome, apelido ou similaridade, ignorando acentos e case.

        Combina busca por substring (ILIKE) no nome e apelido com busca fuzzy
        (pg_trgm similarity) para tolerar erros de digitação. Resultados são
        ordenados por relevância: match no nome > match no apelido > match fuzzy.

        Args:
            nome: Termo de busca (nome, apelido ou parte do nome).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            threshold: Limite mínimo de similaridade fuzzy (0.0 a 1.0, padrão 0.3).
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Pessoas ordenadas por relevância decrescente.
        """
        nome_clean = nome.strip()
        if not nome_clean:
            return []

        # Tokens preservam a ordem digitada: "joao silva" → ["joao", "silva"]
        # O padrão %tok1%tok2% casa nomes onde tok1 aparece ANTES de tok2,
        # independente do que há no meio ("João Carlos Silva" ✓, "Silva João" ✗).
        tokens = nome_clean.split()

        unaccent_nome = func.unaccent(func.lower(Pessoa.nome))
        unaccent_apelido = func.unaccent(func.lower(func.coalesce(Pessoa.apelido, "")))

        # Escapa %, _ e \ dos tokens: senão um % ou _ digitado pelo usuário viraria
        # curinga do LIKE (ex.: buscar "100%" casaria qualquer nome). Os '%'
        # estruturais abaixo continuam sendo curingas; o ESCAPE '\' abaixo trata
        # os literais escapados.
        def _esc(t: str) -> str:
            return t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        # Monta: '%' || unaccent(lower(tok1)) || '%' || unaccent(lower(tok2)) || '%'
        like_pattern = "%" + func.unaccent(func.lower(_esc(tokens[0]))) + "%"
        for token in tokens[1:]:
            like_pattern = like_pattern + func.unaccent(func.lower(_esc(token))) + "%"

        unaccent_full_query = func.unaccent(func.lower(nome_clean))

        match_nome = unaccent_nome.like(like_pattern, escape="\\")
        match_apelido = unaccent_apelido.like(like_pattern, escape="\\")
        match_fuzzy = func.similarity(unaccent_nome, unaccent_full_query) > threshold

        query = select(Pessoa).where(
            Pessoa.ativo == True,  # noqa: E712
            or_(match_nome, match_apelido, match_fuzzy),
        )
        if guarnicao_id is not None:
            query = query.where(Pessoa.guarnicao_id == guarnicao_id)

        # Ordena pela posição do primeiro token no nome (menor = mais relevante)
        first_token_expr = func.unaccent(func.lower(tokens[0]))
        ordem = case(
            (match_nome, func.strpos(unaccent_nome, first_token_expr)),
            (match_apelido, 5000),
            else_=9999,
        )
        query = query.order_by(ordem.asc(), Pessoa.nome.asc()).offset(skip).limit(limit)
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

    async def get_by_client_id(self, client_id: str) -> Pessoa | None:
        """Busca pessoa por client_id para deduplicação offline.

        Args:
            client_id: ID único do cliente (gerado no frontend offline).

        Returns:
            Pessoa existente com este client_id ou None.
        """
        query = select(Pessoa).where(Pessoa.client_id == client_id)
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
        return list(result.all())  # type: ignore[arg-type]

    async def search_by_localidade_ids_com_endereco(
        self,
        estado_id: int | None,
        cidade_id: int | None,
        bairro_id: int | None,
        guarnicao_id: int | None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[tuple[Pessoa, datetime]]:
        """Busca pessoas pelos ids de localidade (estado/cidade/bairro) do endereço.

        Espelha search_by_bairro_cidade_com_endereco, mas filtra pelas FKs
        estado_id/cidade_id/bairro_id do EnderecoPessoa (igualdade exata) em vez
        de texto ILIKE. Paginado no banco (OFFSET/LIMIT) — um filtro amplo (ex.:
        um estado inteiro) podia carregar milhares de pessoas em memória.

        Args:
            estado_id: ID da localidade estado (opcional).
            cidade_id: ID da localidade cidade (opcional).
            bairro_id: ID da localidade bairro (opcional).
            guarnicao_id: ID da guarnição para filtro multi-tenant (None = global).
            skip: Registros a pular (OFFSET).
            limit: Máximo de resultados (LIMIT).

        Returns:
            Lista de tuplas (Pessoa, endereco_criado_em). Uma linha por pessoa
            (o endereço mais recente que casa o filtro, criado_em DESC).
        """
        query = (
            select(Pessoa, EnderecoPessoa.criado_em)
            .join(EnderecoPessoa, EnderecoPessoa.pessoa_id == Pessoa.id)
            .where(
                Pessoa.ativo == True,  # noqa: E712
                EnderecoPessoa.ativo == True,  # noqa: E712
            )
        )
        if estado_id is not None:
            query = query.where(EnderecoPessoa.estado_id == estado_id)
        if cidade_id is not None:
            query = query.where(EnderecoPessoa.cidade_id == cidade_id)
        if bairro_id is not None:
            query = query.where(EnderecoPessoa.bairro_id == bairro_id)
        if guarnicao_id is not None:
            query = query.where(Pessoa.guarnicao_id == guarnicao_id)

        query = (
            query.order_by(Pessoa.id, EnderecoPessoa.criado_em.desc())
            .distinct(Pessoa.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.all())  # type: ignore[arg-type]

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

    async def get_detail(self, id: int, guarnicao_id: int | None) -> Pessoa | None:
        """Obtém pessoa com todos os relacionamentos carregados (eager load).

        Carrega endereços, fotos e relacionamentos em uma única query
        para evitar N+1 queries.

        Args:
            id: Identificador da pessoa.
            guarnicao_id: ID da guarnição para filtro multi-tenant, ou None para
                acesso global (quando isolamento_abordagens está desativado).

        Returns:
            Pessoa com relacionamentos carregados ou None.
        """
        conditions = [Pessoa.id == id, Pessoa.ativo == True]  # noqa: E712
        if guarnicao_id is not None:
            conditions.append(Pessoa.guarnicao_id == guarnicao_id)

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
            .where(*conditions)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
