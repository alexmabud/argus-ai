"""Router de analytics e métricas operacionais.

Fornece endpoints para o dashboard analítico: pessoas recorrentes,
resumo diário/mensal/total e séries temporais.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/pessoas-recorrentes")
async def pessoas_recorrentes(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna pessoas mais abordadas.

    Args:
        limit: Número máximo de resultados (1-100, padrão 20).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com nome, apelido, total_abordagens e ultima_abordagem.
    """
    service = AnalyticsService(db)
    return await service.pessoas_recorrentes(user.guarnicao_id, limit)


@router.get("/resumo-hoje")
async def resumo_hoje(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna total de abordagens e pessoas abordadas hoje.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com abordagens e pessoas do dia atual.
    """
    service = AnalyticsService(db)
    return await service.resumo_hoje(user.guarnicao_id)


@router.get("/resumo-mes")
async def resumo_mes(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna total de abordagens e pessoas abordadas no mês atual.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com abordagens e pessoas do mês corrente.
    """
    service = AnalyticsService(db)
    return await service.resumo_mes(user.guarnicao_id)


@router.get("/resumo-total")
async def resumo_total(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna totais históricos de abordagens e pessoas.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com abordagens e pessoas totais.
    """
    service = AnalyticsService(db)
    return await service.resumo_total(user.guarnicao_id)


@router.get("/por-dia")
async def por_dia(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna série temporal diária de abordagens e pessoas.

    Args:
        dias: Número de dias retroativos (1-365, padrão 30).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com data, abordagens e pessoas por dia.
    """
    service = AnalyticsService(db)
    return await service.por_dia(user.guarnicao_id, dias)


@router.get("/por-mes")
async def por_mes(
    meses: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna série temporal mensal de abordagens e pessoas.

    Args:
        meses: Número de meses retroativos (1-36, padrão 12).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com mes, abordagens e pessoas por mês.
    """
    service = AnalyticsService(db)
    return await service.por_mes(user.guarnicao_id, meses)


@router.get("/dias-com-abordagem")
async def dias_com_abordagem(
    mes: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[int]:
    """Retorna dias do mês que tiveram abordagem registrada.

    Usado pelo calendário mini para exibir indicadores nos dias com atividade.

    Args:
        mes: Mês no formato YYYY-MM (ex: "2026-03").
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de inteiros representando os dias com abordagem.
    """
    service = AnalyticsService(db)
    return await service.dias_com_abordagem(user.guarnicao_id, mes)


@router.get("/abordagens-do-dia")
async def abordagens_do_dia(
    data: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna pontos geográficos das abordagens de um dia específico.

    Usado pelo mapa no dashboard analítico para exibir onde foram realizadas
    as abordagens do dia selecionado no calendário.

    Args:
        data: Data no formato YYYY-MM-DD.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com lat, lng e horario (HH:MM) de cada abordagem com localização.
    """
    service = AnalyticsService(db)
    return await service.abordagens_do_dia(user.guarnicao_id, str(data))


@router.get("/pessoas-do-dia")
async def pessoas_do_dia(
    data: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna pessoas abordadas em um dia específico.

    Args:
        data: Data no formato YYYY-MM-DD.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com id, nome, cpf e foto_url das pessoas abordadas.
    """
    service = AnalyticsService(db)
    return await service.pessoas_do_dia(user.guarnicao_id, str(data))
