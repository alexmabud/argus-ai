"""Serviço de OCR para extração de placas veiculares.

Usa EasyOCR para reconhecer texto em imagens e extrair placas
brasileiras nos padrões antigo (ABC-1234) e Mercosul (ABC1D23).
"""

import io
import logging
import re

from PIL import Image

logger = logging.getLogger("argus")

try:
    import easyocr

    _reader = easyocr.Reader(["pt", "en"], gpu=False)
    logger.info("EasyOCR carregado com sucesso")
except ImportError:
    _reader = None
    logger.warning("EasyOCR não instalado — OCR de placas indisponível")


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
        if _reader is None:
            logger.warning("EasyOCR não disponível")
            return None

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        results = _reader.readtext(
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

    def _normalizar(self, placa: str) -> str:
        """Normaliza placa removendo espaços e hifens.

        Args:
            placa: Placa bruta extraída do OCR.

        Returns:
            Placa normalizada em maiúsculas sem separadores.
        """
        return re.sub(r"[\s-]", "", placa).upper()
