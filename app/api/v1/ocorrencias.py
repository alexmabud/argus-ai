"""Router de Ocorrências (boletins de ocorrência).

Fornece endpoints para upload de PDF de ocorrência, busca por nome/RAP/data,
listagem com filtros multi-tenant e detalhe individual. O processamento do
PDF (extração de texto + embedding) é feito em background via arq worker.
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.ocorrencia import OcorrenciaRead
from app.services.ocorrencia_service import OcorrenciaService

logger = logging.getLogger("argus")

#: Tamanho máximo de upload de PDF (50 MB).
MAX_PDF_SIZE = 50 * 1024 * 1024

router = APIRouter(prefix="/ocorrencias", tags=["Ocorrências"])


@router.post("/", response_model=OcorrenciaRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def criar_ocorrencia(
    request: Request,
    arquivo_pdf: UploadFile,
    numero_ocorrencia: str = Form(..., min_length=1, max_length=50),
    abordagem_id: int | None = Form(None),
    nomes_envolvidos: str | None = Form(None),
    data_ocorrencia: date = Form(..., description="Data real do fato (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> OcorrenciaRead:
    """Cria ocorrência com upload de PDF do boletim.

    Faz upload do PDF para S3/R2 e cria registro. Processamento
    (extração de texto + embedding) é enfileirado no arq worker.

    Args:
        request: Objeto Request do FastAPI.
        arquivo_pdf: Arquivo PDF do boletim de ocorrência.
        numero_ocorrencia: Número único do BO (ex: "RAP 2026/000123").
        abordagem_id: ID da abordagem vinculada (opcional).
        nomes_envolvidos: Nomes dos envolvidos separados por pipe (opcional).
        data_ocorrencia: Data real do fato ocorrido (formato YYYY-MM-DD).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        OcorrenciaRead com processada=False.

    Status Code:
        201: Ocorrência criada, processamento em background.
        429: Rate limit (10/min).
    """
    if arquivo_pdf.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato inválido. Apenas arquivos PDF são aceitos",
        )

    pdf_bytes = await arquivo_pdf.read()

    if len(pdf_bytes) > MAX_PDF_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF excede o tamanho máximo de 50 MB",
        )

    service = OcorrenciaService(db)
    ocorrencia = await service.criar(
        numero_ocorrencia=numero_ocorrencia,
        abordagem_id=abordagem_id,
        nomes_envolvidos=nomes_envolvidos,
        data_ocorrencia=data_ocorrencia,
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
        logger.warning("Worker offline — PDF %d será processado depois", ocorrencia.id)

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


@router.get("/buscar", response_model=list[OcorrenciaRead])
@limiter.limit("30/minute")
async def buscar_ocorrencias(
    request: Request,
    nome: str | None = Query(None, description="Nome do abordado no texto do PDF"),
    rap: str | None = Query(None, description="Número RAP (busca parcial)"),
    data: date | None = Query(None, description="Data real do fato ocorrido (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[OcorrenciaRead]:
    """Busca ocorrências por nome no texto extraído, RAP ou data.

    Todos os filtros são opcionais e combinados com AND. Sem filtros,
    retorna lista vazia. Busca por nome opera apenas em ocorrências
    já processadas pelo worker (processada=True).

    Args:
        request: Objeto Request do FastAPI.
        nome: Trecho do nome a buscar no texto extraído do PDF.
        rap: Trecho do número RAP para busca parcial.
        data: Data exata do fato ocorrido (formato YYYY-MM-DD).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de OcorrenciaRead ordenada por data decrescente.
    """
    if not nome and not rap and not data:
        return []
    service = OcorrenciaService(db)
    ocorrencias = await service.buscar(
        guarnicao_id=user.guarnicao_id,
        nome=nome,
        rap=rap,
        data=data,
    )
    return [OcorrenciaRead.model_validate(o) for o in ocorrencias]
