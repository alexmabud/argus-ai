"""Router de CRUD de Abordagens com PostGIS e vinculações.

Fornece endpoints para criação completa de abordagens, busca por raio
geográfico (PostGIS), vinculação/desvinculação de pessoas e veículos.
"""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.abordagem import (
    AbordagemCreate,
    AbordagemDetail,
    AbordagemRead,
    AbordagemUpdate,
)
from app.schemas.passagem import PassagemRead, PassagemVinculoRead
from app.schemas.pessoa import PessoaRead
from app.schemas.veiculo import VeiculoRead
from app.services.abordagem_service import AbordagemService
from app.services.pessoa_service import PessoaService

router = APIRouter(prefix="/abordagens", tags=["Abordagens"])


@router.post("/", response_model=AbordagemRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def criar_abordagem(
    request: Request,
    data: AbordagemCreate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> AbordagemRead:
    """Cria nova abordagem com vinculações em payload único.

    Endpoint central para registro rápido em campo (< 40 segundos).
    Aceita pessoas, veículos e passagens em uma única requisição.
    Realiza geocoding reverso, cria ponto PostGIS e materializa
    relacionamentos entre pessoas automaticamente.

    Args:
        request: Objeto Request do FastAPI.
        data: Dados completos da abordagem.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        AbordagemRead com dados da abordagem criada.

    Status Code:
        201: Abordagem criada.
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


@router.get("/raio/", response_model=list[AbordagemRead])
async def abordagens_por_raio(
    request: Request,
    lat: float = Query(..., description="Latitude do ponto central"),
    lon: float = Query(..., description="Longitude do ponto central"),
    raio_metros: int = Query(500, ge=50, le=50000, description="Raio em metros"),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[AbordagemRead]:
    """Busca abordagens por raio geográfico (PostGIS ST_DWithin).

    Retorna abordagens dentro do raio especificado em metros,
    ordenadas por data/hora decrescente. Máximo 50 resultados.

    Args:
        request: Objeto Request do FastAPI.
        lat: Latitude do ponto central.
        lon: Longitude do ponto central.
        raio_metros: Raio de busca em metros (50-50000, padrão 500).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de AbordagemRead dentro do raio.
    """
    service = AbordagemService(db)
    abordagens = await service.buscar_por_raio(lat, lon, raio_metros, user.guarnicao_id)
    return [AbordagemRead.model_validate(a) for a in abordagens]


@router.get("/", response_model=list[AbordagemRead])
async def listar_abordagens(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[AbordagemRead]:
    """Lista abordagens da guarnição ordenadas por data/hora.

    Args:
        request: Objeto Request do FastAPI.
        skip: Registros a pular (paginação).
        limit: Máximo de resultados (1-100).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de AbordagemRead.
    """
    service = AbordagemService(db)
    abordagens = await service.listar(user.guarnicao_id, skip, limit)
    return [AbordagemRead.model_validate(a) for a in abordagens]


@router.get("/{abordagem_id}", response_model=AbordagemDetail)
async def detalhe_abordagem(
    abordagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> AbordagemDetail:
    """Obtém detalhes completos de uma abordagem.

    Retorna abordagem com pessoas, veículos, fotos e passagens
    vinculadas (eager loaded).

    Args:
        abordagem_id: ID da abordagem.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        AbordagemDetail com todos os relacionamentos.

    Raises:
        NaoEncontradoError: Se abordagem não existe.
        AcessoNegadoError: Se abordagem de outra guarnição.
    """
    service = AbordagemService(db)
    abordagem = await service.buscar_detalhe(abordagem_id, user.guarnicao_id)
    pessoa_service = PessoaService(db)

    # Montar pessoas a partir da associação M:N
    pessoas = []
    for ap in abordagem.pessoas:
        p = ap.pessoa
        pessoas.append(
            PessoaRead(
                id=p.id,
                nome=p.nome,
                cpf_masked=pessoa_service.mask_cpf(p),
                data_nascimento=p.data_nascimento,
                apelido=p.apelido,
                foto_principal_url=p.foto_principal_url,
                observacoes=p.observacoes,
                guarnicao_id=p.guarnicao_id,
                criado_em=p.criado_em,
                atualizado_em=p.atualizado_em,
            )
        )

    # Montar veículos a partir da associação M:N
    veiculos = [VeiculoRead.model_validate(av.veiculo) for av in abordagem.veiculos]

    # Montar passagens vinculadas
    passagens = [
        PassagemVinculoRead(
            passagem=PassagemRead.model_validate(ap.passagem),
            pessoa_id=ap.pessoa_id,
        )
        for ap in abordagem.passagens
    ]

    return AbordagemDetail(
        id=abordagem.id,
        data_hora=abordagem.data_hora,
        latitude=abordagem.latitude,
        longitude=abordagem.longitude,
        endereco_texto=abordagem.endereco_texto,
        observacao=abordagem.observacao,
        usuario_id=abordagem.usuario_id,
        guarnicao_id=abordagem.guarnicao_id,
        origem=abordagem.origem,
        criado_em=abordagem.criado_em,
        atualizado_em=abordagem.atualizado_em,
        pessoas=pessoas,
        veiculos=veiculos,
        fotos=[],
        passagens=passagens,
    )


@router.put("/{abordagem_id}", response_model=AbordagemRead)
async def atualizar_abordagem(
    request: Request,
    abordagem_id: int,
    data: AbordagemUpdate,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> AbordagemRead:
    """Atualiza parcialmente uma abordagem.

    Apenas observação e endereço_texto são editáveis pós-criação.

    Args:
        request: Objeto Request do FastAPI.
        abordagem_id: ID da abordagem.
        data: Campos a atualizar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        AbordagemRead atualizada.

    Raises:
        NaoEncontradoError: Se abordagem não existe.
        AcessoNegadoError: Se abordagem de outra guarnição.
    """
    service = AbordagemService(db)
    abordagem = await service.atualizar(
        abordagem_id,
        data,
        user.id,
        user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return AbordagemRead.model_validate(abordagem)


@router.post(
    "/{abordagem_id}/pessoas/{pessoa_id}",
    status_code=status.HTTP_201_CREATED,
)
async def vincular_pessoa(
    request: Request,
    abordagem_id: int,
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Vincula pessoa a abordagem existente.

    Também materializa relacionamentos com outras pessoas já vinculadas.

    Args:
        request: Objeto Request do FastAPI.
        abordagem_id: ID da abordagem.
        pessoa_id: ID da pessoa a vincular.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Confirmação de vinculação.

    Status Code:
        201: Pessoa vinculada.
    """
    service = AbordagemService(db)
    await service.vincular_pessoa(
        abordagem_id,
        pessoa_id,
        user.id,
        user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"detail": "Pessoa vinculada com sucesso"}


@router.delete(
    "/{abordagem_id}/pessoas/{pessoa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def desvincular_pessoa(
    request: Request,
    abordagem_id: int,
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Desvincula pessoa de abordagem existente.

    Args:
        request: Objeto Request do FastAPI.
        abordagem_id: ID da abordagem.
        pessoa_id: ID da pessoa a desvincular.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Status Code:
        204: Pessoa desvinculada.
    """
    service = AbordagemService(db)
    await service.desvincular_pessoa(
        abordagem_id,
        pessoa_id,
        user.id,
        user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/{abordagem_id}/veiculos/{veiculo_id}",
    status_code=status.HTTP_201_CREATED,
)
async def vincular_veiculo(
    request: Request,
    abordagem_id: int,
    veiculo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> dict:
    """Vincula veículo a abordagem existente.

    Args:
        request: Objeto Request do FastAPI.
        abordagem_id: ID da abordagem.
        veiculo_id: ID do veículo a vincular.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Confirmação de vinculação.

    Status Code:
        201: Veículo vinculado.
    """
    service = AbordagemService(db)
    await service.vincular_veiculo(
        abordagem_id,
        veiculo_id,
        user.id,
        user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"detail": "Veículo vinculado com sucesso"}


@router.delete(
    "/{abordagem_id}/veiculos/{veiculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def desvincular_veiculo(
    request: Request,
    abordagem_id: int,
    veiculo_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> None:
    """Desvincula veículo de abordagem existente.

    Args:
        request: Objeto Request do FastAPI.
        abordagem_id: ID da abordagem.
        veiculo_id: ID do veículo a desvincular.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Status Code:
        204: Veículo desvinculado.
    """
    service = AbordagemService(db)
    await service.desvincular_veiculo(
        abordagem_id,
        veiculo_id,
        user.id,
        user.guarnicao_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
