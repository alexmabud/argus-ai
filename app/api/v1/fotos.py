"""Router de upload, listagem e busca de fotos.

Fornece endpoints para upload de fotos para S3/R2, listagem
por pessoa ou abordagem, busca por similaridade facial
(pgvector 512-dim) e extração de placas via OCR (EasyOCR).
"""

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.core.upload_validation import (
    converter_heic_para_jpeg,
    is_heic,
    ler_upload_com_limite,
    validar_magic_bytes_imagem,
)
from app.database.session import get_db
from app.dependencies import get_current_user, get_face_service
from app.models.pessoa import Pessoa
from app.models.usuario import Usuario
from app.schemas.foto import (
    BuscaRostoItem,
    BuscaRostoResponse,
    FotoRead,
    FotoTipo,
    FotoUploadResponse,
    OCRPlacaResponse,
)
from app.services.audit_service import AuditService
from app.services.foto_service import FotoService
from app.services.pessoa_service import PessoaService

logger = logging.getLogger("argus")

#: Tamanho máximo de upload de imagem (10 MB).
MAX_IMAGE_SIZE = 10 * 1024 * 1024
#: MIME types permitidos para upload de imagem.
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}

# Face service é opcional — requer insightface
try:
    from app.services.face_service import FaceService
except ImportError:
    FaceService = None  # type: ignore[misc, assignment]

# OCR service é opcional — requer easyocr
try:
    from app.services.ocr_service import OCRService
except ImportError:
    OCRService = None  # type: ignore[misc, assignment]

router = APIRouter(prefix="/fotos", tags=["Fotos"])


