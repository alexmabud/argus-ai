"""Router de upload e listagem de fotos.

Fornece endpoints para upload de fotos para S3/R2 e listagem
por pessoa ou abordagem associada.
"""

from fastapi import APIRouter, Depends, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.database.session import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.foto import FotoRead, FotoUploadResponse
from app.services.foto_service import FotoService

router = APIRouter(prefix="/fotos", tags=["Fotos"])


@router.post("/upload", response_model=FotoUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def upload_foto(
    request: Request,
    file: UploadFile,
    tipo: str = Form("rosto"),
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
        tipo: Tipo de foto ("rosto", "corpo", "placa").
        pessoa_id: ID da pessoa associada (opcional).
        abordagem_id: ID da abordagem associada (opcional).
        latitude: Latitude GPS da captura (opcional).
        longitude: Longitude GPS da captura (opcional).
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        FotoUploadResponse com id, url e tipo.

    Status Code:
        201: Foto enviada.
        429: Rate limit (10/min).
    """
    file_bytes = await file.read()
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
