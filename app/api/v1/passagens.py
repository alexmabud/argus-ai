"""Router de CRUD para Passagens (tipos penais/infrações).

Fornece endpoints para criação, listagem e busca de passagens
criminais e infrações administrativas. Passagens são dados de
catálogo compartilhados entre guarnições (sem multi-tenancy).
"""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.passagem import PassagemCreate, PassagemRead
from app.services.passagem_service import PassagemService

router = APIRouter(prefix="/passagens", tags=["Passagens"])


@router.post("/", response_model=PassagemRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def criar_passagem(
    request: Request,
    data: PassagemCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PassagemRead:
    """Cria nova passagem criminal (tipo penal).

    Verifica unicidade da combinação (lei, artigo) antes de criar.
    Requer autenticação mas não aplica filtro multi-tenant (catálogo global).

    Args:
        request: Objeto Request do FastAPI.
        data: Dados de criação (lei, artigo, nome_crime).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PassagemRead com id, lei, artigo e nome_crime.

    Status Code:
        201: Passagem criada.
        409: Combinação (lei, artigo) já existe.
        429: Rate limit (10/min).
    """
    service = PassagemService(db)
    passagem = await service.criar(
        data=data,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return PassagemRead.model_validate(passagem)


@router.get("/", response_model=list[PassagemRead])
async def listar_passagens(
    lei: str | None = Query(None, description="Filtrar por lei (ex: CP, LCP)"),
    artigo: str | None = Query(None, description="Filtrar por artigo (ex: 121)"),
    nome_crime: str | None = Query(None, description="Busca parcial por nome do crime"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[PassagemRead]:
    """Lista passagens com filtros opcionais.

    Filtros combinados com AND. Nome de crime usa busca parcial (ILIKE).
    Requer autenticação mas sem filtro multi-tenant (catálogo global).

    Args:
        lei: Filtro por lei (busca exata, opcional).
        artigo: Filtro por artigo (busca exata, opcional).
        nome_crime: Busca parcial por nome do crime (ILIKE, opcional).
        skip: Registros a pular (paginação).
        limit: Máximo de resultados (1-100, padrão 50).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de PassagemRead.
    """
    service = PassagemService(db)
    passagens = await service.buscar(
        lei=lei, artigo=artigo, nome_crime=nome_crime, skip=skip, limit=limit
    )
    return [PassagemRead.model_validate(p) for p in passagens]


@router.get("/{passagem_id}", response_model=PassagemRead)
async def obter_passagem(
    passagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> PassagemRead:
    """Obtém passagem por ID.

    Args:
        passagem_id: ID da passagem.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        PassagemRead com dados da passagem.

    Status Code:
        404: Passagem não encontrada.
    """
    service = PassagemService(db)
    passagem = await service.buscar_por_id(passagem_id)
    return PassagemRead.model_validate(passagem)
