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

        heic_bytes = b"\x00\x00\x00\x18ftyp heic" + b"\x00" * 10
        validar_magic_bytes_imagem(heic_bytes)

    def test_aceita_heif_mif1(self):
        """Deve aceitar magic bytes HEIF (ftyp mif1)."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        heif_bytes = b"\x00\x00\x00\x18ftypMIF1" + b"\x00" * 10
        validar_magic_bytes_imagem(heif_bytes)

    def test_rejeita_executavel(self):
        """Deve rejeitar arquivo que não é imagem."""
        from app.core.upload_validation import validar_magic_bytes_imagem

        with pytest.raises(HTTPException) as exc:
            validar_magic_bytes_imagem(b"MZ\x00\x00" + b"\x00" * 10)
        assert exc.value.status_code == 400


class TestConverterHeicParaJpeg:
    """Testes para converter_heic_para_jpeg."""

    def test_retorna_jpeg(self):
        """Deve retornar bytes JPEG válidos após conversão."""
        from app.core.upload_validation import converter_heic_para_jpeg

        fake_img = MagicMock()
        fake_img.convert.return_value = fake_img

        def fake_save(buf, format, quality):
            buf.write(b"\xff\xd8\xff" + b"\x00" * 10)

        fake_img.save.side_effect = fake_save

        with patch("app.core.upload_validation.pillow_heif"), patch(
            "app.core.upload_validation.Image"
        ) as mock_pil:
            mock_pil.open.return_value = fake_img
            result = converter_heic_para_jpeg(b"\x00\x00\x00\x18ftyp heic" + b"\x00" * 50)

        assert result[:3] == b"\xff\xd8\xff"
