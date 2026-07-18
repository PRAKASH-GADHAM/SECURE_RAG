"""Application configuration using Pydantic Settings.

All configuration is loaded from environment variables.
Secrets are never hardcoded.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "SecureRAG"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Backend API
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_WORKERS: int = 4
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Database (PostgreSQL)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "secure_rag_user"
    POSTGRES_PASSWORD: str = "change_me_in_production"
    POSTGRES_DB: str = "secure_rag_db"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # ChromaDB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "secure_rag_vectors"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change_me_to_a_secure_random_string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM Configuration (OpenRouter)
    LLM_PROVIDER: str = "openrouter"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"
    OPENROUTER_HTTP_REFERER: str = "https://secure-rag.example.com"
    OPENROUTER_X_TITLE: str = "SecureRAG"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT: int = 60
    LLM_SYSTEM_PROMPT: str = ""
    LLM_STREAMING: bool = True
    LLM_MAX_RETRIES: int = 3
    LLM_CIRCUIT_BREAKER_THRESHOLD: int = 5
    LLM_CIRCUIT_BREAKER_TIMEOUT: int = 60
    LLM_CONTEXT_WINDOW: int = 8192
    LLM_OUTPUT_RESERVED_TOKENS: int = 1024

    # Embedding Configuration
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32

    # Reranking Configuration
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_DEVICE: str = "cpu"
    ENABLE_RERANKING: bool = True
    RERANK_TOP_K: int = 5
    RERANK_BATCH_SIZE: int = 16
    RERANK_SCORE_THRESHOLD: float = 0.0

    # RAG Pipeline
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 5
    MAX_CONTEXT_LENGTH: int = 4096
    RETRIEVAL_MODE: str = "hybrid"  # dense, bm25, hybrid
    RRF_K: int = 60  # Reciprocal Rank Fusion constant
    DENSE_WEIGHT: float = 0.7
    BM25_WEIGHT: float = 0.3

    # File Upload
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: str = "pdf,docx,txt,md"
    UPLOAD_DIR: str = "./uploads"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    # Cache
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 3600  # 1 hour
    EMBEDDING_CACHE_ENABLED: bool = True
    EMBEDDING_CACHE_TTL: int = 86400  # 24 hours
    RETRIEVAL_CACHE_ENABLED: bool = True
    RETRIEVAL_CACHE_TTL: int = 3600  # 1 hour
    RESPONSE_CACHE_ENABLED: bool = True
    RESPONSE_CACHE_TTL: int = 21600  # 6 hours

    # Security
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    ENCRYPTION_KEY: str = "change_me_to_a_secure_random_string"

    # AI Security Layer
    PROMPT_INJECTION_ENABLED: bool = True
    JAILBREAK_DETECTION_ENABLED: bool = True
    SECURITY_RISK_THRESHOLD: float = 0.5
    BLOCK_HIGH_RISK: bool = True
    ALLOW_ADMIN_BYPASS: bool = False
    SECURITY_MAX_PROMPT_LENGTH: int = 10000
    SECURITY_MAX_CONVERSATION_LENGTH: int = 100000

    # Guardrails (Output Protection)
    OUTPUT_PROTECTION_ENABLED: bool = True
    PII_DETECTION_ENABLED: bool = True
    PII_AUTO_REDACT: bool = False
    OUTPUT_MODERATION_ENABLED: bool = True
    MODERATION_BLOCK_ON_DETECTION: bool = True
    CITATION_VALIDATION_ENABLED: bool = True
    CITATION_MIN_COVERAGE: float = 0.5
    RESPONSE_VALIDATION_ENABLED: bool = True
    RESPONSE_MAX_LENGTH: int = 10000
    RESPONSE_MIN_LENGTH: int = 10

    # Monitoring & Evaluation
    MONITORING_ENABLED: bool = True
    PROFILING_ENABLED: bool = False
    PROFILING_SAMPLE_RATE: float = 0.1
    TRACING_ENABLED: bool = True
    TRACING_SAMPLE_RATE: float = 1.0
    BENCHMARK_ITERATIONS: int = 100
    BENCHMARK_WARMUP: int = 10

    # Evaluation
    EVALUATION_ENABLED: bool = True
    EVALUATION_AUTO_RUN: bool = False
    SLA_LATENCY_THRESHOLD_MS: float = 1000.0

    @property
    def database_url(self) -> str:
        """Build async database URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        """Build synchronous database URL (for Alembic)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def redis_url(self) -> str:
        """Build Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_file_types_list(self) -> list[str]:
        """Parse allowed file types into a list."""
        return [ft.strip().lower() for ft in self.ALLOWED_FILE_TYPES.split(",") if ft.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size to bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings: Application settings instance.
    """
    return Settings()
