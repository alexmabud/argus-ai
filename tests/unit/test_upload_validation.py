"""Testes para upload_validation: magic bytes e conversão HEIC."""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from PIL import Image


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


class TestValidarDimensoesImagem:
    """Testes para validar_dimensoes_imagem (achado #17/2026-07-13)."""

    def test_aceita_imagem_dentro_do_limite(self):
        """Imagem pequena, bem dentro do teto, deve passar sem erro."""
        from app.core.upload_validation import validar_dimensoes_imagem

        validar_dimensoes_imagem(_jpeg_bytes_sem_exif(size=(200, 100)))

    def test_rejeita_imagem_acima_do_teto_de_pixels(self):
        """Imagem cujo width*height excede max_pixels deve ser rejeitada com 400."""
        from app.core.upload_validation import validar_dimensoes_imagem

        # 100x100 = 10_000 px — usa um teto bem menor que isso para não
        # precisar gerar uma imagem real gigante só para o teste.
        with pytest.raises(HTTPException) as exc:
            validar_dimensoes_imagem(_jpeg_bytes_sem_exif(size=(100, 100)), max_pixels=9_999)
        assert exc.value.status_code == 400
        assert "pixels" in exc.value.detail.lower()

    def test_tolera_bytes_nao_decodificaveis(self):
        """Magic bytes válidos mas corpo corrompido: não rejeita aqui.

        Não há decompression bomb possível se o header nem decodifica — o
        resto do pipeline (thumbnail, correção EXIF) já tolera esse caso
        de forma estabelecida (passa os bytes originais adiante).
        """
        from app.core.upload_validation import validar_dimensoes_imagem

        validar_dimensoes_imagem(b"\xff\xd8\xff" + b"\x00" * 50)

    def test_usa_max_image_pixels_como_default(self):
        """Sem max_pixels explícito, usa a constante MAX_IMAGE_PIXELS do módulo."""
        from app.core.upload_validation import MAX_IMAGE_PIXELS, validar_dimensoes_imagem

        assert MAX_IMAGE_PIXELS > 0
        # Imagem pequena passa com o default real (não mockado).
        validar_dimensoes_imagem(_jpeg_bytes_sem_exif(size=(50, 50)))


class TestConverterHeicParaJpeg:
    """Testes para converter_heic_para_jpeg."""

    @pytest.mark.asyncio
    async def test_retorna_jpeg(self):
        """Deve retornar bytes JPEG válidos, aplicando exif_transpose antes do convert.

        exif_transpose precisa rodar ANTES de converter para RGB — a tag de
        orientação é perdida assim que o container HEIC é descartado, então
        a rotação tem que ser aplicada aos pixels enquanto o EXIF ainda existe.
        """
        from app.core.upload_validation import converter_heic_para_jpeg

        fake_img = MagicMock()
        fake_img.convert.return_value = fake_img

        def fake_save(buf, format, quality):
            buf.write(b"\xff\xd8\xff" + b"\x00" * 10)

        fake_img.save.side_effect = fake_save

        with (
            patch("app.core.upload_validation.Image") as mock_pil,
            patch("app.core.upload_validation.ImageOps") as mock_ops,
        ):
            mock_pil.open.return_value = fake_img
            mock_ops.exif_transpose.return_value = fake_img
            result = await converter_heic_para_jpeg(b"\x00\x00\x00\x18ftyp heic" + b"\x00" * 50)

        assert result[:3] == b"\xff\xd8\xff"
        mock_ops.exif_transpose.assert_called_once_with(fake_img)

    @pytest.mark.asyncio
    async def test_heic_real_com_orientacao_gira_e_troca_dimensoes(self):
        """HEIC real com orientation=6 deve sair rotacionado — 200x100 vira 100x200.

        Regressão: pillow_heif já reseta getexif() para 1 ao abrir HEIC
        (o valor real fica em img.info["original_orientation"]), então um
        exif_transpose baseado só em getexif() é um no-op para HEIC real —
        o teste mockado acima não pega isso porque simula Image/ImageOps.
        """
        pytest.importorskip("pillow_heif")
        from app.core.upload_validation import converter_heic_para_jpeg

        img = Image.new("RGB", (200, 100), color=(255, 0, 0))
        exif = img.getexif()
        exif[0x0112] = 6
        buf = io.BytesIO()
        img.save(buf, format="HEIF", exif=exif)

        result = await converter_heic_para_jpeg(buf.getvalue())

        with Image.open(io.BytesIO(result)) as out:
            assert out.size == (100, 200)

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


