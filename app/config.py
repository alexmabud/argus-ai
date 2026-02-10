from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Argus AI"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas (turno completo)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # Encryption (LGPD)
    ENCRYPTION_KEY: str  # Fernet key para campos sensíveis

    # Storage
    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str = "argus"
    S3_REGION: str = "auto"

    # LLM
    LLM_PROVIDER: str = "anthropic"  # anthropic | ollama
    ANTHROPIC_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-r1:8b"

    # Embeddings
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSIONS: int = 384
    EMBEDDING_CACHE_TTL: int = 3600  # 1h cache de embeddings de busca

    # Face Recognition
    FACE_SIMILARITY_THRESHOLD: float = 0.6

    # Geocoding
    GEOCODING_PROVIDER: str = "nominatim"  # nominatim (free) | google
    GOOGLE_MAPS_API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "60/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_HEAVY: str = "10/minute"  # endpoints de IA

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # LGPD
    DATA_RETENTION_DAYS: int = 1825  # 5 anos

    model_config = {"env_file": ".env"}


settings = Settings()
