"""Serviço de analytics operacional.

Fornece métricas agregadas para o dashboard: resumo de abordagens,
mapa de calor, distribuição horária, pessoas recorrentes e qualidade RAG.
Respeita multi-tenancy (guarnicao_id) e soft delete em todas as queries.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.abordagem import Abordagem, AbordagemPessoa
from app.models.ocorrencia import Ocorrencia
from app.models.pessoa import Pessoa


class AnalyticsService:
    """Serviço de métricas analíticas da guarnição.

    Gera dados agregados para visualização no dashboard:
    resumo operacional, heatmap geográfico, picos horários,
    pessoas mais abordadas e métricas de qualidade RAG.

    Attributes:
        db: Sessão assíncrona do SQLAlchemy.
    """

    def __init__(self, db: AsyncSession):
        """Inicializa o serviço de analytics.

        Args:
            db: Sessão assíncrona do SQLAlchemy.
        """
        self.db = db

    async def resumo(self, guarnicao_id: int, dias: int = 30) -> dict:
        """Retorna resumo operacional do período.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            dias: Número de dias do período (padrão 30).

        Returns:
            Dicionário com periodo_dias, total_abordagens,
            total_pessoas_distintas e media_abordagens_dia.
        """
        desde = datetime.now(UTC) - timedelta(days=dias)

        # Total abordagens
        total_q = select(func.count(Abordagem.id)).where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.deleted_at.is_(None),
            Abordagem.data_hora >= desde,
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        # Pessoas distintas
        pessoas_q = (
            select(func.count(func.distinct(AbordagemPessoa.pessoa_id)))
            .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.deleted_at.is_(None),
                Abordagem.data_hora >= desde,
            )
        )
        pessoas = (await self.db.execute(pessoas_q)).scalar() or 0

        return {
            "periodo_dias": dias,
            "total_abordagens": total,
            "total_pessoas_distintas": pessoas,
            "media_abordagens_dia": round(total / max(dias, 1), 1),
        }

    async def mapa_calor(self, guarnicao_id: int, dias: int = 30) -> list[dict]:
        """Retorna pontos geográficos para mapa de calor.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            dias: Número de dias do período (padrão 30).

        Returns:
            Lista de dicionários com lat e lon.
        """
        desde = datetime.now(UTC) - timedelta(days=dias)

        query = select(Abordagem.latitude, Abordagem.longitude).where(
            Abordagem.guarnicao_id == guarnicao_id,
            Abordagem.deleted_at.is_(None),
            Abordagem.data_hora >= desde,
            Abordagem.latitude.isnot(None),
            Abordagem.longitude.isnot(None),
        )
        result = await self.db.execute(query)
        return [{"lat": float(row[0]), "lon": float(row[1])} for row in result.all()]

    async def horarios_pico(self, guarnicao_id: int, dias: int = 30) -> list[dict]:
        """Retorna distribuição horária das abordagens.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            dias: Número de dias do período (padrão 30).

        Returns:
            Lista de dicionários com hora (0-23) e total.
        """
        desde = datetime.now(UTC) - timedelta(days=dias)

        hora = extract("hour", Abordagem.data_hora).label("hora")
        query = (
            select(hora, func.count(Abordagem.id).label("total"))
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.deleted_at.is_(None),
                Abordagem.data_hora >= desde,
            )
            .group_by(hora)
            .order_by(hora)
        )
        result = await self.db.execute(query)
        return [{"hora": int(row[0]), "total": int(row[1])} for row in result.all()]

    async def pessoas_recorrentes(self, guarnicao_id: int, limit: int = 20) -> list[dict]:
        """Retorna pessoas mais abordadas.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            limit: Número máximo de resultados (padrão 20, máximo 100).

        Returns:
            Lista de dicionários com id, nome, apelido,
            total_abordagens e ultima_abordagem.
        """
        limit = min(limit, 100)

        query = (
            select(
                Pessoa.id,
                Pessoa.nome,
                Pessoa.apelido,
                func.count(AbordagemPessoa.abordagem_id).label("total"),
                func.max(Abordagem.data_hora).label("ultima"),
            )
            .join(AbordagemPessoa, Pessoa.id == AbordagemPessoa.pessoa_id)
            .join(Abordagem, AbordagemPessoa.abordagem_id == Abordagem.id)
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.deleted_at.is_(None),
                Pessoa.deleted_at.is_(None),
            )
            .group_by(Pessoa.id, Pessoa.nome, Pessoa.apelido)
            .order_by(func.count(AbordagemPessoa.abordagem_id).desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return [
            {
                "id": row[0],
                "nome": row[1],
                "apelido": row[2],
                "total_abordagens": int(row[3]),
                "ultima_abordagem": row[4].isoformat() if row[4] else None,
            }
            for row in result.all()
        ]

    async def metricas_rag(self, guarnicao_id: int) -> dict:
        """Retorna métricas de qualidade do RAG.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.

        Returns:
            Dicionário com total_ocorrencias e ocorrencias_indexadas.
        """
        total_q = select(func.count(Ocorrencia.id)).where(
            Ocorrencia.guarnicao_id == guarnicao_id,
            Ocorrencia.deleted_at.is_(None),
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        indexadas_q = select(func.count(Ocorrencia.id)).where(
            Ocorrencia.guarnicao_id == guarnicao_id,
            Ocorrencia.deleted_at.is_(None),
            Ocorrencia.processada.is_(True),
        )
        indexadas = (await self.db.execute(indexadas_q)).scalar() or 0

        return {
            "total_ocorrencias": total,
            "ocorrencias_indexadas": indexadas,
        }
