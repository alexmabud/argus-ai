"""Serviço de analytics operacional.

Fornece métricas agregadas para o dashboard: resumo por período (hoje, mês, total),
séries temporais diária e mensal, suporte ao calendário (dias com abordagem e
pessoas do dia), mapa de calor, distribuição horária e pessoas recorrentes.
Respeita multi-tenancy (guarnicao_id) e soft delete em todas as queries.
Quando guarnicao_id é None, as queries são globais (todas as equipes).
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import cast, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date as DateType

from app.models.abordagem import Abordagem, AbordagemPessoa
from app.models.guarnicao import Guarnicao
from app.models.pessoa import Pessoa
from app.services.pessoa_service import PessoaService
from app.services.storage_service import normalize_storage_url

BRT = ZoneInfo("America/Sao_Paulo")


class AnalyticsService:
    """Serviço de métricas analíticas da guarnição.

    Gera dados agregados para visualização no dashboard:
    resumo operacional, heatmap geográfico, picos horários,
    pessoas mais abordadas.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço de analytics.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db

    def _filtro_base(
        self,
        guarnicao_id: int | None,
        bpm_id: int | None = None,
    ) -> list:
        """Retorna condições base de filtro para queries de analytics.

        Prioridade: guarnicao_id > bpm_id > global (sem filtro de escopo).

        Args:
            guarnicao_id: ID da guarnição para filtro por equipe.
            bpm_id: ID do BPM para filtro por BPM (subquery IN).

        Returns:
            Lista de condições SQLAlchemy para uso em .where(*conditions).
        """
        conditions: list = [Abordagem.ativo == True]  # noqa: E712
        if guarnicao_id is not None:
            conditions.append(Abordagem.guarnicao_id == guarnicao_id)
        elif bpm_id is not None:
            guarnicao_ids = select(Guarnicao.id).where(
                Guarnicao.bpm_id == bpm_id,
                Guarnicao.ativo == True,  # noqa: E712
            )
            conditions.append(Abordagem.guarnicao_id.in_(guarnicao_ids))
        return conditions

    async def resumo(
        self, guarnicao_id: int | None, dias: int = 30, bpm_id: int | None = None
    ) -> dict:
        """Retorna resumo operacional do período.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            dias: Número de dias do período (padrão 30).

        Returns:
            Dicionário com periodo_dias, total_abordagens,
            total_pessoas_distintas e media_abordagens_dia.
        """
        desde = datetime.now(UTC) - timedelta(days=dias)

        base = self._filtro_base(guarnicao_id, bpm_id)
        base.append(Abordagem.data_hora >= desde)

        # Total abordagens
        total_q = select(func.count(Abordagem.id)).where(*base)
        total = (await self.db.execute(total_q)).scalar() or 0

        # Pessoas distintas
        pessoas_q = (
            select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
            .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(*base)
        )
        pessoas = (await self.db.execute(pessoas_q)).scalar() or 0

        return {
            "periodo_dias": dias,
            "total_abordagens": total,
            "total_pessoas_distintas": pessoas,
            "media_abordagens_dia": round(total / max(dias, 1), 1),
        }

    async def mapa_calor(
        self, guarnicao_id: int | None, dias: int = 30, bpm_id: int | None = None
    ) -> list[dict]:
        """Retorna pontos geográficos para mapa de calor.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            dias: Número de dias do período (padrão 30).

        Returns:
            Lista de dicionários com lat e lon.
        """
        desde = datetime.now(UTC) - timedelta(days=dias)

        base = self._filtro_base(guarnicao_id, bpm_id)
        base += [
            Abordagem.data_hora >= desde,
            Abordagem.latitude.isnot(None),
            Abordagem.longitude.isnot(None),
        ]

        query = select(Abordagem.latitude, Abordagem.longitude).where(*base)
        result = await self.db.execute(query)
        return [{"lat": float(row[0]), "lon": float(row[1])} for row in result.all()]

    async def horarios_pico(
        self, guarnicao_id: int | None, dias: int = 30, bpm_id: int | None = None
    ) -> list[dict]:
        """Retorna distribuição horária das abordagens.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            dias: Número de dias do período (padrão 30).

        Returns:
            Lista de dicionários com hora (0-23) e total.
        """
        desde = datetime.now(UTC) - timedelta(days=dias)

        hora = extract("hour", func.timezone("America/Sao_Paulo", Abordagem.data_hora)).label(
            "hora"
        )

        base = self._filtro_base(guarnicao_id, bpm_id)
        base.append(Abordagem.data_hora >= desde)

        query = (
            select(hora, func.count(Abordagem.id).label("total"))
            .where(*base)
            .group_by(hora)
            .order_by(hora)
        )
        result = await self.db.execute(query)
        return [{"hora": int(row[0]), "total": int(row[1])} for row in result.all()]

    async def pessoas_recorrentes(
        self, guarnicao_id: int | None, limit: int = 20, bpm_id: int | None = None
    ) -> list[dict]:
        """Retorna pessoas mais abordadas.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            limit: Número máximo de resultados (padrão 20, máximo 100).

        Returns:
            Lista de dicionários com id, nome, apelido, total_abordagens,
            ultima_abordagem, cpf (mascarado, achado #16/2026-07-13) e foto_url.
        """
        limit = min(limit, 100)

        base = self._filtro_base(guarnicao_id, bpm_id)
        base.append(Pessoa.ativo)

        query = (
            select(
                Pessoa.id,
                Pessoa.nome,
                Pessoa.apelido,
                func.count(AbordagemPessoa.abordagem_id).label("total"),
                func.max(Abordagem.data_hora).label("ultima"),
                Pessoa.cpf_encrypted,
                Pessoa.foto_principal_url,
            )
            .join(AbordagemPessoa, Pessoa.id == AbordagemPessoa.pessoa_id)
            .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(*base)
            .group_by(
                Pessoa.id,
                Pessoa.nome,
                Pessoa.apelido,
                Pessoa.cpf_encrypted,
                Pessoa.foto_principal_url,
            )
            .order_by(func.count(AbordagemPessoa.abordagem_id).desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        rows = result.all()

        def _build_results() -> list[dict]:
            return [
                {
                    "id": row[0],
                    "nome": row[1],
                    "apelido": row[2],
                    "total_abordagens": int(row[3]),
                    "ultima_abordagem": row[4].isoformat() if row[4] else None,
                    "cpf": PessoaService.mask_cpf_encrypted(row[5], context_id=row[0]),
                    "foto_url": normalize_storage_url(row[6]),
                }
                for row in rows
            ]

        return await asyncio.to_thread(_build_results)

    async def resumo_hoje(self, guarnicao_id: int | None, bpm_id: int | None = None) -> dict:
        """Retorna total de abordagens e pessoas abordadas hoje.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).

        Returns:
            Dicionário com abordagens e pessoas do dia atual.
        """
        hoje = datetime.now(BRT).date()
        inicio = datetime(hoje.year, hoje.month, hoje.day, tzinfo=BRT)
        fim = inicio + timedelta(days=1)

        base = self._filtro_base(guarnicao_id, bpm_id)
        base += [Abordagem.data_hora >= inicio, Abordagem.data_hora < fim]

        total_q = select(func.count(Abordagem.id)).where(*base)
        total = (await self.db.execute(total_q)).scalar() or 0

        pessoas_q = (
            select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
            .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(*base)
        )
        pessoas = (await self.db.execute(pessoas_q)).scalar() or 0

        return {"abordagens": total, "pessoas": pessoas}

    async def resumo_mes(self, guarnicao_id: int | None, bpm_id: int | None = None) -> dict:
        """Retorna total de abordagens e pessoas abordadas no mês atual.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).

        Returns:
            Dicionário com abordagens e pessoas do mês corrente.
        """
        agora = datetime.now(BRT)
        inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if agora.month == 12:
            fim = inicio.replace(year=agora.year + 1, month=1)
        else:
            fim = inicio.replace(month=agora.month + 1)

        base = self._filtro_base(guarnicao_id, bpm_id)
        base += [Abordagem.data_hora >= inicio, Abordagem.data_hora < fim]

        total_q = select(func.count(Abordagem.id)).where(*base)
        total = (await self.db.execute(total_q)).scalar() or 0

        pessoas_q = (
            select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
            .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(*base)
        )
        pessoas = (await self.db.execute(pessoas_q)).scalar() or 0

        return {"abordagens": total, "pessoas": pessoas}

    async def resumo_total(self, guarnicao_id: int | None, bpm_id: int | None = None) -> dict:
        """Retorna totais históricos de abordagens e pessoas.

        Sem filtro de data — agrega todos os registros ativos. Pessoas cadastradas
        é sempre um total global, independente do filtro de guarnição.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).

        Returns:
            Dicionário com abordagens e pessoas totais.
        """
        base_ab = self._filtro_base(guarnicao_id, bpm_id)

        total_q = select(func.count(Abordagem.id)).where(*base_ab)
        total = (await self.db.execute(total_q)).scalar() or 0

        # Conta pessoas distintas que foram abordadas ao menos uma vez
        pessoas_abordadas_q = (
            select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
            .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(*base_ab)
        )
        pessoas_abordadas = (await self.db.execute(pessoas_abordadas_q)).scalar() or 0

        # Conta todas as pessoas cadastradas — sempre global, sem filtro de guarnição
        pessoas_cadastradas_q = select(func.count(Pessoa.id)).where(Pessoa.ativo)
        pessoas_cadastradas = (await self.db.execute(pessoas_cadastradas_q)).scalar() or 0

        return {
            "abordagens": total,
            "pessoas": pessoas_abordadas,
            "pessoas_cadastradas": pessoas_cadastradas,
        }

    async def por_dia(
        self, guarnicao_id: int | None, dias: int = 30, bpm_id: int | None = None
    ) -> list[dict]:
        """Retorna série temporal diária de abordagens e pessoas.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            dias: Número de dias retroativos (padrão 30).

        Returns:
            Lista de dicionários com data (YYYY-MM-DD), abordagens e pessoas.
        """
        desde = datetime.now(UTC) - timedelta(days=dias)
        data_label = cast(func.timezone("America/Sao_Paulo", Abordagem.data_hora), DateType).label(
            "data"
        )

        base = self._filtro_base(guarnicao_id, bpm_id)
        base.append(Abordagem.data_hora >= desde)

        query = (
            select(
                data_label,
                func.count(func.distinct(Abordagem.id)).label("abordagens"),
                func.count(func.distinct(AbordagemPessoa.pessoa_id)).label("pessoas"),
            )
            .outerjoin(AbordagemPessoa, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(*base)
            .group_by(data_label)
            .order_by(data_label)
        )
        result = await self.db.execute(query)
        return [
            {
                "data": row[0].strftime("%Y-%m-%d") if hasattr(row[0], "strftime") else str(row[0]),
                "abordagens": int(row[1]),
                "pessoas": int(row[2]),
            }
            for row in result.all()
        ]

    async def por_mes(
        self, guarnicao_id: int | None, meses: int = 12, bpm_id: int | None = None
    ) -> list[dict]:
        """Retorna série temporal mensal de abordagens e pessoas.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            meses: Número de meses retroativos (padrão 12).

        Returns:
            Lista de dicionários com mes (YYYY-MM), abordagens e pessoas.
        """
        agora = datetime.now(BRT)
        primeiro_mes_atual = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Recuar (meses - 1) meses para o início da janela
        total_meses = primeiro_mes_atual.month - (meses - 1)
        ano_inicio = primeiro_mes_atual.year + (total_meses - 1) // 12
        mes_inicio = ((total_meses - 1) % 12) + 1
        desde = primeiro_mes_atual.replace(year=ano_inicio, month=mes_inicio)
        _brt_ts = func.timezone("America/Sao_Paulo", Abordagem.data_hora)
        ano_label = extract("year", _brt_ts).label("ano")
        mes_label = extract("month", _brt_ts).label("mes")

        base = self._filtro_base(guarnicao_id, bpm_id)
        base.append(Abordagem.data_hora >= desde)

        query = (
            select(
                ano_label,
                mes_label,
                func.count(func.distinct(Abordagem.id)).label("abordagens"),
                func.count(func.distinct(AbordagemPessoa.pessoa_id)).label("pessoas"),
            )
            .outerjoin(AbordagemPessoa, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(*base)
            .group_by(ano_label, mes_label)
            .order_by(ano_label, mes_label)
        )
        result = await self.db.execute(query)
        return [
            {
                "mes": f"{int(row[0])}-{int(row[1]):02d}",
                "abordagens": int(row[2]),
                "pessoas": int(row[3]),
            }
            for row in result.all()
        ]

    async def dias_com_abordagem(
        self, guarnicao_id: int | None, mes: str, bpm_id: int | None = None
    ) -> list[int]:
        """Retorna lista de dias do mês que tiveram abordagem.

        Usado pelo calendário mini para exibir pontos indicativos.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            mes: Mês no formato "YYYY-MM" (ex: "2026-03").

        Returns:
            Lista de inteiros representando os dias com abordagem.
        """
        ano, mes_num = int(mes.split("-")[0]), int(mes.split("-")[1])
        _brt_ts = func.timezone("America/Sao_Paulo", Abordagem.data_hora)
        dia_label = extract("day", _brt_ts).label("dia")

        base = self._filtro_base(guarnicao_id, bpm_id)
        base += [
            extract("year", _brt_ts) == ano,
            extract("month", _brt_ts) == mes_num,
        ]

        query = select(dia_label).where(*base).distinct().order_by(dia_label)
        result = await self.db.execute(query)
        return [int(row[0]) for row in result.all()]

    async def pessoas_do_dia(
        self, guarnicao_id: int | None, data: str, bpm_id: int | None = None
    ) -> list[dict]:
        """Retorna pessoas abordadas em um dia específico.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            data: Data no formato "YYYY-MM-DD" (ex: "2026-03-14").

        Returns:
            Lista de dicionários com id, nome, cpf (mascarado, achado
            #16/2026-07-13) e foto_url.
        """
        data_obj = date.fromisoformat(data)

        base = self._filtro_base(guarnicao_id, bpm_id)
        base += [
            Pessoa.ativo,
            cast(func.timezone("America/Sao_Paulo", Abordagem.data_hora), DateType) == data_obj,
        ]

        query = (
            select(
                Pessoa.id,
                Pessoa.nome,
                Pessoa.cpf_encrypted,
                Pessoa.foto_principal_url,
            )
            .join(AbordagemPessoa, AbordagemPessoa.pessoa_id == Pessoa.id)
            .join(Abordagem, Abordagem.id == AbordagemPessoa.abordagem_id)
            .where(*base)
            .order_by(Pessoa.nome)
            .distinct()
        )
        result = await self.db.execute(query)
        rows = result.all()

        pessoas = []
        for row in rows:
            pessoas.append(
                {
                    "id": row[0],
                    "nome": row[1],
                    "cpf": PessoaService.mask_cpf_encrypted(row[2], context_id=row[0]),
                    "foto_url": normalize_storage_url(row[3]),
                }
            )
        return pessoas

    async def abordagens_do_dia(
        self, guarnicao_id: int | None, data: str, bpm_id: int | None = None
    ) -> list[dict]:
        """Retorna pontos geográficos das abordagens de um dia específico.

        Retorna apenas abordagens que possuem coordenadas GPS registradas.
        Usado para renderizar o mapa no dashboard analítico ao selecionar
        um dia no calendário.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).
            data: Data no formato "YYYY-MM-DD" (ex: "2026-03-28").

        Returns:
            Lista de dicionários com lat (float), lng (float) e horario (str HH:MM).
        """
        data_obj = date.fromisoformat(data)

        base = self._filtro_base(guarnicao_id, bpm_id)
        base += [
            cast(func.timezone("America/Sao_Paulo", Abordagem.data_hora), DateType) == data_obj,
            Abordagem.latitude.isnot(None),
            Abordagem.longitude.isnot(None),
        ]

        query = (
            select(
                Abordagem.latitude,
                Abordagem.longitude,
                Abordagem.data_hora,
            )
            .where(*base)
            .order_by(Abordagem.data_hora)
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "lat": float(row[0]),
                "lng": float(row[1]),
                "horario": row[2].astimezone(BRT).strftime("%H:%M") if row[2] else "—",
            }
            for row in rows
        ]

    async def metricas_rag(self, guarnicao_id: int | None, bpm_id: int | None = None) -> dict:
        """Retorna métricas de ocorrências para o módulo RAG.

        Conta total de ocorrências e quantas estão indexadas (com embedding).

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
                None = global (todas as equipes).

        Returns:
            Dict com total_ocorrencias e ocorrencias_indexadas.
        """
        from sqlalchemy import text as sql_text

        if guarnicao_id is not None:
            result_total = await self.db.execute(
                sql_text(
                    "SELECT COUNT(*) FROM ocorrencias WHERE guarnicao_id = :gid AND ativo = true"
                ),
                {"gid": guarnicao_id},
            )
            result_indexadas = await self.db.execute(
                sql_text(
                    "SELECT COUNT(*) FROM ocorrencias"
                    " WHERE guarnicao_id = :gid AND ativo = true AND embedding IS NOT NULL"
                ),
                {"gid": guarnicao_id},
            )
        elif bpm_id is not None:
            result_total = await self.db.execute(
                sql_text(
                    "SELECT COUNT(*) FROM ocorrencias"
                    " WHERE ativo = true"
                    " AND guarnicao_id IN ("
                    "SELECT id FROM guarnicoes WHERE bpm_id = :bid AND ativo = true)"
                ),
                {"bid": bpm_id},
            )
            result_indexadas = await self.db.execute(
                sql_text(
                    "SELECT COUNT(*) FROM ocorrencias"
                    " WHERE ativo = true AND embedding IS NOT NULL"
                    " AND guarnicao_id IN ("
                    "SELECT id FROM guarnicoes WHERE bpm_id = :bid AND ativo = true)"
                ),
                {"bid": bpm_id},
            )
        else:
            result_total = await self.db.execute(
                sql_text("SELECT COUNT(*) FROM ocorrencias WHERE ativo = true")
            )
            result_indexadas = await self.db.execute(
                sql_text(
                    "SELECT COUNT(*) FROM ocorrencias WHERE ativo = true AND embedding IS NOT NULL"
                )
            )
        return {
            "total_ocorrencias": result_total.scalar() or 0,
            "ocorrencias_indexadas": result_indexadas.scalar() or 0,
        }
