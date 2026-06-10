"""Testa o fallback de MIGRATION_DATABASE_URL para DATABASE_URL.

Em dev/test o mesmo usuário (dono) faz runtime e migrations, então
MIGRATION_DATABASE_URL é opcional e cai para DATABASE_URL. Em produção,
MIGRATION_DATABASE_URL aponta para o dono (argus) enquanto DATABASE_URL
aponta para o papel só-DML (argus_app).
"""

from unittest.mock import patch

from app.config import Settings

_BASE_ENV = {
    "SECRET_KEY": "a" * 64,
    "ENCRYPTION_KEY": "Y2hhdmUtZmVybmV0LXBhcmEtdGVzdGVzLWFxdWktcGFkZA==",
    "S3_ENDPOINT": "http://minio:9000",
    "S3_ACCESS_KEY": "minioadmin",
    "S3_SECRET_KEY": "minioadmin",
    "TESTING": "1",
}


def test_migration_url_default_para_database_url() -> None:
    """Sem MIGRATION_DATABASE_URL, usa DATABASE_URL (compat dev/test)."""
    with patch.dict(
        "os.environ",
        {**_BASE_ENV, "DATABASE_URL": "postgresql://app:pwd@db/argus_db"},
        clear=True,
    ):
        s = Settings()
        assert s.effective_migration_url == "postgresql://app:pwd@db/argus_db"


def test_migration_url_explicita_tem_prioridade() -> None:
    """Com MIGRATION_DATABASE_URL definida, ela é usada para migrations."""
    with patch.dict(
        "os.environ",
        {
            **_BASE_ENV,
            "DATABASE_URL": "postgresql://app:pwd@db/argus_db",
            "MIGRATION_DATABASE_URL": "postgresql://argus:owner@db/argus_db",
        },
        clear=True,
    ):
        s = Settings()
        assert s.effective_migration_url == "postgresql://argus:owner@db/argus_db"
