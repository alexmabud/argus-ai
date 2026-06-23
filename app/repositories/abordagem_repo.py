"""Repositório especializado para Abordagem com PostGIS e eager loading.

Estende BaseRepository com busca por raio geográfico (ST_DWithin),
carregamento eager de relacionamentos e deduplicação por client_id.
"""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import and_, cast, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.types import Date

from app.models.abordagem import (
    Abordagem,
    AbordagemPessoa,
    AbordagemVeiculo,
)
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.veiculo import Veiculo
from app.repositories.base import BaseRepository
from app.services.text_utils import cor_variantes, escape_like


def _cor_match(q: str):
    """Casa a cor do veículo aceitando flexão de gênero (masculino/feminino).

    Ex.: "branco" também encontra "branca"; "vermelha" também encontra
    "vermelho". Cores sem flexão (azul, cinza) casam apenas o próprio termo.

    Args:
        q: Termo de busca livre informado pelo usuário.

    Returns:
        Expressão booleana SQLAlchemy (OR de ILIKEs) para o filtro de cor;
        falsa quando o termo é vazio após strip.
    """
    clauses = [Veiculo.cor.ilike(f"%{escape_like(v)}%") for v in cor_variantes(q)]
    if not clauses:
        return false()
    return or_(*clauses)


def _modelo_word_boundary(q: str):
    """Casa o termo como palavra completa no modelo do veículo.

    Evita que "gol" retorne "golf" (problema do ILIKE substring). Usa quatro
    condições OR — termo exato, no início, no fim ou no meio de modelos
    compostos — espelhando a busca da consulta (veiculo_repo).

    Args:
        q: Termo de busca livre informado pelo usuário.

    Returns:
        Expressão booleana SQLAlchemy para o filtro de modelo; falsa quando
        o termo é vazio após strip.
    """
    m = escape_like(q.strip())
    if not m:
        return false()
    return (
        Veiculo.modelo.ilike(m)
        | Veiculo.modelo.ilike(f"{m} %")
        | Veiculo.modelo.ilike(f"% {m}")
        | Veiculo.modelo.ilike(f"% {m} %")
    )


def _texto_match(q: str):
    """Casa a busca textual livre por palavras (AND entre palavras).

    Quebra o termo em palavras e exige que CADA palavra case em ALGUM dos campos
    (nome, placa, modelo com word-boundary, cor com flexão de gênero, tipo,
    endereço). Assim "gol branca" exige modelo~gol E cor~branca (encontrando
    "Branco"), enquanto "branca" sozinho casa todos os veículos brancos. Cada
    palavra é escapada para LIKE para neutralizar wildcards do usuário.

    Args:
        q: Termo de busca livre informado pelo usuário.

    Returns:
        Expressão booleana SQLAlchemy (AND de ORs por palavra); falsa quando o
        termo é vazio após split.
    """
    palavras = q.split()
    if not palavras:
        return false()
    clausulas = []
    for palavra in palavras:
        termo = f"%{escape_like(palavra)}%"
        clausulas.append(
            or_(
                Pessoa.nome.ilike(termo),
                Veiculo.placa.ilike(termo),
                _modelo_word_boundary(palavra),
                _cor_match(palavra),
                Veiculo.tipo.ilike(termo),
                Abordagem.endereco_texto.ilike(termo),
            )
        )
    return and_(*clausulas)


