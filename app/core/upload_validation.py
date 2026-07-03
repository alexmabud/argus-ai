"""Validação de uploads: magic bytes e leitura segura em chunks.

Garante que arquivos enviados correspondem ao tipo declarado (anti-spoofing
via magic bytes) e que uploads grandes não causam OOM (leitura em chunks
com limite de tamanho antes de carregar tudo na memória).
"""

import asyncio
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    _HEIF_AVAILABLE = True
except ImportError:
    pillow_heif = None  # type: ignore[assignment]
    _HEIF_AVAILABLE = False

from fastapi import HTTPException, UploadFile, status

#: Brands ISOBMFF que identificam HEIC/HEIF (não MP4, MOV, M4A, AVIF).
_HEIC_BRANDS = {b"heic", b"heix"}


def is_heic(file_bytes: bytes) -> bool:
    """Verifica se os bytes correspondem a uma imagem HEIC/HEIF por magic bytes.

    Usa a assinatura ftyp do container ISO Base Media File Format com
    validação da brand para distinguir HEIC de outros containers ISOBMFF.

    Args:
        file_bytes: Bytes do arquivo (mínimo 12 bytes necessário).

    Returns:
        True se os bytes correspondem a HEIC/HEIF, False caso contrário.
    """
    return len(file_bytes) >= 12 and file_bytes[4:8] == b"ftyp" and file_bytes[8:12] in _HEIC_BRANDS


#: WebP requer checagem em dois pontos do cabeçalho.
_WEBP_RIFF = b"RIFF"
_WEBP_MARKER = b"WEBP"

_PDF_MAGIC = b"%PDF"

#: Tamanho do chunk para leitura incremental (64 KB).
_CHUNK_SIZE = 65_536


def validar_magic_bytes_imagem(file_bytes: bytes) -> None:
    """Valida que o conteúdo do arquivo corresponde a uma imagem real.

    Verifica magic bytes contra JPEG, PNG, WebP e HEIC/HEIF. Previne upload de
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

    # HEIC/HEIF: bytes 4-7 contêm "ftyp" e brand nos bytes 8-11 identifica o formato
    if len(file_bytes) >= 12 and file_bytes[4:8] == b"ftyp" and file_bytes[8:12] in _HEIC_BRANDS:
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Conteúdo do arquivo não corresponde a uma imagem válida (JPEG, PNG, WebP ou HEIC)",
    )


async def converter_heic_para_jpeg(file_bytes: bytes) -> bytes:
    """Converte imagem HEIC/HEIF para JPEG de forma assíncrona.

    Delega a conversão para uma thread separada via asyncio.to_thread
    para não bloquear o event loop (imagens HEIC de iPhone podem ter
    vários MB e a decodificação Pillow é síncrona).

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
        return await asyncio.to_thread(_converter_heic_sincrono, file_bytes)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falha ao converter imagem HEIC",
        ) from exc


def _converter_heic_sincrono(file_bytes: bytes) -> bytes:
    """Executa a conversão HEIC→JPEG de forma síncrona (use via asyncio.to_thread).

    Aplica ``exif_transpose`` antes de converter para RGB — a tag de
    orientação EXIF do container HEIC seria perdida na conversão, e por
    isso a rotação precisa ser aplicada aos pixels enquanto o EXIF ainda
    existe (senão fotos de iPhone em retrato saem "deitadas" do rosto).

    O plugin HEIF do Pillow (``pillow_heif``) já reseta ``getexif()`` para
    1 ao abrir o arquivo, guardando a orientação real em
    ``img.info["original_orientation"]`` — sem isso, ``exif_transpose``
    não teria mais nenhuma tag para aplicar e viraria um no-op.

    Args:
        file_bytes: Bytes do arquivo HEIC/HEIF.

    Returns:
        Bytes JPEG convertidos, já com orientação corrigida.
    """
    img = Image.open(BytesIO(file_bytes))
    original_orientation = img.info.get("original_orientation")
    if original_orientation and original_orientation != 1:
        img.getexif()[_EXIF_ORIENTATION_TAG] = original_orientation
    img = ImageOps.exif_transpose(img).convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()


#: Tag EXIF que codifica a orientação da câmera (1 = normal, sem correção necessária).
_EXIF_ORIENTATION_TAG = 0x0112


async def normalizar_imagem_para_reconhecimento(file_bytes: bytes) -> bytes:
    """Normaliza bytes de imagem para reconhecimento facial e exibição.

    Converte HEIC/HEIF para JPEG (câmeras de iPhone) e corrige a rotação
    EXIF de fotos tiradas em retrato — sem isso, o InsightFace processa o
    rosto "deitado" e a detecção falha ou perde qualidade. HEIC já corrige
    a orientação internamente em ``converter_heic_para_jpeg`` (a rotação
    precisa ser aplicada antes de descartar o container HEIC, que carrega
    a tag de orientação).

    Args:
        file_bytes: Bytes da imagem já validados por
            ``validar_magic_bytes_imagem`` (JPEG, PNG, WebP ou HEIC/HEIF).

    Returns:
        Bytes da imagem normalizada. HEIC sempre vira JPEG; os demais
        formatos só são reencodados quando havia rotação EXIF a corrigir
        (caso contrário os bytes originais são preservados).

    Raises:
        HTTPException: 400 se for HEIC e pillow-heif estiver indisponível,
            ou se a conversão/normalização falhar.
    """
    if is_heic(file_bytes):
        return await converter_heic_para_jpeg(file_bytes)
    return await asyncio.to_thread(_corrigir_orientacao_sincrono, file_bytes)


def _corrigir_orientacao_sincrono(file_bytes: bytes) -> bytes:
    """Corrige rotação EXIF preservando os bytes originais quando não há tag.

    Se os bytes não formam uma imagem decodificável pelo Pillow (magic bytes
    válidos mas corpo corrompido ou truncado), retorna os bytes originais
    inalterados — mesma tolerância que ``FotoService.upload_foto`` já aplica
    na geração de thumbnail (``UnidentifiedImageError``/``OSError``), para
    não travar o upload/busca por um arquivo inválido. Corpo truncado com
    header/EXIF válidos lança ``OSError`` (não ``UnidentifiedImageError``)
    só quando ``exif_transpose`` força a decodificação completa dos pixels.

    Args:
        file_bytes: Bytes de imagem JPEG, PNG ou WebP.

    Returns:
        Bytes normalizados (reencodados só se havia rotação a corrigir).
    """
    try:
        with Image.open(BytesIO(file_bytes)) as img:
            orientation = img.getexif().get(_EXIF_ORIENTATION_TAG, 1)
            if orientation == 1:
                return file_bytes

            transposed = ImageOps.exif_transpose(img)
            fmt = img.format or "JPEG"
            save_kwargs = {"quality": 90} if fmt == "JPEG" else {}
            if fmt == "JPEG" and transposed.mode not in ("RGB", "L"):
                transposed = transposed.convert("RGB")

            out = BytesIO()
            transposed.save(out, format=fmt, **save_kwargs)
            return out.getvalue()
    except (UnidentifiedImageError, OSError):
        return file_bytes


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