@router.post("/upload", response_model=FotoUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_foto(
    request: Request,
    file: UploadFile,
    tipo: FotoTipo = Form(FotoTipo.rosto),
    pessoa_id: int | None = Form(None, gt=0),
    abordagem_id: int | None = Form(None, gt=0),
    veiculo_id: int | None = Form(None, gt=0),
    latitude: float | None = Form(None, ge=-90, le=90),
    longitude: float | None = Form(None, ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> FotoUploadResponse:
    """Faz upload de foto para S3/R2 e cria registro.

    Aceita multipart/form-data com arquivo e metadados. A foto
    pode ser associada a uma pessoa, abordagem ou ambos.

    Args:
        request: Objeto Request do FastAPI.
        file: Arquivo de imagem (multipart/form-data).
        tipo: Tipo de foto (rosto, corpo, placa, documento).
        pessoa_id: ID da pessoa associada (opcional).
        abordagem_id: ID da abordagem associada (opcional).
        veiculo_id: ID do veículo associado (opcional — para fotos de veículos específicos).
        latitude: Latitude GPS da captura (opcional).
        longitude: Longitude GPS da captura (opcional).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        FotoUploadResponse com id, url e tipo.

    Raises:
        HTTPException: 400 se formato inválido, 413 se exceder 10 MB.

    Status Code:
        201: Foto enviada.
        429: Rate limit (10/min).
    """
    # Leitura em chunks (previne OOM) + validação de magic bytes (anti-spoofing)
    file_bytes = await ler_upload_com_limite(file, MAX_IMAGE_SIZE)
    validar_magic_bytes_imagem(file_bytes)

    # Converte HEIC/HEIF para JPEG antes de prosseguir
    original_content_type = file.content_type or "image/jpeg"
    if is_heic(file_bytes):
        file_bytes = await converter_heic_para_jpeg(file_bytes)
        original_content_type = "image/jpeg"

    filename = file.filename or "foto.jpg"
    if filename.lower().endswith((".heic", ".heif")):
        filename = filename.rsplit(".", 1)[0] + ".jpg"

    service = FotoService(db)
    try:
        foto = await service.upload_foto(
            file_bytes=file_bytes,
            filename=filename,
            content_type=original_content_type,
            pessoa_id=pessoa_id,
            abordagem_id=abordagem_id,
            veiculo_id=veiculo_id,
            tipo=tipo,
            latitude=latitude,
            longitude=longitude,
            user_id=user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao fazer upload da foto. Verifique o storage e tente novamente.",
        ) from exc

    # Atualizar foto principal da pessoa quando for rosto
    if tipo == FotoTipo.rosto and pessoa_id:
        pessoa = await db.get(Pessoa, pessoa_id)
        if pessoa:
            pessoa.foto_principal_url = foto.arquivo_url
            await db.commit()

    # Enfileirar processamento facial em background (apenas para fotos de rosto)
    if tipo == FotoTipo.rosto:
        try:
            from arq.connections import ArqRedis, create_pool

            from app.worker import WorkerSettings

            redis_pool: ArqRedis = await create_pool(WorkerSettings.redis_settings)
            await redis_pool.enqueue_job("processar_face_task", foto.id)
            await redis_pool.close()
        except Exception:
            logger.warning("Worker offline — face da foto %d será processada depois", foto.id)

    return FotoUploadResponse(id=foto.id, arquivo_url=foto.arquivo_url, tipo=foto.tipo)


@router.get("/pessoa/{pessoa_id}", response_model=list[FotoRead])
async def listar_fotos_pessoa(
    pessoa_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[FotoRead]:
    """Lista fotos de uma pessoa com paginação.

    Args:
        pessoa_id: ID da pessoa.
        skip: Registros a pular (padrão 0).
        limit: Máximo de resultados (padrão 50, máx 100).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de FotoRead ordenadas por data/hora decrescente.
    """
    service = FotoService(db)
    fotos = await service.listar_por_pessoa(pessoa_id)
    return [FotoRead.model_validate(f) for f in fotos[skip : skip + limit]]


@router.get("/abordagem/{abordagem_id}", response_model=list[FotoRead])
async def listar_fotos_abordagem(
    abordagem_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[FotoRead]:
    """Lista fotos de uma abordagem com paginação.

    Args:
        abordagem_id: ID da abordagem.
        skip: Registros a pular (padrão 0).
        limit: Máximo de resultados (padrão 50, máx 100).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de FotoRead ordenadas por data/hora decrescente.
    """
    service = FotoService(db)
    fotos = await service.listar_por_abordagem(abordagem_id)
    return [FotoRead.model_validate(f) for f in fotos[skip : skip + limit]]


@router.post("/buscar-rosto", response_model=BuscaRostoResponse)
@limiter.limit("10/minute")
async def buscar_por_rosto(
    request: Request,
    file: UploadFile,
    top_k: int = Form(5),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    face_service=Depends(get_face_service),
) -> BuscaRostoResponse:
    """Busca pessoas por similaridade facial via pgvector.

    Recebe imagem com rosto, extrai embedding facial (512-dim via
    InsightFace) e busca fotos similares no banco usando distância
    cosseno com pgvector. Retorna lista vazia com disponivel=False
    quando InsightFace não está disponível (degradação graciosa).

    Args:
        request: Objeto Request do FastAPI.
        file: Imagem com rosto para busca (multipart/form-data).
        top_k: Número máximo de resultados (padrão 5).
        db: Sessão do banco de dados.
        user: Usuário autenticado.
        face_service: Serviço InsightFace do application state (pode ser None).

    Returns:
        BuscaRostoResponse com lista de fotos similares e total.
        Retorna disponivel=False se InsightFace não estiver disponível.

    Status Code:
        200: Busca realizada (pode retornar lista vazia).
        429: Rate limit (10/min).
    """
    if face_service is None:
        return BuscaRostoResponse(resultados=[], total=0, disponivel=False)

    file_bytes = await ler_upload_com_limite(file, MAX_IMAGE_SIZE)
    validar_magic_bytes_imagem(file_bytes)
    service = FotoService(db)
    results = await service.buscar_por_rosto(
        image_bytes=file_bytes,
        face_service=face_service,
        top_k=top_k,
    )

    # Audit log — busca biométrica é operação sensível
    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="SEARCH",
        recurso="busca_facial",
        detalhes={"top_k": top_k, "resultados": len(results)},
        ip_address=request.client.host if request.client else None,
    )

    items = [
        BuscaRostoItem(
            foto_id=r["foto"].id,
            arquivo_url=r["foto"].arquivo_url,
            pessoa_id=r["foto"].pessoa_id,
            similaridade=r["similaridade"],
            nome=r["pessoa"].nome if r["pessoa"] else None,
            cpf_masked=PessoaService.mask_cpf(r["pessoa"])
            if r["pessoa"] and r["pessoa"].cpf_encrypted
            else None,
            apelido=r["pessoa"].apelido if r["pessoa"] else None,
            foto_principal_url=r["pessoa"].foto_principal_url if r["pessoa"] else None,
        )
        for r in results
    ]
    return BuscaRostoResponse(resultados=items, total=len(items))


@router.post("/ocr-placa", response_model=OCRPlacaResponse)
@limiter.limit("10/minute")
async def extrair_placa(
    request: Request,
    file: UploadFile,
    user: Usuario = Depends(get_current_user),
) -> OCRPlacaResponse:
    """Extrai placa veicular de imagem via OCR (EasyOCR).

    Processa a imagem com EasyOCR, detectando placas nos padrões
    Mercosul (ABC1D23) e antigo (ABC1234).

    Args:
        request: Objeto Request do FastAPI.
        file: Imagem com placa para extração (multipart/form-data).
        user: Usuário autenticado.

    Returns:
        OCRPlacaResponse com placa detectada ou None.

    Status Code:
        200: OCR processado (placa pode ser None se não detectada).
        429: Rate limit (10/min).
    """
    if OCRService is None:
        return OCRPlacaResponse(placa=None, detectada=False)

    file_bytes = await ler_upload_com_limite(file, MAX_IMAGE_SIZE)
    validar_magic_bytes_imagem(file_bytes)
    if is_heic(file_bytes):
        file_bytes = await converter_heic_para_jpeg(file_bytes)
    ocr = OCRService()
    placa = await ocr.extrair_placa_async(file_bytes)
    return OCRPlacaResponse(placa=placa, detectada=placa is not None)
