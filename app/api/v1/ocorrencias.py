"""Router de Ocorrências (boletins de ocorrência).

Fornece endpoints para upload de PDF de ocorrência, listagem com filtros
multi-tenant e detalhe individual. O processamento do PDF (extração de
texto + embedding) é feito em background via arq worker.
"""

from fastapi import APIRouter, Depends, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.ocorrencia import OcorrenciaCreate, OcorrenciaRead
from app.services.ocorrencia_service import OcorrenciaService

router = APIRouter(prefix="/ocorrencias", tags=["Ocorrências"])


@router.post("/", response_model=OcorrenciaRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def criar_ocorrencia(
    request: Request,
    data: OcorrenciaCreate = Depends(),
    arquivo_pdf: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> OcorrenciaRead:
    """Cria ocorrência com upload de PDF do boletim.

    Faz upload do PDF para S3/R2 e cria registro. Processamento
    (extração de texto + embedding) é enfileirado no arq worker.

    Args:
        request: Objeto Request do FastAPI.
        data: Dados básicos (numero_ocorrencia, abordagem_id).
        arquivo_pdf: Arquivo PDF do boletim de ocorrência.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        OcorrenciaRead com processada=False.

    Status Code:
        201: Ocorrência criada, processamento em background.
        429: Rate limit (10/min).
    """
    pdf_bytes = await arquivo_pdf.read()
    service = OcorrenciaService(db)
    ocorrencia = await service.criar(
        numero_ocorrencia=data.numero_ocorrencia,
        abordagem_id=data.abordagem_id,
        arquivo_pdf=pdf_bytes,
        filename=arquivo_pdf.filename or "ocorrencia.pdf",
        usuario_id=user.id,
        guarnicao_id=user.guarnicao_id,
    )

    # Enfileirar processamento em background
    try:
        from arq.connections import ArqRedis, create_pool

        from app.worker import WorkerSettings

        redis_pool: ArqRedis = await create_pool(WorkerSettings.redis_settings)
        await redis_pool.enqueue_job("processar_pdf_task", ocorrencia.id)
        await redis_pool.close()
    except Exception:
        pass  # Worker offline — processamento será feito depois

    return OcorrenciaRead.model_validate(ocorrencia)


@router.get("/", response_model=list[OcorrenciaRead])
async def listar_ocorrencias(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[OcorrenciaRead]:
    """Lista ocorrências da guarnição com paginação.

    Args:
        request: Objeto Request do FastAPI.
        skip: Registros a pular.
        limit: Máximo de resultados (1-100).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de OcorrenciaRead.
    """
    service = OcorrenciaService(db)
    ocorrencias = await service.listar(guarnicao_id=user.guarnicao_id, skip=skip, limit=limit)
    return [OcorrenciaRead.model_validate(o) for o in ocorrencias]


@router.get("/{ocorrencia_id}", response_model=OcorrenciaRead)
async def detalhe_ocorrencia(
    ocorrencia_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> OcorrenciaRead:
    """Obtém detalhes de uma ocorrência.

    Args:
        ocorrencia_id: ID da ocorrência.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        OcorrenciaRead com dados da ocorrência.

    Raises:
        NaoEncontradoError: Se ocorrência não existe ou de outra guarnição.
    """
    service = OcorrenciaService(db)
    ocorrencia = await service.buscar_por_id(ocorrencia_id, user.guarnicao_id)
    return OcorrenciaRead.model_validate(ocorrencia)
