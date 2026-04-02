"""Testes para upload_validation: magic bytes e conversão HEIC."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestValidarMagicBytesImagem:
    """Testes para validar_magic_bytes_imagem."""

    def test_aceita_jpeg(self):
        """Deve aceitar magic bytes JPEG."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        validar_magic_bytes_imagem(b"\xff\xd8\xff" + b"\x00" * 10)

    def test_aceita_png(self):
        """Deve aceitar magic bytes PNG."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        validar_magic_bytes_imagem(b"\x89PNG" + b"\x00" * 10)

    def test_aceita_webp(self):
        """Deve aceitar magic bytes WebP."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        validar_magic_bytes_imagem(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 2)

    def test_aceita_heic(self):
        """Deve aceitar magic bytes HEIC (ftyp heic)."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        heic_bytes = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 10
        validar_magic_bytes_imagem(heic_bytes)

    def test_aceita_heic_brand_heix(self):
        """Deve aceitar magic bytes HEIC com brand heix (variante Apple)."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        heic_bytes = b"\x00\x00\x00\x18ftypheix" + b"\x00" * 10
        validar_magic_bytes_imagem(heic_bytes)

    def test_rejeita_mif1_brand(self):
        """Deve rejeitar container genérico ISOBMFF com brand mif1."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        with pytest.raises(HTTPException) as exc:
            validar_magic_bytes_imagem(b"\x00\x00\x00\x18ftypMIF1" + b"\x00" * 10)
        assert exc.value.status_code == 400

    def test_is_heic_detecta_por_magic_bytes(self):
        """is_heic deve detectar HEIC pelos magic bytes independente do content_type."""
        from app.core.upload_validation import is_heic

        assert is_heic(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 10) is True
        assert is_heic(b"\xff\xd8\xff" + b"\x00" * 10) is False
        assert is_heic(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 10) is False

    def test_rejeita_mp4_com_ftyp(self):
        """Deve rejeitar MP4 mesmo com magic bytes ftyp (não é HEIC)."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        # MP4 tem ftyp com brand "mp42" ou "isom"
        mp4_bytes = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 10
        with pytest.raises(HTTPException) as exc:
            validar_magic_bytes_imagem(mp4_bytes)
        assert exc.value.status_code == 400

    def test_rejeita_arquivo_pequeno(self):
        """Deve rejeitar arquivo com menos de 12 bytes."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        with pytest.raises(HTTPException) as exc:
            validar_magic_bytes_imagem(b"\xff\xd8\xff")
        assert exc.value.status_code == 400

    def test_rejeita_executavel(self):
        """Deve rejeitar arquivo que não é imagem."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        with pytest.raises(HTTPException) as exc:
            validar_magic_bytes_imagem(b"MZ\x00\x00" + b"\x00" * 10)
        assert exc.value.status_code == 400


class TestConverterHeicParaJpeg:
    """Testes para converter_heic_para_jpeg."""

    @pytest.mark.asyncio
    async def test_retorna_jpeg(self):
        """Deve retornar bytes JPEG válidos após conversão."""
        from app.core.upload_validation import converter_heic_para_jpeg

        fake_img = MagicMock()
        fake_img.convert.return_value = fake_img

        def fake_save(buf, format, quality):
            buf.write(b"\xff\xd8\xff" + b"\x00" * 10)

        fake_img.save.side_effect = fake_save

        with patch("app.core.upload_validation.Image") as mock_pil:
            mock_pil.open.return_value = fake_img
            result = await converter_heic_para_jpeg(b"\x00\x00\x00\x18ftyp heic" + b"\x00" * 50)

        assert result[:3] == b"\xff\xd8\xff"

    @pytest.mark.asyncio
    async def test_lanca_erro_se_heif_indisponivel(self):
        """Deve lançar HTTPException 400 se pillow_heif não estiver disponível."""
        import app.core.upload_validation as mod

        original = mod._HEIF_AVAILABLE
        try:
            mod._HEIF_AVAILABLE = False
            from app.core.upload_validation import converter_heic_para_jpeg

            with pytest.raises(HTTPException) as exc:
                await converter_heic_para_jpeg(b"\x00" * 20)
            assert exc.value.status_code == 400
        finally:
            mod._HEIF_AVAILABLE = original
