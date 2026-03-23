"""Router de CRUD de Veículos com busca por placa.

Fornece endpoints para criação, listagem, detalhe, atualização
e soft delete de veículos registrados em abordagens.
"""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user, get_current_user_with_guarnicao
from app.models.usuario import Usuario
from app.schemas.veiculo import VeiculoCreate, VeiculoRead
from app.services.veiculo_service import VeiculoService

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


@router.post("/", response_model=VeiculoRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def criar_veiculo(
    request: Request,
    data: VeiculoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user_with_guarnicao),
) -> VeiculoRead:
    """Cria novo veículo com placa normalizada.

    Normaliza placa para uppercase e verifica unicidade global.

    Args:
        request: Objeto Request do FastAPI.
        data: Dados do veículo (placa, modelo, cor, ano, tipo).
        db: Sessão do banco de dados.
        user: Usuário autenticado com guarnição atribuída.

    Returns:
        VeiculoRead com dados do veículo criado.

    Raises:
        ConflitoDadosError: Se placa já cadastrada.

    Status Code:
        201: Veículo criado.
        403: Usuário sem guarnição.
        409: Placa duplicada.
        429: Rate limit (30/min).
    """
    service = VeiculoService(db)
    veiculo = await service.criar(
        data,
        user_id=user.id,
        guarnicao_id=user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return VeiculoRead.model_validate(veiculo)


@router.get("/localidades")
async def listar_localidades_veiculos(
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Retorna valores distintos de modelo e cor cadastrados.

    Utilizado pelo frontend para popular datalists de autocomplete nos
    campos de modelo e cor do formulário de veículo.

    Args:
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Dicionário com "modelos" e "cores" — listas de strings distintas
        ordenadas alfabeticamente.
    """
    service = VeiculoService(db)
    return await service.listar_localidades(guarnicao_id=user.guarnicao_id)
