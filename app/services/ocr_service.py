"""Serviço de OCR para extração de placas veiculares.

Usa EasyOCR para reconhecer texto em imagens e extrair placas
brasileiras nos padrões antigo (ABC-1234) e Mercosul (ABC1D23).
"""

import asyncio
import io
import logging
import re

from PIL import Image

logger = logging.getLogger("argus")

#: Reader EasyOCR carregado sob demanda (lazy) para evitar startup lento.
_reader = None
_reader_loaded = False


def _get_reader():
    """Retorna reader EasyOCR, carregando na primeira chamada (lazy init).

    Returns:
        Reader EasyOCR ou None se indisponível.
    """
    global _reader, _reader_loaded
    if _reader_loaded:
        return _reader
    try:
        import easyocr

        _reader = easyocr.Reader(["pt", "en"], gpu=False)
        logger.info("EasyOCR carregado com sucesso")
    except Exception as exc:
        _reader = None
        logger.warning("EasyOCR indisponível: %s", exc)
    _reader_loaded = True
    return _reader


class OCRService:
    """Serviço de OCR para extração de placas veiculares brasileiras.

    Usa EasyOCR com modelos pt/en para reconhecer texto em imagens
    e aplicar regex para identificar placas nos padrões brasileiro
    antigo (ABC-1234) e Mercosul (ABC1D23).

    Attributes:
        PLACA_MERCOSUL: Regex para padrão Mercosul.
        PLACA_ANTIGA: Regex para padrão antigo.
    """

    PLACA_MERCOSUL = re.compile(r"[A-Z]{3}\d[A-Z]\d{2}")
    PLACA_ANTIGA = re.compile(r"[A-Z]{3}\s?-?\s?\d{4}")

    def extrair_placa(self, image_bytes: bytes) -> str | None:
        """Extrai placa veicular de uma imagem via OCR.

        Processa a imagem com EasyOCR, filtrando apenas caracteres
        relevantes para placas. Tenta match com padrão Mercosul
        primeiro, depois antigo.

        Args:
            image_bytes: Conteúdo da imagem em bytes.

        Returns:
            Placa normalizada (ex: "ABC1D23") ou None se não encontrada.
        """
        reader = _get_reader()
        if reader is None:
            logger.warning("EasyOCR não disponível")
            return None

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = reader.readtext(
            img,
            detail=0,
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ",
        )

        for text in results:
            text = text.upper().strip()

            # Tentar Mercosul primeiro (padrão mais recente)
            match = self.PLACA_MERCOSUL.search(text)
            if match:
                return self._normalizar(match.group())

            # Tentar padrão antigo
            match = self.PLACA_ANTIGA.search(text)
            if match:
                return self._normalizar(match.group())

        return None

    async def extrair_placa_async(self, image_bytes: bytes) -> str | None:
        """Wrapper async para extrair_placa via thread pool.

        Executa a inferência OCR (CPU-bound) em thread separada para
        não bloquear o event loop do asyncio.

        Args:
            image_bytes: Conteúdo da imagem em bytes.

        Returns:
            Placa normalizada ou None se não encontrada.
        """
        return await asyncio.to_thread(self.extrair_placa, image_bytes)

    def _normalizar(self, placa: str) -> str:
        """Normaliza placa removendo espaços e hifens.

        Args:
            placa: Placa bruta extraída do OCR.

        Returns:
            Placa normalizada em maiúsculas sem separadores.
        """
        return re.sub(r"[\s-]", "", placa).upper()
