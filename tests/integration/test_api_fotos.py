"""Testes de integração da API de Fotos.

Testa endpoints de upload de fotos, busca por similaridade
facial e extração de placa via OCR.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient


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
        mock_storage._generate_key = MagicMock(return_value="fotos/test.jpg")
        mock_storage_cls.return_value = mock_storage

        response = await client.post(
            "/api/v1/fotos/upload",
            files={"file": ("test.jpg", b"fake_image_data", "image/jpeg")},
            data={"tipo": "cena"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "arquivo_url" in data
        assert data["tipo"] == "cena"

    async def test_upload_foto_sem_auth_retorna_403(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/fotos/upload",
            files={"file": ("test.jpg", b"fake", "image/jpeg")},
            data={"tipo": "cena"},
        )
        assert response.status_code == 403


class TestBuscarRosto:
    """Testes do endpoint POST /api/v1/fotos/buscar-rosto."""

    async def test_buscar_rosto_sem_auth_retorna_403(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/fotos/buscar-rosto",
            files={"file": ("face.jpg", b"fake", "image/jpeg")},
        )
        assert response.status_code == 403


class TestOCRPlaca:
    """Testes do endpoint POST /api/v1/fotos/ocr-placa."""

    async def test_ocr_placa_sem_auth_retorna_403(self, client: AsyncClient):
        """Deve retornar 403 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.post(
            "/api/v1/fotos/ocr-placa",
            files={"file": ("placa.jpg", b"fake", "image/jpeg")},
        )
        assert response.status_code == 403
