"""Repositório especializado para Veículo com busca por placa.

Estende BaseRepository com métodos de busca exata e parcial por placa,
com filtros multi-tenant e soft delete.
"""

import logging
from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import AbordagemPessoa, AbordagemVeiculo
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.models.pessoa_veiculo import PessoaVeiculo
from app.models.veiculo import Veiculo
from app.repositories.base import BaseRepository
from app.services.text_utils import cor_variantes, escape_like

logger = logging.getLogger(__name__)


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

    async def get_by_client_id(self, client_id: str) -> Veiculo | None:
        """Busca veículo por client_id para deduplicação offline.

        Args:
            client_id: ID único do cliente (gerado no frontend offline).

        Returns:
            Veículo existente com este client_id ou None.
        """
        query = select(Veiculo).where(Veiculo.client_id == client_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def search_by_placa_partial(
        self,
        placa_partial: str,
        guarnicao_id: int | None,
        skip: int = 0,
        limit: int = 20,
        bpm_id: int | None = None,
    ) -> Sequence[Veiculo]:
        """Busca veículos por placa parcial (ILIKE).

        Aplica filtro em cascata: guarnicao_id > bpm_id > global.

        Args:
            placa_partial: Parte da placa para busca parcial.
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.
            bpm_id: ID do BPM para filtro quando guarnicao_id for None.

        Returns:
            Sequência de Veículos que contêm a placa parcial.
        """
        normalized = placa_partial.upper().replace("-", "").replace(" ", "")
        # Termo que normaliza para vazio não deve virar ILIKE '%%' (busca global).
        if not normalized:
            return []
        query = select(Veiculo).where(
            Veiculo.ativo == True,  # noqa: E712
            Veiculo.placa.ilike(f"%{escape_like(normalized)}%"),
        )
        if guarnicao_id is not None:
            query = query.where(Veiculo.guarnicao_id == guarnicao_id)
        elif bpm_id is not None:
            guarnicao_ids = select(Guarnicao.id).where(
                Guarnicao.bpm_id == bpm_id,
                Guarnicao.ativo == True,  # noqa: E712
            )
            query = query.where(Veiculo.guarnicao_id.in_(guarnicao_ids))

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
        """Busca pessoas vinculadas a veículos via abordagens ou vínculo direto.

        Resolve Veiculo → AbordagemVeiculo (veiculo_id) → AbordagemPessoa
        (abordagem_id) → Pessoa para retornar todos os abordados presentes
        na mesma abordagem em que o veículo foi registrado. Deduplicação
        via DISTINCT no par (Pessoa, Veiculo).

        O caminho passa por AbordagemPessoa (não AbordagemVeiculo.pessoa_id)
        pois o campo pessoa_id em AbordagemVeiculo é opcional (nullable) e
        frequentemente NULL — o que tornava a busca inoperante.

        Além do caminho via abordagem, resolve também Pessoa → PessoaVeiculo
        → Veiculo: o vínculo direto cadastrado na ficha do abordado (Tasks
        3-6), sem nenhuma abordagem envolvida. Sem esse segundo caminho, um
        veículo vinculado só via PessoaVeiculo ficava invisível nesta busca
        — o gap que motivou este método passar a rodar as duas queries e
        combinar (union em Python) os resultados, deduplicando por par
        (pessoa.id, veiculo.id).

        Args:
            placa: Placa parcial para busca ILIKE (opcional).
            modelo: Modelo parcial para busca ILIKE (opcional).
            cor: Cor parcial para busca ILIKE (opcional).
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            skip: Número de registros a pular.
            limit: Número máximo de resultados.

        Returns:
            Lista de tuplas (Pessoa, Veiculo) sem duplicatas por par — a mesma
            pessoa pode aparecer múltiplas vezes se vinculada a veículos distintos
            que atendam o filtro.
        """

        def _montar_filtros(query: Select) -> tuple[Select, bool]:
            """Aplica os filtros de placa/modelo/cor comuns aos dois caminhos.

            Args:
                query: Select parcial (ainda sem filtros de placa/modelo/cor).

            Returns:
                Tupla (query com filtros aplicados, se algum filtro foi efetivo).
            """
            aplicou_filtro = False
            if placa:
                normalized = placa.upper().replace("-", "").replace(" ", "")
                if normalized:
                    query = query.where(Veiculo.placa.ilike(f"%{escape_like(normalized)}%"))
                    aplicou_filtro = True
            if modelo:
                modelo_clean = modelo.strip()
                if modelo_clean:
                    m = escape_like(modelo_clean)
                    query = query.where(
                        Veiculo.modelo.ilike(m)
                        | Veiculo.modelo.ilike(f"{m} %")
                        | Veiculo.modelo.ilike(f"% {m}")
                        | Veiculo.modelo.ilike(f"% {m} %")
                    )
                    aplicou_filtro = True
            if cor:
                # Flexão de gênero: "branco" também casa "branca" e vice-versa.
                clauses = [Veiculo.cor.ilike(f"%{escape_like(v)}%") for v in cor_variantes(cor)]
                if clauses:
                    query = query.where(or_(*clauses))
                    aplicou_filtro = True
            return query, aplicou_filtro

        query_abordagem = (
            select(Pessoa, Veiculo)
            .join_from(Pessoa, AbordagemPessoa, AbordagemPessoa.pessoa_id == Pessoa.id)
            .join(AbordagemVeiculo, AbordagemVeiculo.abordagem_id == AbordagemPessoa.abordagem_id)
            .join(Veiculo, Veiculo.id == AbordagemVeiculo.veiculo_id)
            .where(
                Pessoa.ativo == True,  # noqa: E712
                Veiculo.ativo == True,  # noqa: E712
                AbordagemVeiculo.ativo == True,  # noqa: E712
                AbordagemPessoa.ativo == True,  # noqa: E712
            )
        )
        query_abordagem, aplicou_filtro = _montar_filtros(query_abordagem)

        query_direto = (
            select(Pessoa, Veiculo)
            .join_from(PessoaVeiculo, Pessoa, PessoaVeiculo.pessoa_id == Pessoa.id)
            .join(Veiculo, Veiculo.id == PessoaVeiculo.veiculo_id)
            .where(
                Pessoa.ativo == True,  # noqa: E712
                Veiculo.ativo == True,  # noqa: E712
                PessoaVeiculo.ativo == True,  # noqa: E712
            )
        )
        # `_montar_filtros` aplica os mesmos placa/modelo/cor nos dois
        # caminhos — o segundo retorno de "filtro efetivo" é sempre igual
        # ao primeiro por construção, então só uma variável é mantida.
        query_direto, _ = _montar_filtros(query_direto)

        # Nenhum filtro efetivo (ex.: placa que normaliza para vazio) →
        # sem match-all, nem toca o banco.
        if not aplicou_filtro:
            return []

        if guarnicao_id is not None:
            # Pessoas são sempre globais per spec do projeto — NÃO filtrar por guarnicao_id.
            # Filtrar apenas veículos por tenant para restringir o escopo da busca.
            query_abordagem = query_abordagem.where(Veiculo.guarnicao_id == guarnicao_id)
            query_direto = query_direto.where(Veiculo.guarnicao_id == guarnicao_id)

        resultado_abordagem = (await self.db.execute(query_abordagem.distinct())).all()
        resultado_direto = (await self.db.execute(query_direto.distinct())).all()

        vistos: set[tuple[int, int]] = set()
        combinado: list[tuple] = []
        for pessoa_row, veiculo_row in [*resultado_abordagem, *resultado_direto]:
            chave = (pessoa_row.id, veiculo_row.id)
            if chave not in vistos:
                vistos.add(chave)
                combinado.append((pessoa_row, veiculo_row))

        return combinado[skip : skip + limit]

    async def get_veiculos_por_pessoa_via_abordagem(self, pessoa_id: int) -> Sequence[Veiculo]:
        """Veículos vinculados à pessoa através de abordagens.

        Resolve AbordagemPessoa (pessoa esteve na abordagem) → AbordagemVeiculo
        (veículo esteve na mesma abordagem) → Veiculo. Inclui tanto vínculos
        onde o veículo foi explicitamente atribuído a esta pessoa
        (AbordagemVeiculo.pessoa_id == pessoa_id) quanto vínculos órfãos sem
        pessoa atribuída (pessoa_id NULL), mesmo padrão usado hoje no frontend.

        Args:
            pessoa_id: ID da pessoa.

        Returns:
            Sequência de Veículos únicos vinculados via abordagem.
        """
        query = (
            select(Veiculo)
            .join(AbordagemVeiculo, AbordagemVeiculo.veiculo_id == Veiculo.id)
            .join(AbordagemPessoa, AbordagemPessoa.abordagem_id == AbordagemVeiculo.abordagem_id)
            .where(
                AbordagemPessoa.pessoa_id == pessoa_id,
                or_(AbordagemVeiculo.pessoa_id == pessoa_id, AbordagemVeiculo.pessoa_id.is_(None)),
                Veiculo.ativo == True,  # noqa: E712
                AbordagemVeiculo.ativo == True,  # noqa: E712
                AbordagemPessoa.ativo == True,  # noqa: E712
            )
            .distinct()
        )
        result = await self.db.execute(query)
        return result.scalars().all()
