"""Router de CRUD de Veículos com busca por placa.

Fornece endpoints para criação, listagem, detalhe, atualização
e soft delete de veículos registrados em abordagens.
"""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.veiculo import VeiculoCreate, VeiculoRead, VeiculoUpdate
from app.services.veiculo_service import VeiculoService

router = APIRouter(prefix="/veiculos", tags=["Veículos"])


@router.post("/", response_model=VeiculoRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def criar_veiculo(
    request: Request,
    data: VeiculoCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VeiculoRead:
    """Cria novo veículo com placa normalizada.

    Normaliza placa para uppercase e verifica unicidade global.

    Args:
        request: Objeto Request do FastAPI.
        data: Dados do veículo (placa, modelo, cor, ano, tipo).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        VeiculoRead com dados do veículo criado.

    Raises:
        ConflitoDadosError: Se placa já cadastrada.

    Status Code:
        201: Veículo criado.
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


@router.get("/", response_model=list[VeiculoRead])
async def listar_veiculos(
    request: Request,
    placa: str | None = Query(None, description="Busca por placa (parcial)"),
    modelo: str | None = Query(None, description="Filtro por modelo"),
    cor: str | None = Query(None, description="Filtro por cor"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[VeiculoRead]:
    """Lista veículos com filtros opcionais.

    Suporta busca parcial por placa (ILIKE) ou listagem paginada.

    Args:
        request: Objeto Request do FastAPI.
        placa: Placa para busca parcial.
        modelo: Filtro por modelo.
        cor: Filtro por cor.
        skip: Registros a pular.
        limit: Máximo de resultados.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de VeiculoRead.
    """
    service = VeiculoService(db)
    veiculos = await service.buscar(placa=placa, skip=skip, limit=limit, user=user)
    return [VeiculoRead.model_validate(v) for v in veiculos]


@router.get("/{veiculo_id}", response_model=VeiculoRead)
async def detalhe_veiculo(
    veiculo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VeiculoRead:
    """Obtém detalhes de um veículo.

    Args:
        veiculo_id: ID do veículo.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        VeiculoRead.

    Raises:
        NaoEncontradoError: Se veículo não existe.
        AcessoNegadoError: Se veículo de outra guarnição.
    """
    service = VeiculoService(db)
    veiculo = await service.buscar_por_id(veiculo_id, user)
    return VeiculoRead.model_validate(veiculo)


@router.put("/{veiculo_id}", response_model=VeiculoRead)
async def atualizar_veiculo(
    request: Request,
    veiculo_id: int,
    data: VeiculoUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> VeiculoRead:
    """Atualiza parcialmente um veículo.

    Placa não pode ser alterada. Apenas modelo, cor, ano, tipo
    e observações são editáveis.

    Args:
        request: Objeto Request do FastAPI.
        veiculo_id: ID do veículo.
        data: Campos a atualizar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        VeiculoRead atualizado.

    Raises:
        NaoEncontradoError: Se veículo não existe.
        AcessoNegadoError: Se veículo de outra guarnição.
    """
    service = VeiculoService(db)
    veiculo = await service.atualizar(
        veiculo_id,
        data,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return VeiculoRead.model_validate(veiculo)


@router.delete("/{veiculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def desativar_veiculo(
    request: Request,
    veiculo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Desativa um veículo (soft delete).

    Args:
        request: Objeto Request do FastAPI.
        veiculo_id: ID do veículo a desativar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Raises:
        NaoEncontradoError: Se veículo não existe.
        AcessoNegadoError: Se veículo de outra guarnição.

    Status Code:
        204: Veículo desativado.
    """
    service = VeiculoService(db)
    await service.desativar(
        veiculo_id,
        user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
