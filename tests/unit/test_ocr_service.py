"""Testes unitários para o serviço de OCR de placas veiculares.

Valida extração de placas nos padrões Mercosul e antigo,
normalização e tratamento quando nenhuma placa é detectada.
"""

from unittest.mock import MagicMock, patch


class TestOCRService:
    """Testes para OCRService."""

    def _make_service(self):
        """Cria instância de OCRService."""
        from app.services.ocr_service import OCRService

        return OCRService()

    @patch("app.services.ocr_service._reader")
    def test_extrair_placa_mercosul(self, mock_reader):
        """Deve extrair placa no padrão Mercosul (ABC1D23)."""
        mock_reader.readtext.return_value = ["ABC1D23"]

        with patch("app.services.ocr_service.Image") as mock_pil:
            mock_pil.open.return_value.convert.return_value = MagicMock()
            service = self._make_service()
            result = service.extrair_placa(b"fake_image")

        assert result == "ABC1D23"

    @patch("app.services.ocr_service._reader")
    def test_extrair_placa_antiga(self, mock_reader):
        """Deve extrair placa no padrão antigo (ABC-1234)."""
        mock_reader.readtext.return_value = ["ABC-1234"]

        with patch("app.services.ocr_service.Image") as mock_pil:
            mock_pil.open.return_value.convert.return_value = MagicMock()
            service = self._make_service()
            result = service.extrair_placa(b"fake_image")

        assert result == "ABC1234"

    @patch("app.services.ocr_service._reader")
    def test_extrair_placa_nenhuma_detectada(self, mock_reader):
        """Deve retornar None quando nenhuma placa é encontrada."""
        mock_reader.readtext.return_value = ["TEXTO ALEATORIO 123"]

        with patch("app.services.ocr_service.Image") as mock_pil:
            mock_pil.open.return_value.convert.return_value = MagicMock()
            service = self._make_service()
            result = service.extrair_placa(b"fake_image")

        assert result is None

    @patch("app.services.ocr_service._reader", None)
    def test_extrair_placa_sem_easyocr(self):
        """Deve retornar None quando EasyOCR não está instalado."""
        service = self._make_service()
        result = service.extrair_placa(b"fake_image")

        assert result is None

    def test_normalizar_placa_com_hifen(self):
        """Deve remover hifens e espaços da placa."""
        service = self._make_service()

        assert service._normalizar("ABC-1234") == "ABC1234"
        assert service._normalizar("ABC 1D23") == "ABC1D23"
        assert service._normalizar("abc-1234") == "ABC1234"

    @patch("app.services.ocr_service._reader")
    def test_mercosul_prioritario_sobre_antigo(self, mock_reader):
        """Deve priorizar padrão Mercosul quando ambos são possíveis."""
        mock_reader.readtext.return_value = ["ABC1D23"]

        with patch("app.services.ocr_service.Image") as mock_pil:
            mock_pil.open.return_value.convert.return_value = MagicMock()
            service = self._make_service()
            result = service.extrair_placa(b"fake_image")

        assert result == "ABC1D23"
