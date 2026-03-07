"""Testes unitários para as configurações da aplicação.

Valida o comportamento da classe Settings, em especial a property
s3_public_url que controla a URL pública do storage retornada ao browser.
"""

from unittest.mock import patch

from app.config import Settings


class TestS3PublicUrl:
    """Testes para a property s3_public_url da classe Settings."""

    def test_s3_public_url_retorna_s3_endpoint_quando_nao_definida(self):
        """Deve retornar S3_ENDPOINT como fallback quando S3_PUBLIC_URL não está definida.

        Garante que ambientes que não definem S3_PUBLIC_URL continuam
        funcionando — o S3_ENDPOINT é usado como URL pública.
        """
        with patch.dict(
            "os.environ",
            {
                "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
                "SECRET_KEY": "chave-secreta-para-testes",
                "ENCRYPTION_KEY": "Y2hhdmUtZmVybmV0LXBhcmEtdGVzdGVzLWFxdWktcGFkZA==",
                "S3_ENDPOINT": "http://minio:9000",
                "S3_ACCESS_KEY": "minioadmin",
                "S3_SECRET_KEY": "minioadmin",
            },
            clear=True,
        ):
            s = Settings()
            assert s.s3_public_url == "http://minio:9000"

    def test_s3_public_url_retorna_s3_public_url_quando_definida(self):
        """Deve retornar S3_PUBLIC_URL quando a variável está definida.

        Garante que em Docker Compose o browser usa http://localhost:9000
        enquanto o backend interno usa http://minio:9000 para uploads.
        """
        with patch.dict(
            "os.environ",
            {
                "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
                "SECRET_KEY": "chave-secreta-para-testes",
                "ENCRYPTION_KEY": "Y2hhdmUtZmVybmV0LXBhcmEtdGVzdGVzLWFxdWktcGFkZA==",
                "S3_ENDPOINT": "http://minio:9000",
                "S3_ACCESS_KEY": "minioadmin",
                "S3_SECRET_KEY": "minioadmin",
                "S3_PUBLIC_URL": "http://localhost:9000",
            },
            clear=True,
        ):
            s = Settings()
            assert s.s3_public_url == "http://localhost:9000"

    def test_s3_public_url_ignora_endpoint_interno_quando_public_url_definida(self):
        """Deve ignorar S3_ENDPOINT ao construir URLs públicas quando S3_PUBLIC_URL está definida.

        Confirma que o hostname interno Docker (minio) nunca vaza para URLs
        retornadas ao browser quando S3_PUBLIC_URL está configurada.
        """
        with patch.dict(
            "os.environ",
            {
                "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
                "SECRET_KEY": "chave-secreta-para-testes",
                "ENCRYPTION_KEY": "Y2hhdmUtZmVybmV0LXBhcmEtdGVzdGVzLWFxdWktcGFkZA==",
                "S3_ENDPOINT": "http://minio:9000",
                "S3_ACCESS_KEY": "minioadmin",
                "S3_SECRET_KEY": "minioadmin",
                "S3_PUBLIC_URL": "http://localhost:9000",
            },
            clear=True,
        ):
            s = Settings()
            assert "minio" not in s.s3_public_url
