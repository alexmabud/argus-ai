"""Configurações da aplicação Argus AI.

Carrega variáveis de ambiente e fornece configuração tipada para toda a
aplicação Argus AI. Suporta recarregamento automático de arquivos .env.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações centralizadas da aplicação.

    Centraliza todos os parâmetros de configuração da aplicação Argus AI,
    incluindo banco de dados, autenticação, armazenamento, LLM, embeddings
    e conformidade LGPD. Valores são carregados de variáveis de ambiente
    via arquivo .env.

    Attributes:
        APP_NAME: Nome da aplicação.
        DEBUG: Flag de modo debug.
        API_V1_PREFIX: Prefixo de rota da API v1.
        DATABASE_URL: String de conexão PostgreSQL (async).
        DATABASE_POOL_SIZE: Tamanho do pool de conexões SQLAlchemy.
        DATABASE_MAX_OVERFLOW: Conexões extras de overflow SQLAlchemy.
        REDIS_URL: String de conexão Redis para cache e fila arq.
        SECRET_KEY: Secret para assinatura JWT (deve ser forte).
        ACCESS_TOKEN_EXPIRE_MINUTES: Tempo de vida do token de acesso (padrão 8h).
        REFRESH_TOKEN_EXPIRE_DAYS: Tempo de vida do token de refresh.
        ALGORITHM: Algoritmo JWT (HS256).
        ENCRYPTION_KEY: Chave Fernet para criptografia de campos sensíveis LGPD.
        S3_ENDPOINT: Endpoint de armazenamento S3-compatível (R2, MinIO).
        S3_ACCESS_KEY: Credencial de acesso S3.
        S3_SECRET_KEY: Credencial secreta S3.
        S3_BUCKET: Nome do bucket S3 para armazenamento de arquivos.
        S3_REGION: Região S3 (auto para Cloudflare R2).
        LLM_PROVIDER: Provedor LLM (anthropic ou ollama).
        ANTHROPIC_API_KEY: Chave de API Anthropic para modelos Claude.
        OLLAMA_BASE_URL: URL do servidor Ollama para LLM local.
        OLLAMA_MODEL: Nome do modelo Ollama.
        EMBEDDING_MODEL: Modelo SentenceTransformers para embeddings.
        EMBEDDING_DIMENSIONS: Dimensão dos vetores de embedding (384 para texto).
        EMBEDDING_CACHE_TTL: TTL do cache de embeddings em segundos.
        FACE_SIMILARITY_THRESHOLD: Limite de similaridade facial (0.0-1.0).
        GEOCODING_PROVIDER: Provedor de geocoding (nominatim ou google).
        GOOGLE_MAPS_API_KEY: Chave de API Google Maps.
        RATE_LIMIT_DEFAULT: Limite de taxa padrão (por minuto).
        RATE_LIMIT_AUTH: Limite de taxa para endpoints de auth.
        RATE_LIMIT_HEAVY: Limite de taxa para endpoints pesados de IA.
        CORS_ORIGINS: Origens CORS permitidas.
        DATA_RETENTION_DAYS: Período de retenção de dados LGPD em dias.
    """

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
    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://localhost:3000"]

    # LGPD
    DATA_RETENTION_DAYS: int = 1825  # 5 anos

    model_config = {"env_file": ".env"}


settings = Settings()
