"""Router de analytics e métricas operacionais.

Fornece endpoints para o dashboard analítico: resumo,
mapa de calor, horários de pico, pessoas recorrentes
e métricas de qualidade RAG.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/resumo")
async def resumo(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna resumo operacional do período.

    Args:
        dias: Número de dias do período (1-365, padrão 30).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Resumo com total_abordagens, pessoas_distintas e média/dia.
    """
    service = AnalyticsService(db)
    return await service.resumo(user.guarnicao_id, dias)


@router.get("/mapa-calor")
async def mapa_calor(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna pontos para mapa de calor de abordagens.

    Args:
        dias: Número de dias do período (1-365, padrão 30).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de pontos com lat e lon.
    """
    service = AnalyticsService(db)
    return await service.mapa_calor(user.guarnicao_id, dias)


@router.get("/horarios-pico")
async def horarios_pico(
    dias: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna distribuição horária de abordagens.

    Args:
        dias: Número de dias do período (1-365, padrão 30).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com hora (0-23) e total.
    """
    service = AnalyticsService(db)
    return await service.horarios_pico(user.guarnicao_id, dias)


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


@router.get("/rag-qualidade")
async def rag_qualidade(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna métricas de qualidade do RAG.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Métricas com total_ocorrencias e ocorrencias_indexadas.
    """
    service = AnalyticsService(db)
    return await service.metricas_rag(user.guarnicao_id)
