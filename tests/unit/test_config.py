"""Testes unitários para as configurações da aplicação.

Valida o comportamento da classe Settings, em especial a property
s3_public_url que controla a URL pública do storage retornada ao browser.
"""

from unittest.mock import patch

import pytest

from app.config import Settings


_BASE_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
    "ENCRYPTION_KEY": "Y2hhdmUtZmVybmV0LXBhcmEtdGVzdGVzLWFxdWktcGFkZA==",
    "S3_ENDPOINT": "http://minio:9000",
    "S3_ACCESS_KEY": "minioadmin",
    "S3_SECRET_KEY": "minioadmin",
    "TESTING": "1",
}


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
                "TESTING": "1",
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
                "TESTING": "1",
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
                "TESTING": "1",
            },
            clear=True,
        ):
            s = Settings()
            assert "minio" not in s.s3_public_url


class TestCpfHmacKey:
    """Testes para separação de SECRET_KEY (JWT) e CPF_HMAC_KEY (HMAC LGPD)."""

    def test_jwt_secret_and_cpf_hmac_are_separate(self):
        """Quando CPF_HMAC_KEY for definida, deve ser distinta da SECRET_KEY.

        Vazamento de uma das chaves não pode comprometer a outra função:
        SECRET_KEY assina JWT; CPF_HMAC_KEY pepper o hash de busca de CPF.
        """
        env = dict(_BASE_ENV)
        env["SECRET_KEY"] = "a" * 64
        env["CPF_HMAC_KEY"] = "b" * 64
        with patch.dict("os.environ", env, clear=True):
            s = Settings()
            assert s.SECRET_KEY != s.CPF_HMAC_KEY
            assert len(s.CPF_HMAC_KEY) >= 32

    def test_cpf_hmac_key_falls_back_to_secret_key_when_unset(self):
        """Quando CPF_HMAC_KEY não estiver definida, deve usar SECRET_KEY como fallback.

        Preserva compatibilidade com ambientes existentes onde apenas
        SECRET_KEY foi rotacionada — hashes antigos continuam batendo.
        """
        env = dict(_BASE_ENV)
        env["SECRET_KEY"] = "a" * 64
        with patch.dict("os.environ", env, clear=True):
            s = Settings()
            assert s.CPF_HMAC_KEY == s.SECRET_KEY

    def test_cpf_hmac_key_rejeita_valor_curto(self):
        """CPF_HMAC_KEY explicitamente definida deve ter pelo menos 32 caracteres."""
        env = dict(_BASE_ENV)
        env["SECRET_KEY"] = "a" * 64
        env["CPF_HMAC_KEY"] = "curto"
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match="CPF_HMAC_KEY"):
                Settings()
