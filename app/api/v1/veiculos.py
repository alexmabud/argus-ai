"""Router de CRUD de Veículos com busca por placa.

Fornece endpoints para criação, listagem, detalhe, atualização
e soft delete de veículos registrados em abordagens.
"""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user, get_current_user_with_guarnicao
from app.models.usuario import Usuario
from app.schemas.veiculo import VeiculoCreate, VeiculoRead
from app.services.audit_service import AuditService
from app.services.veiculo_service import VeiculoService

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


@router.get("/", response_model=list[VeiculoRead])
@limiter.limit("30/minute")
async def listar_veiculos(
    request: Request,
    placa: str | None = Query(None, description="Busca parcial por placa"),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[VeiculoRead]:
    """Lista veículos com busca opcional por placa.

    Busca parcial via ILIKE na placa normalizada. Sem filtros, retorna
    lista paginada da guarnição.

    Args:
        request: Objeto Request do FastAPI.
        placa: Trecho da placa para busca parcial (opcional).
        limit: Máximo de resultados (1-100).
        skip: Registros a pular.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de VeiculoRead.
    """
    service = VeiculoService(db)
    veiculos = await service.buscar(placa=placa, skip=skip, limit=limit, user=user)
    return [VeiculoRead.model_validate(v) for v in veiculos]


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
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="veiculo",
        recurso_id=veiculo.id,
        detalhes={"placa": data.placa},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return VeiculoRead.model_validate(veiculo)


@router.get("/localidades")
@limiter.limit("30/minute")
async def listar_localidades_veiculos(
    request: Request,
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
