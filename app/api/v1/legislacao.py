"""Router de Legislação (artigos de lei indexados para RAG).

Fornece endpoints para listagem e busca semântica de artigos de
legislação. Legislação é dado global (sem filtro multi-tenant).
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user, get_embedding_service
from app.models.usuario import Usuario
from app.schemas.legislacao import LegislacaoRead, LegislacaoSemanticaRead
from app.services.embedding_service import EmbeddingService
from app.services.legislacao_service import LegislacaoService

router = APIRouter(prefix="/legislacao", tags=["Legislação"])


@router.get("/", response_model=list[LegislacaoRead])
async def listar_legislacao(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[LegislacaoRead]:
    """Lista artigos de legislação com paginação.

    Dados globais acessíveis por qualquer guarnição.

    Args:
        request: Objeto Request do FastAPI.
        skip: Registros a pular.
        limit: Máximo de resultados (1-200).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de LegislacaoRead.
    """
    service = LegislacaoService(db)
    legislacoes = await service.listar(skip=skip, limit=limit)
    return [LegislacaoRead.model_validate(leg) for leg in legislacoes]


@router.get("/busca", response_model=list[LegislacaoSemanticaRead])
async def buscar_legislacao_semantica(
    request: Request,
    q: str = Query(..., min_length=2, max_length=500, description="Termo de busca"),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> list[LegislacaoSemanticaRead]:
    """Busca legislação por similaridade semântica (pgvector).

    Gera embedding do termo de busca e encontra artigos de lei
    semanticamente similares via distância cosseno.

    Args:
        request: Objeto Request do FastAPI.
        q: Texto de busca em linguagem natural.
        top_k: Máximo de resultados (1-20).
        db: Sessão do banco de dados.
        user: Usuário autenticado.
        embedding_service: Serviço de embedding injetado.

    Returns:
        Lista de LegislacaoSemanticaRead com score de similaridade.
    """
    service = LegislacaoService(db)
    resultados = await service.buscar_semantica(q, embedding_service, top_k=top_k)

    return [
        LegislacaoSemanticaRead(
            id=item["legislacao"].id,
            lei=item["legislacao"].lei,
            artigo=item["legislacao"].artigo,
            nome=item["legislacao"].nome,
            texto=item["legislacao"].texto,
            ativo=item["legislacao"].ativo,
            criado_em=item["legislacao"].criado_em,
            atualizado_em=item["legislacao"].atualizado_em,
            similaridade=item["similaridade"],
        )
        for item in resultados
    ]


@router.get("/{legislacao_id}", response_model=LegislacaoRead)
async def detalhe_legislacao(
    legislacao_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> LegislacaoRead:
    """Obtém detalhes de um artigo de legislação.

    Args:
        legislacao_id: ID da legislação.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        LegislacaoRead com dados do artigo.

    Raises:
        NaoEncontradoError: Se legislação não existe ou inativa.
    """
    service = LegislacaoService(db)
    legislacao = await service.buscar_por_id(legislacao_id)
    return LegislacaoRead.model_validate(legislacao)
