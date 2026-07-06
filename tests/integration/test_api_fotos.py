"""Testes de integração da API de Fotos.

Testa endpoints de upload de fotos, busca por similaridade
facial e extração de placa via OCR, e download com marca d'água.
"""

import io
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db
from app.dependencies import get_face_service
from app.main import create_app
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

    @pytest.fixture
    async def client_face(self, db_session: AsyncSession):
        """Cliente com get_db e get_face_service sobrescritos.

        Expõe o mock de FaceService para o teste controlar o retorno de
        extrair_embedding sem depender do modelo InsightFace real.

        Args:
            db_session: Sessão do banco de testes.

        Yields:
            tuple[AsyncClient, MagicMock]: cliente HTTP e o mock de FaceService.
        """
        app = create_app()
        mock_face = MagicMock()

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_face_service] = lambda: mock_face
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="https://test") as ac:
            yield ac, mock_face
        app.dependency_overrides.clear()

    async def test_buscar_rosto_retorna_200_com_resultado(
        self,
        client_face,
        auth_headers: dict,
        pessoa,
        db_session: AsyncSession,
    ):
        """Deve extrair embedding e retornar a pessoa com foto similar.

        Args:
            client_face: Cliente com face_service mockado.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa dona da foto de referência.
            db_session: Sessão do banco de testes.
        """
        ac, mock_face = client_face
        embedding = [1.0] + [0.0] * 511
        mock_face.extrair_embedding.return_value = embedding

        db_session.add(
            Foto(
                arquivo_url="/storage/x/rosto.jpg",
                tipo="rosto",
                data_hora=datetime.now(),
                pessoa_id=pessoa.id,
                embedding_face=embedding,
                face_processada=True,
            )
        )
        await db_session.flush()

        response = await ac.post(
            "/api/v1/fotos/buscar-rosto",
            files={"file": ("face.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 16, "image/jpeg")},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["resultados"][0]["pessoa_id"] == pessoa.id
        mock_face.extrair_embedding.assert_called_once()

    async def test_buscar_rosto_heic_e_convertido_antes_do_embedding(
        self,
        client_face,
        auth_headers: dict,
    ):
        """HEIC deve ser convertido para JPEG antes de chegar no FaceService.

        Regressão: buscar-rosto aceitava HEIC nos magic bytes mas não
        convertia antes de extrair o embedding — diferente do endpoint de
        upload, que já convertia.

        Args:
            client_face: Cliente com face_service mockado.
            auth_headers: Headers com Bearer token válido.
        """
        pytest.importorskip("pillow_heif")
        buf = io.BytesIO()
        Image.new("RGB", (400, 300), (70, 90, 110)).save(buf, format="HEIF")
        heic_bytes = buf.getvalue()

        ac, mock_face = client_face
        mock_face.extrair_embedding.return_value = None

        response = await ac.post(
            "/api/v1/fotos/buscar-rosto",
            files={"file": ("face.heic", heic_bytes, "image/heic")},
            headers=auth_headers,
        )

        assert response.status_code == 200
        called_bytes = mock_face.extrair_embedding.call_args[0][0]
        assert called_bytes[:3] == b"\xff\xd8\xff"


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


class TestDeletarFoto:
    """Testes do endpoint DELETE /api/v1/fotos/{foto_id}."""

    @patch("app.services.foto_service.StorageService")
    async def test_deletar_foto_retorna_204(
        self,
        mock_storage_cls,
        client: AsyncClient,
        auth_headers: dict,
        pessoa,
    ):
        """Deve desativar a foto (204) e removê-la da listagem da pessoa.

        Args:
            mock_storage_cls: Mock do StorageService.
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
            pessoa: Fixture de pessoa dona da foto enviada.
        """
        mock_storage = MagicMock()
        mock_storage.upload = AsyncMock(return_value="https://s3.example.com/fotos/test.jpg")
        mock_storage.generate_key = MagicMock(return_value="fotos/test.jpg")
        mock_storage_cls.return_value = mock_storage
        mock_storage_cls.get = MagicMock(return_value=mock_storage)

        upload_resp = await client.post(
            "/api/v1/fotos/upload",
            files={"file": ("teste.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 16, "image/jpeg")},
            data={"tipo": "evidencia", "pessoa_id": str(pessoa.id)},
            headers=auth_headers,
        )
        foto_id = upload_resp.json()["id"]

        response = await client.delete(f"/api/v1/fotos/{foto_id}", headers=auth_headers)
        assert response.status_code == 204

        # Foto some da listagem da pessoa
        listagem = await client.get(f"/api/v1/fotos/pessoa/{pessoa.id}", headers=auth_headers)
        assert all(f["id"] != foto_id for f in listagem.json())

    async def test_deletar_foto_inexistente_retorna_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Deve retornar 404 ao tentar desativar uma foto que não existe.

        Args:
            client: Cliente HTTP assincrónico.
            auth_headers: Headers com Bearer token válido.
        """
        response = await client.delete("/api/v1/fotos/99999", headers=auth_headers)
        assert response.status_code == 404

    async def test_deletar_foto_sem_auth_retorna_401(self, client: AsyncClient):
        """Deve retornar 401 sem autenticação.

        Args:
            client: Cliente HTTP assincrónico.
        """
        response = await client.delete("/api/v1/fotos/1")
        assert response.status_code == 401
