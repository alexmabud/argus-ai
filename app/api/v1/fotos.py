"""Router de upload, listagem e busca de fotos.

Fornece endpoints para upload de fotos para S3/R2, listagem
por pessoa ou abordagem, busca por similaridade facial
(pgvector 512-dim) e extração de placas via OCR (EasyOCR).
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user, get_face_service
from app.models.usuario import Usuario
from app.schemas.foto import (
    BuscaRostoItem,
    BuscaRostoResponse,
    FotoRead,
    FotoTipo,
    FotoUploadResponse,
    OCRPlacaResponse,
)
from app.services.foto_service import FotoService

#: Tamanho máximo de upload de imagem (10 MB).
MAX_IMAGE_SIZE = 10 * 1024 * 1024
#: MIME types permitidos para upload de imagem.
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}

# Face service é opcional — requer insightface
try:
    from app.services.face_service import FaceService
except ImportError:
    FaceService = None

# OCR service é opcional — requer easyocr
try:
    from app.services.ocr_service import OCRService
except ImportError:
    OCRService = None

router = APIRouter(prefix="/fotos", tags=["Fotos"])


@router.post("/upload", response_model=FotoUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_foto(
    request: Request,
    file: UploadFile,
    tipo: FotoTipo = Form(FotoTipo.rosto),
    pessoa_id: int | None = Form(None),
    abordagem_id: int | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
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
    if file.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato inválido. Permitidos: {', '.join(ALLOWED_IMAGE_MIMES)}",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem excede o tamanho máximo de 10 MB",
        )

    service = FotoService(db)
    foto = await service.upload_foto(
        file_bytes=file_bytes,
        filename=file.filename or "foto.jpg",
        content_type=file.content_type or "image/jpeg",
        pessoa_id=pessoa_id,
        abordagem_id=abordagem_id,
        tipo=tipo,
        latitude=latitude,
        longitude=longitude,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return FotoUploadResponse(id=foto.id, arquivo_url=foto.arquivo_url, tipo=foto.tipo)


@router.get("/pessoa/{pessoa_id}", response_model=list[FotoRead])
async def listar_fotos_pessoa(
    pessoa_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[FotoRead]:
    """Lista fotos de uma pessoa.

    Args:
        pessoa_id: ID da pessoa.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de FotoRead ordenadas por data/hora decrescente.
    """
    service = FotoService(db)
    fotos = await service.listar_por_pessoa(pessoa_id)
    return [FotoRead.model_validate(f) for f in fotos]


@router.get("/abordagem/{abordagem_id}", response_model=list[FotoRead])
async def listar_fotos_abordagem(
    abordagem_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[FotoRead]:
    """Lista fotos de uma abordagem.

    Args:
        abordagem_id: ID da abordagem.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista de FotoRead ordenadas por data/hora decrescente.
    """
    service = FotoService(db)
    fotos = await service.listar_por_abordagem(abordagem_id)
    return [FotoRead.model_validate(f) for f in fotos]


@router.post("/buscar-rosto", response_model=BuscaRostoResponse)
@limiter.limit("10/minute")
async def buscar_por_rosto(
    request: Request,
    file: UploadFile,
    top_k: int = Form(5),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
    face_service: FaceService = Depends(get_face_service),
) -> BuscaRostoResponse:
    """Busca pessoas por similaridade facial via pgvector.

    Recebe imagem com rosto, extrai embedding facial (512-dim via
    InsightFace) e busca fotos similares no banco usando distância
    cosseno com pgvector.

    Args:
        request: Objeto Request do FastAPI.
        file: Imagem com rosto para busca (multipart/form-data).
        top_k: Número máximo de resultados (padrão 5).
        db: Sessão do banco de dados.
        user: Usuário autenticado.
        face_service: Serviço InsightFace do application state.

    Returns:
        BuscaRostoResponse com lista de fotos similares e total.

    Status Code:
        200: Busca realizada (pode retornar lista vazia).
        429: Rate limit (10/min).
    """
    file_bytes = await file.read()
    service = FotoService(db)
    results = await service.buscar_por_rosto(
        image_bytes=file_bytes,
        face_service=face_service,
        top_k=top_k,
    )

    items = [
        BuscaRostoItem(
            foto_id=r["foto"].id,
            arquivo_url=r["foto"].arquivo_url,
            pessoa_id=r["foto"].pessoa_id,
            similaridade=r["similaridade"],
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

    if file.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato inválido. Permitidos: {', '.join(ALLOWED_IMAGE_MIMES)}",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Imagem excede o tamanho máximo de 10 MB",
        )
    ocr = OCRService()
    placa = ocr.extrair_placa(file_bytes)
    return OCRPlacaResponse(placa=placa, detectada=placa is not None)
