"""Router de criação de Abordagens.

Fornece endpoint para criação completa de abordagens em campo.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user_with_guarnicao
from app.models.usuario import Usuario
from app.schemas.abordagem import (
    AbordagemCreate,
    AbordagemRead,
)
from app.services.abordagem_service import AbordagemService

router = APIRouter(prefix="/abordagens", tags=["Abordagens"])


@router.post("/", response_model=AbordagemRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def criar_abordagem(
    request: Request,
    data: AbordagemCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user_with_guarnicao),
) -> AbordagemRead:
    """Cria nova abordagem com vinculações em payload único.

    Endpoint central para registro rápido em campo (< 40 segundos).
    Aceita pessoas e veículos em uma única requisição.
    Realiza geocoding reverso, cria ponto PostGIS e materializa
    relacionamentos entre pessoas automaticamente.

    Args:
        request: Objeto Request do FastAPI.
        data: Dados completos da abordagem.
        db: Sessão do banco de dados.
        user: Usuário autenticado com guarnição atribuída.

    Returns:
        AbordagemRead com dados da abordagem criada.

    Status Code:
        201: Abordagem criada.
        403: Usuário sem guarnição.
        429: Rate limit (30/min).
    """
    service = AbordagemService(db)
    abordagem = await service.criar(
        data,
        user_id=user.id,
        guarnicao_id=user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return AbordagemRead.model_validate(abordagem)
