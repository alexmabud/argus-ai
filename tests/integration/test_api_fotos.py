"""Testes de integração da API de Fotos.

Testa endpoints de upload de fotos, busca por similaridade
facial e extração de placa via OCR, e download com marca d'água.
"""

import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.foto import Foto


class TestUploadFoto:
    """Testes do endpoint POST /api/v1/fotos/upload."""

    @patch("app.services.foto_service.StorageService")
    async def test_upload_foto_retorna_201(
        self,
        mock_storage_cls,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Deve fazer upload de foto e retornar 201.

        Args:
            mock_storage_cls: Mock do StorageService.
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        mock_storage = MagicMock()
        mock_storage.upload = AsyncMock(return_value="https://s3.example.com/fotos/test.jpg")
        mock_storage.generate_key = MagicMock(return_value="fotos/test.jpg")
        mock_storage_cls.return_value = mock_storage
        mock_storage_cls.get = MagicMock(return_value=mock_storage)

        response = await client.post(
            "/api/v1/fotos/upload",
            files={"file": ("test.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 16, "image/jpeg")},
            data={"tipo": "rosto"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "arquivo_url" in data
        assert data["tipo"] == "rosto"

    async def test_upload_foto_sem_auth_retorna_401(self, client: AsyncClient):
        """Deve retornar 401 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/fotos/upload",
            files={"file": ("test.jpg", b"fake", "image/jpeg")},
            data={"tipo": "rosto"},
        )
        assert response.status_code == 401


class TestBuscarRosto:
    """Testes do endpoint POST /api/v1/fotos/buscar-rosto."""

    async def test_buscar_rosto_sem_auth_retorna_401(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/fotos/buscar-rosto",
            files={"file": ("face.jpg", b"fake", "image/jpeg")},
        )
        assert response.status_code == 401


class TestOCRPlaca:
    """Testes do endpoint POST /api/v1/fotos/ocr-placa."""

    async def test_ocr_placa_sem_auth_retorna_401(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/fotos/ocr-placa",
            files={"file": ("placa.jpg", b"fake", "image/jpeg")},
        )
        assert response.status_code == 401


def _jpeg_bytes() -> bytes:
    """Gera bytes de imagem JPEG mínima para testes de download.

    Returns:
        Bytes de uma imagem JPEG 100x100 sólida.
    """
    buf = io.BytesIO()
    Image.new("RGB", (100, 100), (80, 80, 80)).save(buf, format="JPEG")
    return buf.getvalue()


class TestDownloadMidia:
    """Testes do endpoint GET /api/v1/fotos/{id}/download."""

    @pytest.mark.asyncio
    async def test_download_imagem_retorna_marcada(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        usuario,
    ):
        """Download de imagem deve retornar bytes com marca queimada (≠ original).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            db_session: Sessão assíncrona do banco de dados.
            usuario: Fixture de usuário autenticado.
        """
        original = _jpeg_bytes()

        foto = Foto(
            arquivo_url=f"/storage/{settings.S3_BUCKET}/fotos/prova.jpg",
            tipo="abordagem",
            data_hora=datetime.now(),
            pessoa_id=None,
            guarnicao_id=usuario.guarnicao_id,
        )
        db_session.add(foto)
        await db_session.flush()

        from botocore.exceptions import ClientError

        def _nosuchkey():
            return ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

        mock_storage = AsyncMock()
        # 1ª chamada (cache wm/) → miss; 2ª (original) → bytes reais
        mock_storage.download_with_meta = AsyncMock(
            side_effect=[_nosuchkey(), (original, "image/jpeg")]
        )
        mock_storage.upload = AsyncMock()

        with patch("app.services.watermark_service.StorageService") as mock_cls:
            mock_cls.get = MagicMock(return_value=mock_storage)
            resp = await client.get(
                f"/api/v1/fotos/{foto.id}/download",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.content != original  # marca queimada nos pixels
        assert resp.headers["content-disposition"].startswith('attachment; filename="')

    @pytest.mark.asyncio
    async def test_download_pdf_nao_marcado(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        usuario,
    ):
        """Download de PDF não recebe marca queimada (passthrough).

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            db_session: Sessão assíncrona do banco de dados.
            usuario: Fixture de usuário autenticado.
        """
        pdf_bytes = b"%PDF-1.7 fake content"

        foto = Foto(
            arquivo_url=f"/storage/{settings.S3_BUCKET}/pdfs/laudo.pdf",
            tipo="pdf",
            data_hora=datetime.now(),
            pessoa_id=None,
            guarnicao_id=usuario.guarnicao_id,
        )
        db_session.add(foto)
        await db_session.flush()

        mock_storage = AsyncMock()
        mock_storage.download = AsyncMock(return_value=pdf_bytes)

        with patch("app.api.v1.fotos.StorageService") as mock_cls:
            mock_cls.get = MagicMock(return_value=mock_storage)
            resp = await client.get(
                f"/api/v1/fotos/{foto.id}/download",
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert resp.content == pdf_bytes  # PDF inalterado