class AbordagemRepository(BaseRepository[Abordagem]):
    """Repositório para operações de Abordagem.

    Estende BaseRepository com busca geoespacial por raio (PostGIS),
    carregamento eager de pessoas/veículos/fotos/ocorrências,
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

        Carrega pessoas, veículos, fotos e ocorrências
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

    async def list_by_data(
        self,
        guarnicao_id: int,
        data: date,
    ) -> Sequence[Abordagem]:
        """Lista abordagens de uma guarnição em uma data específica.

        Filtra pela data de data_hora convertida para o fuso BRT (America/Sao_Paulo)
        antes do cast para Date, evitando que abordagens após 21h BRT apareçam
        no dia seguinte (UTC). Aplica eager loading completo de relacionamentos.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            data: Data de referência (YYYY-MM-DD).

        Returns:
            Sequência de Abordagens do dia ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.ativo == True,  # noqa: E712
                cast(func.timezone("America/Sao_Paulo", Abordagem.data_hora), Date) == data,
            )
            .order_by(Abordagem.data_hora.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_by_usuario(
        self,
        usuario_id: int,
        guarnicao_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[Abordagem]:
        """Lista abordagens de um usuário específico com eager loading.

        Filtra por usuario_id (minhas abordagens) com tenant guard por
        guarnicao_id. Carrega pessoas, veículos e ocorrências via selectin.

        Args:
            usuario_id: ID do oficial autenticado.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Registros a pular (paginação).
            limit: Número máximo de resultados.

        Returns:
            Sequência de Abordagens com relacionamentos carregados.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(
                Abordagem.usuario_id == usuario_id,
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
                func.ST_DWithin(
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

    async def list_by_pessoa(
        self,
        pessoa_id: int,
        guarnicao_id: int | None,
        limit: int = 50,
    ) -> Sequence[Abordagem]:
        """Lista abordagens de uma pessoa com relacionamentos carregados.

        Quando guarnicao_id é None, retorna abordagens de todas as guarnições —
        comportamento correto para a ficha individual da pessoa, onde o isolamento
        de guarnição não se aplica.

        Args:
            pessoa_id: ID da pessoa.
            guarnicao_id: ID da guarnição para filtro, ou None para todas.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Abordagens com pessoas e veículos carregados.
        """
        conditions = [
            AbordagemPessoa.pessoa_id == pessoa_id,
            Abordagem.ativo == True,  # noqa: E712
        ]
        if guarnicao_id is not None:
            conditions.append(Abordagem.guarnicao_id == guarnicao_id)

        query = (
            select(Abordagem)
            .join(AbordagemPessoa, AbordagemPessoa.abordagem_id == Abordagem.id)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
            )
            .where(*conditions)
            .order_by(Abordagem.data_hora.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().unique().all()

    async def search_by_texto(
        self,
        q: str,
        guarnicao_id: int,
        limit: int = 100,
    ) -> Sequence[Abordagem]:
        """Busca abordagens por texto em nome, placa, veículo ou endereço.

        Cobre nome de pessoa, placa, atributos do veículo (modelo, cor, tipo)
        e endereço. Faz outer join com Pessoa e Veiculo para cobrir os campos,
        retornando abordagens de qualquer data que contenham o termo.

        Args:
            q: Termo de busca (mínimo 1 caractere).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            limit: Número máximo de resultados (padrão 100).

        Returns:
            Sequência de Abordagens ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .outerjoin(
                AbordagemPessoa,
                (AbordagemPessoa.abordagem_id == Abordagem.id) & (AbordagemPessoa.ativo == True),  # noqa: E712
            )
            .outerjoin(Pessoa, Pessoa.id == AbordagemPessoa.pessoa_id)
            .outerjoin(
                AbordagemVeiculo,
                (AbordagemVeiculo.abordagem_id == Abordagem.id) & (AbordagemVeiculo.ativo == True),  # noqa: E712
            )
            .outerjoin(Veiculo, Veiculo.id == AbordagemVeiculo.veiculo_id)
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.ativo == True,  # noqa: E712
                _texto_match(q),
            )
            .distinct()
            .order_by(Abordagem.data_hora.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().unique().all()

    async def get_detail_global(self, id: int) -> Abordagem | None:
        """Busca abordagem por ID em todo o sistema (sem filtro de guarnição).

        Usado quando o usuário pertence a equipe sem isolamento_abordagens.

        Args:
            id: ID da abordagem.

        Returns:
            Abordagem com relacionamentos ou None.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(Abordagem.id == id, Abordagem.ativo == True)  # noqa: E712
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_global(self, skip: int = 0, limit: int = 20) -> Sequence[Abordagem]:
        """Lista todas as abordagens ativas do sistema sem filtro de guarnição.

        Args:
            skip: Registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Abordagens ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .where(Abordagem.ativo == True)  # noqa: E712
            .order_by(Abordagem.data_hora.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_by_data_global(self, data: date) -> Sequence[Abordagem]:
        """Lista abordagens de todas as equipes em uma data específica.

        Args:
            data: Data de referência (YYYY-MM-DD).

        Returns:
            Sequência de Abordagens do dia ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(
                Abordagem.ativo == True,  # noqa: E712
                cast(func.timezone("America/Sao_Paulo", Abordagem.data_hora), Date) == data,
            )
            .order_by(Abordagem.data_hora.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_texto_global(self, q: str, limit: int = 100) -> Sequence[Abordagem]:
        """Busca abordagens por texto em todo o sistema (sem filtro de guarnição).

        Args:
            q: Termo de busca.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Abordagens ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .outerjoin(
                AbordagemPessoa,
                (AbordagemPessoa.abordagem_id == Abordagem.id) & (AbordagemPessoa.ativo == True),  # noqa: E712
            )
            .outerjoin(Pessoa, Pessoa.id == AbordagemPessoa.pessoa_id)
            .outerjoin(
                AbordagemVeiculo,
                (AbordagemVeiculo.abordagem_id == Abordagem.id) & (AbordagemVeiculo.ativo == True),  # noqa: E712
            )
            .outerjoin(Veiculo, Veiculo.id == AbordagemVeiculo.veiculo_id)
            .where(
                Abordagem.ativo == True,  # noqa: E712
                _texto_match(q),
            )
            .distinct()
            .order_by(Abordagem.data_hora.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().unique().all()

    async def list_by_bpm(self, bpm_id: int, skip: int = 0, limit: int = 20) -> Sequence[Abordagem]:
        """Lista abordagens de todas as equipes de um BPM.

        Filtra via JOIN em guarnicoes.bpm_id. Retorna apenas abordagens ativas,
        ordenadas por data_hora decrescente.

        Args:
            bpm_id: ID do BPM para filtro.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Abordagens do BPM ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .join(Guarnicao, Guarnicao.id == Abordagem.guarnicao_id)
            .where(
                Guarnicao.bpm_id == bpm_id,
                Guarnicao.ativo == True,  # noqa: E712
                Abordagem.ativo == True,  # noqa: E712
            )
            .order_by(Abordagem.data_hora.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_by_data_by_bpm(self, bpm_id: int, data: date) -> Sequence[Abordagem]:
        """Lista abordagens de todas as equipes de um BPM em uma data específica.

        Filtra pela data em fuso BRT (America/Sao_Paulo) via JOIN em guarnicoes.bpm_id.
        Carrega relacionamentos via selectin (pessoas, veículos, fotos, ocorrências).

        Args:
            bpm_id: ID do BPM para filtro.
            data: Data de referência (YYYY-MM-DD).

        Returns:
            Sequência de Abordagens do dia no BPM ordenadas por data_hora decrescente.
        """
        query = (
            select(Abordagem)
            .join(Guarnicao, Guarnicao.id == Abordagem.guarnicao_id)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(
                Guarnicao.bpm_id == bpm_id,
                Guarnicao.ativo == True,  # noqa: E712
                Abordagem.ativo == True,  # noqa: E712
                cast(func.timezone("America/Sao_Paulo", Abordagem.data_hora), Date) == data,
            )
            .order_by(Abordagem.data_hora.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_texto_by_bpm(
        self, bpm_id: int, q: str, limit: int = 100
    ) -> Sequence[Abordagem]:
        """Busca abordagens por texto dentro de um BPM.

        Pesquisa por nome, placa, veículo (modelo/cor/tipo) ou endereço.
        Filtra por bpm_id via subquery para evitar conflito com JOINs de
        pessoa e veículo.

        Args:
            bpm_id: ID do BPM para filtro.
            q: Termo de busca.
            limit: Número máximo de resultados.

        Returns:
            Sequência de Abordagens com correspondência no BPM.
        """
        guarnicao_ids_bpm = select(Guarnicao.id).where(
            Guarnicao.bpm_id == bpm_id,
            Guarnicao.ativo == True,  # noqa: E712
        )
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .outerjoin(
                AbordagemPessoa,
                (AbordagemPessoa.abordagem_id == Abordagem.id) & (AbordagemPessoa.ativo == True),  # noqa: E712
            )
            .outerjoin(Pessoa, Pessoa.id == AbordagemPessoa.pessoa_id)
            .outerjoin(
                AbordagemVeiculo,
                (AbordagemVeiculo.abordagem_id == Abordagem.id) & (AbordagemVeiculo.ativo == True),  # noqa: E712
            )
            .outerjoin(Veiculo, Veiculo.id == AbordagemVeiculo.veiculo_id)
            .where(
                Abordagem.ativo == True,  # noqa: E712
                Abordagem.guarnicao_id.in_(guarnicao_ids_bpm),
                _texto_match(q),
            )
            .distinct()
            .order_by(Abordagem.data_hora.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().unique().all()

    async def get_detail_by_bpm(self, abordagem_id: int, bpm_id: int) -> Abordagem | None:
        """Busca abordagem por ID dentro de um BPM com eager loading.

        Verifica se a abordagem pertence a uma equipe do BPM antes de retornar.

        Args:
            abordagem_id: ID da abordagem.
            bpm_id: ID do BPM para validação de acesso.

        Returns:
            Abordagem com relacionamentos carregados, ou None se não pertence ao BPM.
        """
        guarnicao_ids_bpm = select(Guarnicao.id).where(
            Guarnicao.bpm_id == bpm_id,
            Guarnicao.ativo == True,  # noqa: E712
        )
        query = (
            select(Abordagem)
            .options(
                selectinload(Abordagem.pessoas).selectinload(AbordagemPessoa.pessoa),
                selectinload(Abordagem.veiculos).selectinload(AbordagemVeiculo.veiculo),
                selectinload(Abordagem.fotos),
                selectinload(Abordagem.ocorrencias),
            )
            .where(
                Abordagem.id == abordagem_id,
                Abordagem.ativo == True,  # noqa: E712
                Abordagem.guarnicao_id.in_(guarnicao_ids_bpm),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

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
