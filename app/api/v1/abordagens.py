"""Router de Abordagens.

Fornece endpoints para criação e listagem de abordagens em campo,
incluindo detalhe completo com pessoas, veículos, fotos e ocorrências.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NaoEncontradoError
from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user, get_current_user_with_guarnicao
from app.models.abordagem import Abordagem
from app.models.usuario import Usuario
from app.schemas.abordagem import (
    AbordagemCreate,
    AbordagemDetail,
    AbordagemRead,
    PessoaAbordagemRead,
    VeiculoAbordagemRead,
)
from app.schemas.auth import UsuarioResumoRead
from app.schemas.foto import FotoRead
from app.schemas.ocorrencia import OcorrenciaRead
from app.services.abordagem_service import AbordagemService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/abordagens", tags=["Abordagens"])


def _filtro_abordagem(user: Usuario) -> tuple[int | None, int | None]:
    """Retorna (guarnicao_id, bpm_id) para filtro de abordagens.

    Prioridade: equipe > BPM > global. Apenas um dos dois será não-None.

    Args:
        user: Usuário autenticado com guarnicao e bpm carregados.

    Returns:
        Tupla (guarnicao_id, bpm_id). Ambos None = acesso global.
    """
    if user.guarnicao and user.guarnicao.isolamento_abordagens:
        return (user.guarnicao_id, None)
    if user.guarnicao and user.guarnicao.bpm and user.guarnicao.bpm.isolamento_abordagens:
        return (None, user.guarnicao.bpm_id)
    return (None, None)


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
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="abordagem",
        recurso_id=abordagem.id,
        detalhes={"origem": data.origem or "online"},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return AbordagemRead.model_validate(abordagem)


@router.get("/", response_model=list[AbordagemDetail])
@limiter.limit("30/minute")
async def listar_abordagens(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    data: date | None = Query(
        None, description="Filtrar por data (YYYY-MM-DD). Ignora skip/limit."
    ),
    q: str | None = Query(
        None,
        min_length=1,
        max_length=200,
        description="Busca por nome, placa ou endereço em todas as datas.",
    ),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[AbordagemDetail]:
    """Lista abordagens da guarnição com paginação, filtro por data ou busca textual.

    Prioridade dos filtros: `q` > `data` > paginação padrão.
    Quando `q` é informado, busca por nome de pessoa, placa ou endereço
    em todas as datas, ignorando `data` e `skip`/`limit`.
    Quando apenas `data` é informado, retorna todas as abordagens do dia.
    Sem filtros, retorna lista paginada.

    Args:
        request: Objeto Request do FastAPI.
        skip: Registros a pular (ignorado se `q` ou `data` informados).
        limit: Máximo de resultados 1-100 (ignorado se `q` ou `data` informados).
        data: Data para filtrar abordagens (YYYY-MM-DD), opcional.
        q: Termo de busca textual em todas as datas, opcional.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de AbordagemDetail ordenada por data/hora decrescente.

    Status Code:
        200: Lista retornada.
        403: Usuário sem guarnição.
        422: Formato de data inválido.
        429: Rate limit (30/min).
    """
    if user.guarnicao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem guarnição atribuída",
        )
    guarnicao_id_filtro, bpm_id_filtro = _filtro_abordagem(user)
    service = AbordagemService(db)
    if q is not None:
        abordagens = await service.buscar_por_texto(
            q=q,
            guarnicao_id=guarnicao_id_filtro,
            bpm_id=bpm_id_filtro,
        )
    elif data is not None:
        abordagens = await service.listar_por_data(
            guarnicao_id=guarnicao_id_filtro,
            data=data,
            bpm_id=bpm_id_filtro,
        )
    else:
        abordagens = await service.listar(
            guarnicao_id=guarnicao_id_filtro,
            bpm_id=bpm_id_filtro,
            skip=skip,
            limit=limit,
        )
    return [_serializar_detalhe(a) for a in abordagens]


@router.get("/{abordagem_id}", response_model=AbordagemDetail)
@limiter.limit("60/minute")
async def detalhe_abordagem(
    request: Request,
    abordagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> AbordagemDetail:
    """Retorna detalhe completo de uma abordagem.

    Carrega todos os relacionamentos: pessoas abordadas, veículos,
    fotos (inclui mídias) e ocorrências (RAPs) vinculadas.

    Args:
        request: Objeto Request do FastAPI.
        abordagem_id: Identificador da abordagem.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        AbordagemDetail com todos os relacionamentos.

    Raises:
        HTTPException 404: Abordagem não encontrada ou não pertence à guarnição.

    Status Code:
        200: Detalhe retornado.
        404: Abordagem não encontrada.
        429: Rate limit (60/min).
    """
    if user.guarnicao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem guarnição atribuída",
        )
    guarnicao_id_filtro, bpm_id_filtro = _filtro_abordagem(user)
    service = AbordagemService(db)
    try:
        abordagem = await service.buscar_detalhe(
            abordagem_id, guarnicao_id_filtro, bpm_id=bpm_id_filtro
        )
    except NaoEncontradoError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Abordagem não encontrada",
        )
    return _serializar_detalhe(abordagem)


def _serializar_detalhe(abordagem: Abordagem) -> AbordagemDetail:
    """Serializa Abordagem com relacionamentos para AbordagemDetail.

    Extrai Pessoa dos objetos AbordagemPessoa e Veiculo dos
    AbordagemVeiculo antes de montar o schema de resposta.
    Filtra associações inativas (soft delete).
    Também popula o campo `usuario` com os dados resumidos do policial
    que registrou a abordagem (UsuarioResumoRead), quando disponível.

    Args:
        abordagem: Objeto Abordagem com relacionamentos carregados via selectinload.

    Returns:
        AbordagemDetail serializado com listas populadas, incluindo
        pessoas, veículos, fotos, ocorrências e usuário (policial).
    """
    pessoas = [
        PessoaAbordagemRead.model_validate(ap.pessoa)
        for ap in abordagem.pessoas
        if ap.ativo and ap.pessoa
    ]
    veiculos = [
        VeiculoAbordagemRead(
            **VeiculoAbordagemRead.model_validate(av.veiculo).model_dump(exclude={"pessoa_id"}),
            pessoa_id=av.pessoa_id,
        )
        for av in abordagem.veiculos
        if av.ativo and av.veiculo
    ]
    fotos = [FotoRead.model_validate(f) for f in abordagem.fotos if f.ativo]
    ocorrencias = [OcorrenciaRead.model_validate(o) for o in abordagem.ocorrencias if o.ativo]

    usuario = UsuarioResumoRead.model_validate(abordagem.usuario) if abordagem.usuario else None
    base = AbordagemRead.model_validate(abordagem)
    return AbordagemDetail(
        **base.model_dump(),
        pessoas=pessoas,
        veiculos=veiculos,
        fotos=fotos,
        ocorrencias=ocorrencias,
        usuario=usuario,
    )
