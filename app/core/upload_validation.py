"""Validação de uploads: magic bytes e leitura segura em chunks.

Garante que arquivos enviados correspondem ao tipo declarado (anti-spoofing
via magic bytes) e que uploads grandes não causam OOM (leitura em chunks
com limite de tamanho antes de carregar tudo na memória).
"""

from io import BytesIO

from PIL import Image

try:
    import pillow_heif

    _HEIF_AVAILABLE = True
except ImportError:
    pillow_heif = None  # type: ignore[assignment]
    _HEIF_AVAILABLE = False

from fastapi import HTTPException, UploadFile, status

#: Assinaturas de magic bytes para tipos de arquivo permitidos.
_IMAGE_MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
}
#: WebP requer checagem em dois pontos do cabeçalho.
_WEBP_RIFF = b"RIFF"
_WEBP_MARKER = b"WEBP"

_PDF_MAGIC = b"%PDF"

#: Tamanho do chunk para leitura incremental (64 KB).
_CHUNK_SIZE = 65_536


def validar_magic_bytes_imagem(file_bytes: bytes) -> None:
    """Valida que o conteúdo do arquivo corresponde a uma imagem real.

    Verifica magic bytes contra JPEG, PNG e WebP. Previne upload de
    executáveis disfarçados com content_type spoofado.

    Args:
        file_bytes: Primeiros bytes do arquivo (mínimo 12 bytes).

    Raises:
        HTTPException: 400 se magic bytes não correspondem a imagem válida.
    """
    if len(file_bytes) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo muito pequeno para ser uma imagem válida",
        )

    # JPEG
    if file_bytes[:3] == b"\xff\xd8\xff":
        return
    # PNG
    if file_bytes[:4] == b"\x89PNG":
        return
    # WebP: RIFF....WEBP
    if file_bytes[:4] == _WEBP_RIFF and file_bytes[8:12] == _WEBP_MARKER:
        return

    # HEIC/HEIF: bytes 4-7 contêm "ftyp"
    if len(file_bytes) >= 8 and file_bytes[4:8] == b"ftyp":
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Conteúdo do arquivo não corresponde a uma imagem válida (JPEG, PNG ou WebP)",
    )


def converter_heic_para_jpeg(file_bytes: bytes) -> bytes:
    """Converte imagem HEIC/HEIF para JPEG.

    Usa pillow-heif para decodificar o container HEIC e re-salva
    como JPEG com qualidade 90. Chamada apenas quando o arquivo
    é detectado como HEIC/HEIF.

    Args:
        file_bytes: Bytes do arquivo HEIC/HEIF.

    Returns:
        Bytes do arquivo convertido em JPEG.

    Raises:
        HTTPException: 400 se pillow-heif não estiver disponível ou
            se a conversão falhar.
    """
    if not _HEIF_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato HEIC não suportado neste servidor",
        )
    try:
        pillow_heif.register_heif_opener()
        img = Image.open(BytesIO(file_bytes)).convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao converter imagem HEIC",
        ) from exc


def validar_magic_bytes_pdf(file_bytes: bytes) -> None:
    """Valida que o conteúdo do arquivo é um PDF real.

    Verifica se os primeiros bytes contêm a assinatura %PDF.

    Args:
        file_bytes: Primeiros bytes do arquivo (mínimo 4 bytes).

    Raises:
        HTTPException: 400 se magic bytes não correspondem a PDF.
    """
    if len(file_bytes) < 4 or not file_bytes[:4].startswith(_PDF_MAGIC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conteúdo do arquivo não corresponde a um PDF válido",
        )


async def ler_upload_com_limite(file: UploadFile, max_size: int) -> bytes:
    """Lê arquivo de upload em chunks, abortando se exceder limite.

    Previne OOM ao não carregar o arquivo inteiro antes de verificar
    tamanho. Lê em blocos de 64 KB e aborta assim que o acumulado
    excede max_size.

    Args:
        file: Arquivo de upload do FastAPI.
        max_size: Tamanho máximo permitido em bytes.

    Returns:
        Conteúdo completo do arquivo em bytes.

    Raises:
        HTTPException: 413 se o arquivo exceder max_size.
    """
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Arquivo excede o tamanho máximo de {max_size // (1024 * 1024)} MB",
            )
        chunks.append(chunk)

    return b"".join(chunks)