def _jpeg_bytes_sem_exif(size: tuple[int, int] = (20, 10)) -> bytes:
    """Gera JPEG sem tag de orientação EXIF."""
    img = Image.new("RGB", size, color=(0, 255, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _jpeg_bytes_com_orientacao(orientation: int, size: tuple[int, int] = (20, 10)) -> bytes:
    """Gera JPEG com tag EXIF Orientation (0x0112) para testar exif_transpose."""
    img = Image.new("RGB", size, color=(255, 0, 0))
    exif = img.getexif()
    exif[0x0112] = orientation
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


class TestNormalizarImagemParaReconhecimento:
    """Testes para normalizar_imagem_para_reconhecimento."""

    @pytest.mark.asyncio
    async def test_jpeg_sem_orientacao_preserva_bytes_originais(self):
        """Sem tag EXIF de orientação (ou orientação=1), retorna os bytes originais."""
        from app.core.upload_validation import normalizar_imagem_para_reconhecimento

        original = _jpeg_bytes_sem_exif()
        result = await normalizar_imagem_para_reconhecimento(original)

        assert result == original

    @pytest.mark.asyncio
    async def test_jpeg_orientacao_6_gira_e_troca_dimensoes(self):
        """Orientation=6 (90° CW) gira a imagem — 20x10 vira 10x20."""
        from app.core.upload_validation import normalizar_imagem_para_reconhecimento

        original = _jpeg_bytes_com_orientacao(6, size=(20, 10))
        result = await normalizar_imagem_para_reconhecimento(original)

        with Image.open(io.BytesIO(result)) as img:
            assert img.size == (10, 20)
            assert img.getexif().get(0x0112, 1) == 1

    @pytest.mark.asyncio
    async def test_jpeg_nao_decodificavel_preserva_bytes_originais(self):
        """Magic bytes válidos mas corpo corrompido não deve quebrar a normalização.

        Mesma tolerância que FotoService.upload_foto já aplica na geração
        de thumbnail (except UnidentifiedImageError) — a normalização não
        pode travar o upload/busca por um arquivo com corpo inválido.
        """
        from app.core.upload_validation import normalizar_imagem_para_reconhecimento

        fake_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 16
        result = await normalizar_imagem_para_reconhecimento(fake_jpeg)

        assert result == fake_jpeg

    @pytest.mark.asyncio
    async def test_jpeg_truncado_com_exif_preserva_bytes_originais(self):
        """JPEG com header/EXIF válidos mas corpo truncado não deve derrubar a request.

        Regressão: Image.open() abre normalmente (header intacto), mas
        ImageOps.exif_transpose() força a decodificação completa dos pixels
        e lança OSError (não UnidentifiedImageError) num corpo truncado —
        cenário real de upload cortado no meio em campo com sinal ruim.
        """
        from app.core.upload_validation import normalizar_imagem_para_reconhecimento

        full = _jpeg_bytes_com_orientacao(6, size=(200, 100))
        truncated = full[:-30]

        result = await normalizar_imagem_para_reconhecimento(truncated)

        assert result == truncated

    @pytest.mark.asyncio
    async def test_jpeg_orientacao_3_mantem_dimensoes(self):
        """Orientation=3 (180°) mantém proporção mas inverte os pixels."""
        from app.core.upload_validation import normalizar_imagem_para_reconhecimento

        original = _jpeg_bytes_com_orientacao(3, size=(20, 10))
        result = await normalizar_imagem_para_reconhecimento(original)

        with Image.open(io.BytesIO(result)) as img:
            assert img.size == (20, 10)

    @pytest.mark.asyncio
    async def test_heic_delega_para_converter_heic(self):
        """Bytes HEIC devem passar por converter_heic_para_jpeg, não pela correção EXIF direta."""
        from app.core.upload_validation import normalizar_imagem_para_reconhecimento

        heic_bytes = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 50
        with patch(
            "app.core.upload_validation.converter_heic_para_jpeg",
            new=AsyncMock(return_value=b"\xff\xd8\xff" + b"\x00" * 10),
        ) as mock_convert:
            result = await normalizar_imagem_para_reconhecimento(heic_bytes)

        mock_convert.assert_called_once_with(heic_bytes)
        assert result[:3] == b"\xff\xd8\xff"
