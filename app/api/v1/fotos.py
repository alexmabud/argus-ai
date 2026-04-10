"""Router de upload, listagem e busca de fotos.

Fornece endpoints para upload de fotos para S3/R2, listagem
por pessoa ou abordagem, busca por similaridade facial
(pgvector 512-dim) e extração de placas via OCR (EasyOCR).
"""

import logging
import re

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
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
from app.services.abordagem_service import AbordagemService
from app.services.audit_service import AuditService
from app.services.foto_service import FotoService
from app.services.pessoa_service import PessoaService
from app.services.storage_service import StorageService

logger = logging.getLogger("argus")

#: Tamanho máximo de upload de imagem (10 MB).
MAX_IMAGE_SIZE = 10 * 1024 * 1024
#: MIME types permitidos para upload de imagem.
ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
#: Tamanho máximo de upload de mídia (10 MB — apenas fotos e PDF).
MAX_MIDIA_SIZE = 10 * 1024 * 1024
#: MIME types permitidos para upload de mídia (vídeo removido).
ALLOWED_MIDIA_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}

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


def _sanitizar_filename(filename: str) -> str:
    """Sanitiza nome de arquivo para uso em Content-Disposition.

    Remove path traversal, substitui espaços por underscore e
    garante que o resultado não seja vazio.

    Args:
        filename: Nome original do arquivo.

    Returns:
        Nome sanitizado seguro para cabeçalho HTTP.
    """
    # Remover qualquer componente de path
    name = filename.replace("\\", "/").split("/")[-1]
    # Substituir espaços por underscore
    name = name.replace(" ", "_")
    # Remover caracteres não seguros (manter alfanuméricos, ponto, hífen, underscore)
    name = re.sub(r"[^\w.\-]", "", name)
    return name or "midia"


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
            await redis_pool.aclose()
        except Exception:
            logger.warning("Worker offline — face da foto %d será processada depois", foto.id)

    return FotoUploadResponse(id=foto.id, arquivo_url=foto.arquivo_url, tipo=foto.tipo)


@router.get("/pessoa/{pessoa_id}", response_model=list[FotoRead])
@limiter.limit("30/minute")
async def listar_fotos_pessoa(
    request: Request,
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
@limiter.limit("30/minute")
async def listar_fotos_abordagem(
    request: Request,
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


@router.post(
    "/midias",
    response_model=FotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def upload_midia_abordagem(
    request: Request,
    file: UploadFile,
    abordagem_id: int = Form(..., gt=0),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> FotoUploadResponse:
    """Faz upload de mídia (foto, vídeo ou PDF) vinculada a uma abordagem.

    Aceita imagens, vídeos (MP4, MOV, AVI, WebM) e PDFs até 200 MB.
    Usado para registrar autorizações de entrada em residência,
    vídeos de ocorrência e outros documentos operacionais.
    O tipo é fixado em FotoTipo.midia_abordagem automaticamente.

    Args:
        request: Objeto Request do FastAPI.
        file: Arquivo de mídia (multipart/form-data).
        abordagem_id: ID da abordagem a vincular (obrigatório, > 0).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        FotoUploadResponse com id, url e tipo="midia_abordagem".

    Raises:
        HTTPException 400: Formato de arquivo não permitido.
        HTTPException 500: Erro no storage.

    Status Code:
        201: Mídia enviada.
        429: Rate limit (20/min).
    """
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIDIA_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Formato não permitido: {content_type}. "
                "Aceitos: imagens, vídeos MP4/MOV/AVI/WebM e PDF."
            ),
        )

    file_bytes = await ler_upload_com_limite(file, MAX_MIDIA_SIZE)

    # Valida magic bytes para imagens (anti-spoofing via Content-Type).
    # Vídeos e PDF não possuem validador de magic bytes implementado.
    _image_mimes = {"image/jpeg", "image/png", "image/webp"}
    if content_type in _image_mimes:
        validar_magic_bytes_imagem(file_bytes)

    filename = file.filename or "midia"

    # Verificar que a abordagem pertence à guarnição do usuário (anti cross-tenant)
    if user.guarnicao_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem guarnição atribuída",
        )
    await AbordagemService(db).buscar_por_id(abordagem_id, user.guarnicao_id)

    service = FotoService(db)
    try:
        foto = await service.upload_foto(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            pessoa_id=None,
            abordagem_id=abordagem_id,
            veiculo_id=None,
            tipo=FotoTipo.midia_abordagem,
            latitude=None,
            longitude=None,
            user_id=user.id,
            guarnicao_id=user.guarnicao_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            max_size=MAX_MIDIA_SIZE,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao fazer upload. Verifique o storage e tente novamente.",
        ) from exc

    audit = AuditService(db)
    await audit.log(
        usuario_id=user.id,
        acao="CREATE",
        recurso="midia_abordagem",
        recurso_id=foto.id,
        detalhes={"abordagem_id": abordagem_id, "content_type": content_type},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return FotoUploadResponse(id=foto.id, arquivo_url=foto.arquivo_url, tipo=foto.tipo)


@router.get("/{foto_id}/download")
@limiter.limit("30/minute")
async def download_midia(
    request: Request,
    foto_id: int,
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> StreamingResponse:
    """Faz download forçado de mídia ou PDF vinculado a uma abordagem.

    Busca a Foto no banco, valida que pertence à guarnição do usuário,
    baixa os bytes do MinIO e retorna com Content-Disposition: attachment
    para forçar o download no browser em vez de abrir inline.

    Args:
        request: Objeto Request do FastAPI.
        foto_id: ID da Foto a baixar.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        StreamingResponse com o arquivo e header de download.

    Raises:
        HTTPException 404: Foto não encontrada ou deletada.
        HTTPException 403: Foto não pertence à guarnição do usuário.
        HTTPException 500: Erro ao baixar do storage.

    Status Code:
        200: Arquivo retornado com Content-Disposition: attachment.
        429: Rate limit (30/min).
    """
    from sqlalchemy import select

    from app.models.foto import Foto
    from app.utils.s3 import extrair_key_da_url

    # Buscar foto (respeitando soft delete via ativo=True)
    result = await db.execute(
        select(Foto).where(Foto.id == foto_id, Foto.ativo == True)  # noqa: E712
    )
    foto = result.scalar_one_or_none()

    if foto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mídia não encontrada")

    # Validar tenant — foto deve pertencer à guarnição do usuário
    if foto.guarnicao_id != user.guarnicao_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a esta mídia",
        )

    # Determinar nome do arquivo a partir da URL armazenada
    url_filename = foto.arquivo_url.split("/")[-1]
    safe_filename = _sanitizar_filename(url_filename)

    # Determinar content-type a partir da extensão
    ext = safe_filename.rsplit(".", 1)[-1].lower() if "." in safe_filename else ""
    content_type_map = {
        "mp4": "video/mp4",
        "mov": "video/quicktime",
        "avi": "video/x-msvideo",
        "webm": "video/webm",
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    media_type = content_type_map.get(ext, "application/octet-stream")

    # Download dos bytes do MinIO
    try:
        storage = StorageService()
        key = extrair_key_da_url(foto.arquivo_url)
        file_bytes = await storage.download(key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao baixar o arquivo do storage.",
        ) from exc

    return StreamingResponse(
        iter([file_bytes]),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )
