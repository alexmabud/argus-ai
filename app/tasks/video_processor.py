"""Task de compressão de vídeo via ffmpeg.

Processa vídeos enviados para mídias de abordagem: download do MinIO,
compressão H.264 com ffmpeg (720p, CRF 28, preset fast), substituição
no MinIO e atualização do status no banco.
"""

import asyncio
import logging
import tempfile
from pathlib import Path

from app.services.storage_service import StorageService
from app.utils.s3 import extrair_key_da_url

logger = logging.getLogger("argus")

#: MIME types que identificam vídeos para compressão.
_VIDEO_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
}


def _e_video(content_type: str) -> bool:
    """Verifica se o MIME type corresponde a um vídeo.

    Args:
        content_type: MIME type do arquivo.

    Returns:
        True se for vídeo, False caso contrário.
    """
    return content_type in _VIDEO_MIMES


def _comprimir_video_sincrono(video_bytes: bytes, ext: str = "mp4") -> bytes:
    """Comprime vídeo com ffmpeg: H.264, 720p max, CRF 28, preset fast.

    Executa ffmpeg via subprocess síncrono. Usa arquivos temporários para
    entrada e saída (ffmpeg não aceita stdin/stdout para MP4 sem -movflags).

    Args:
        video_bytes: Bytes do vídeo original.
        ext: Extensão do arquivo de entrada para detecção correta do container
            pelo ffmpeg (padrão: 'mp4').

    Returns:
        Bytes do vídeo comprimido em MP4/H.264.

    Raises:
        RuntimeError: Se ffmpeg falhar ou retornar arquivo vazio.
    """
    import subprocess

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        entrada = tmp / f"input.{ext}"
        saida = tmp / "output.mp4"

        entrada.write_bytes(video_bytes)

        cmd = [
            "ffmpeg",
            "-i",
            str(entrada),
            "-vf",
            "scale='if(gt(iw,1280),1280,iw)':'if(gt(ih,720),720,ih)':flags=lanczos",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            "-y",
            str(saida),
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            stderr = result.stderr.decode(errors="replace")
            raise RuntimeError(f"ffmpeg falhou (código {result.returncode}): {stderr[-500:]}")

        compressed = saida.read_bytes()
        if not compressed:
            raise RuntimeError("ffmpeg produziu arquivo vazio")

        return compressed


async def comprimir_video_task(ctx: dict, foto_id: int) -> dict:
    """Task arq para comprimir vídeo de mídia de abordagem.

    Pipeline:
    1. Busca Foto no banco com lock (skip_locked para evitar duplo processamento)
    2. Download dos bytes do MinIO usando a extensão da URL para o input do ffmpeg
    3. Comprime com ffmpeg em thread separada (CPU-bound)
    4. Substitui o arquivo no MinIO (mesma key)
    5. Atualiza compressao_status='done' no banco

    Em caso de falha, atualiza compressao_status='error' e mantém o original
    no MinIO para não perder o vídeo.

    Args:
        ctx: Contexto do worker arq com db_session_factory.
        foto_id: ID da Foto a comprimir.

    Returns:
        Dicionário com status e métricas de compressão.
    """
    from sqlalchemy import select

    from app.models.foto import Foto

    db_factory = ctx["db_session_factory"]
    storage = StorageService()

    logger.info("Comprimindo vídeo da foto %d", foto_id)

    async with db_factory() as db:
        try:
            result = await db.execute(
                select(Foto).where(Foto.id == foto_id).with_for_update(skip_locked=True)
            )
            foto = result.scalar_one_or_none()

            if foto is None:
                logger.error("Foto %d não encontrada para compressão", foto_id)
                return {"status": "erro", "motivo": "Foto não encontrada"}

            if foto.compressao_status in {"done", "processing"}:
                logger.info("Foto %d já em processamento/comprimida, pulando", foto_id)
                return {"status": "já_processada"}

            # Marcar como processing antes de baixar (protege contra retry duplo)
            foto.compressao_status = "processing"
            await db.commit()

            # Download do original
            key = extrair_key_da_url(foto.arquivo_url)
            video_bytes = await storage.download(key)
            tamanho_original = len(video_bytes)

            # Extrair extensão do arquivo para o ffmpeg detectar o container correto
            url_ext = (
                foto.arquivo_url.rsplit(".", 1)[-1].lower() if "." in foto.arquivo_url else "mp4"
            )
            safe_ext = url_ext if url_ext in {"mp4", "mov", "avi", "webm"} else "mp4"

            # Compressão em thread separada (CPU-bound + subprocess)
            compressed = await asyncio.to_thread(_comprimir_video_sincrono, video_bytes, safe_ext)
            tamanho_comprimido = len(compressed)

            # Substituir no MinIO (mesma key)
            await storage.upload(compressed, key, "video/mp4")

            # Atualizar status no banco
            foto.compressao_status = "done"
            await db.commit()

            reducao_pct = round((1 - tamanho_comprimido / tamanho_original) * 100, 1)
            logger.info(
                "Foto %d comprimida: %d KB → %d KB (-%s%%)",
                foto_id,
                tamanho_original // 1024,
                tamanho_comprimido // 1024,
                reducao_pct,
            )
            return {
                "status": "sucesso",
                "tamanho_original_kb": tamanho_original // 1024,
                "tamanho_comprimido_kb": tamanho_comprimido // 1024,
                "reducao_pct": reducao_pct,
            }

        except Exception:
            await db.rollback()
            # Marcar como erro sem perder o arquivo original
            try:
                async with db_factory() as db2:
                    result2 = await db2.execute(select(Foto).where(Foto.id == foto_id))
                    foto2 = result2.scalar_one_or_none()
                    if foto2:
                        foto2.compressao_status = "error"
                        await db2.commit()
            except Exception:
                pass
            logger.exception("Erro ao comprimir vídeo da foto %d", foto_id)
            return {"status": "erro", "motivo": "Erro na compressão"}
