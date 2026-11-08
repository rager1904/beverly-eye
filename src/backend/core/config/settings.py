from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Dict, List, Optional, Set

from pydantic import field_validator, model_validator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Values that were committed to the repository at some point. They must never
# be accepted by a production process.
_PLACEHOLDER_SECRETS = {
    "change-me-in-production",
    "change-me-in-production!!-32chars!",
    "ubuntucare-railway-demo-app-secret-replace-before-production-0001",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    APP_NAME: str = "ubuntucare"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="production", pattern="^(development|staging|production)$")
    SECRET_KEY: str = Field(default="change-me-in-production!!-32chars!", min_length=32)
    API_V1_PREFIX: str = "/api/v1"
    ROOT_PATH: str = ""

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "ubuntucare"
    POSTGRES_PASSWORD: str = "ubuntucare"
    POSTGRES_DB: str = "ubuntucare"
    POSTGRES_POOL_SIZE: int = 20
    POSTGRES_MAX_OVERFLOW: int = 10
    POSTGRES_POOL_TIMEOUT: int = 30
    POSTGRES_POOL_RECYCLE: int = 1800
    POSTGRES_ECHO: bool = False

    @property
    def database_url(self) -> str:
        if env_url := os.environ.get("DATABASE_URL"):
            return env_url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url_sync(self) -> str:
        if env_url := os.environ.get("DATABASE_URL"):
            return env_url.replace("+asyncpg", "")
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_RETRY_COUNT: int = 3

    @property
    def redis_url(self) -> str:
        pw = f":{self.REDIS_PASSWORD}" if self.REDIS_PASSWORD else ""
        return f"redis://{pw}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ------------------------------------------------------------------
    # Celery
    # ------------------------------------------------------------------
    CELERY_BROKER_URL: Optional[str] = None  # defaults to redis_url
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_EAGER_PROPAGATES: bool = True
    CELERY_WORKER_CONCURRENCY: int = 4
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: Set[str] = {"json"}

    @property
    def celery_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.redis_url

    # ------------------------------------------------------------------
    # Knowledge Graph (Neo4j)
    # ------------------------------------------------------------------
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "CHANGE_ME__neo4j"

    # ------------------------------------------------------------------
    # Vector Store (Qdrant / Weaviate)
    # ------------------------------------------------------------------
    VECTOR_STORE_TYPE: str = Field(default="qdrant", pattern="^(qdrant|weaviate)$")
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_PREFER_GRPC: bool = False
    QDRANT_HTTPS: bool = False

    @property
    def qdrant_url(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    WEAVIATE_HOST: str = "localhost"
    WEAVIATE_PORT: int = 8080
    WEAVIATE_GRPC_PORT: int = 50051
    WEAVIATE_API_KEY: Optional[str] = None
    WEAVIATE_HTTPS: bool = False

    @property
    def weaviate_url(self) -> str:
        return f"http://{self.WEAVIATE_HOST}:{self.WEAVIATE_PORT}"

    EMBEDDING_MODEL_DIMENSION: int = 768
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-base-en-v1.5"

    # ------------------------------------------------------------------
    # Open-Source Model Endpoints
    # ------------------------------------------------------------------
    LLM_ENDPOINT: str = "http://localhost:8001/v1"
    LLM_MODEL_NAME: str = "mistralai/Mistral-7B-Instruct-v0.3"
    LLM_API_KEY: Optional[str] = None
    LLM_REQUEST_TIMEOUT: int = 120
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1

    WHISPER_MODEL_SIZE: str = Field(default="large-v3", pattern="^(tiny|base|small|medium|large-v3)$")
    WHISPER_MODEL_PATH: Optional[str] = Field(default=None, description="Local path to model directory (bypasses download)")
    WHISPER_ENDPOINT: str = "http://localhost:8002/v1"
    WHISPER_DEVICE: str = Field(default="cpu", pattern="^(cpu|cuda)$")
    WHISPER_COMPUTE_TYPE: str = Field(default="int8", pattern="^(float16|int8|int4)$")

    TTS_ENDPOINT: str = "http://localhost:8003/v1"
    TTS_MODEL_NAME: str = "tts_models/en/ljspeech/tacotron2-DDC"
    TTS_DEVICE: str = "cpu"

    VAD_MODEL: str = "silero_vad"
    VAD_THRESHOLD: float = 0.5
    VAD_MIN_SPEECH_DURATION_MS: int = 250
    VAD_MIN_SILENCE_DURATION_MS: int = 500

    DIARIZATION_MODEL: str = "pyannote/speaker-diarization-3.1"
    DIARIZATION_NUM_SPEAKERS: Optional[int] = None
    DIARIZATION_DEVICE: str = "cpu"

    GUARDRAILS_ENDPOINT: str = "http://localhost:8004/v1"
    GUARDRAILS_MODEL: str = "meta-llama/LlamaGuard-7b"

    # ------------------------------------------------------------------
    # Security / JWT
    # ------------------------------------------------------------------
    JWT_ALGORITHM: str = "RS256"
    JWT_PUBLIC_KEY: Optional[str] = None
    JWT_PRIVATE_KEY_PATH: Optional[str] = None
    JWT_PUBLIC_KEY_PATH: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    KEYCLOAK_SERVER_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "ubuntucare"
    KEYCLOAK_CLIENT_ID: str = "ubuntucare-api"
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None

    # ------------------------------------------------------------------
    # Africa / Zambia specific
    # ------------------------------------------------------------------
    DEFAULT_COUNTRY_CODE: str = "ZM"
    DEFAULT_CURRENCY: str = "ZMW"
    ZMW_DECIMAL_PLACES: int = 2
    ZMW_MINOR_UNIT_FACTOR: int = 100
    SUPPORTED_COUNTRIES: List[str] = Field(default_factory=lambda: ["ZM", "ZA", "KE", "NG", "GH", "TZ", "UG", "RW"])
    SUPPORTED_LOCALES: List[str] = Field(default_factory=lambda: ["en-ZM", "en-ZA", "en-KE", "sw", "ny", "bem"])
    SUPPORTED_LANGUAGES: List[str] = Field(default_factory=lambda: ["en", "sw", "ny", "bem", "sn", "zu", "xh", "af"])
    TIMEZONE: str = "Africa/Lusaka"

    # Zambia health-system specific
    ZAMBIA_PROVINCES: List[str] = Field(default_factory=lambda: [
        "Central", "Copperbelt", "Eastern", "Luapula", "Lusaka",
        "Muchinga", "Northern", "North-Western", "Southern", "Western",
    ])
    ZAMBIA_DISTRICTS: List[str] = Field(default_factory=lambda: [
        "Chilanga", "Chongwe", "Kafue", "Luangwa", "Lusaka", "Rufunsa",
        "Siavonga", "Shibuyunji", "Chibombo", "Kabwe", "Kapiri Mposhi",
        "Mkushi", "Mumbwa", "Ngabwe", "Serenje",
    ])
    DHIS2_BASE_URL: str = "https://zm.dhis2.org"
    DHIS2_API_USER: Optional[str] = None
    DHIS2_API_PASSWORD: Optional[str] = None
    SMART_CARE_API_URL: str = "https://api.smartcare.org.zm"
    MOH_ENDPOINT: str = "https://fhir.moh.gov.zm"
    ZAMBIA_NUPI_API_URL: str = "https://nupi.moh.gov.zm/api"
    NATIONAL_ID_FORMAT: str = r"^\d{6}/\d{2}/\d$"

    # ------------------------------------------------------------------
    # Offline / Resilience
    # ------------------------------------------------------------------
    OFFLINE_MODE_ENABLED: bool = False
    OFFLINE_SYNC_INTERVAL_SECONDS: int = 300
    OFFLINE_DATA_DIR: str = str(Path("data/offline").resolve())
    OFFLINE_MAX_STORAGE_MB: int = 1024
    OFFLINE_ENCRYPT_DATA: bool = True
    OFFLINE_SYNC_BATCH_SIZE: int = 50

    # ------------------------------------------------------------------
    # Multi-tenant hospitals
    # ------------------------------------------------------------------
    MULTI_TENANT_ENABLED: bool = True
    TENANT_HEADER: str = "X-Hospital-ID"
    TENANT_ID_REGEX: str = r"^[a-f0-9\-]{36}$"
    DEFAULT_TENANT_ID: str = "00000000-0000-0000-0000-000000000000"
    MAX_HOSPITALS_PER_INSTANCE: int = 500
    HOSPITAL_CONFIG_TABLE: str = "hospitals"
    TENANT_ISOLATION: str = Field(default="shared", pattern="^(shared|schema|database)$")

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_ALLOW_HEADERS: List[str] = Field(default_factory=lambda: ["*"])

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "20/minute"
    RATE_LIMIT_AI: str = "30/minute"
    RATE_LIMIT_STORAGE: str = "redis"

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_UPLOAD_EXTENSIONS: Set[str] = Field(default_factory=lambda: {
        ".jpg", ".jpeg", ".png", ".pdf", ".dcm", ".mp3",
        ".wav", ".ogg", ".flac", ".mp4", ".webm",
    })
    UPLOAD_DIR: str = str(Path("data/uploads").resolve())

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------
    PROMETHEUS_ENABLED: bool = True
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = Field(default="production", pattern="^(development|staging|production)$")
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    LOG_FORMAT: str = Field(default="json", pattern="^(json|text)$")
    LOG_INCLUDE_TRACE: bool = True
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    PHI_REDACTION_ENABLED: bool = True
    PHI_PATTERNS: List[str] = Field(default_factory=lambda: [
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b\d{6}/\d{2}/\d\b",
        r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        r"\b\d{9,12}\b",
    ])

    # ------------------------------------------------------------------
    # LangChain / LangGraph
    # ------------------------------------------------------------------
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[str] = None
    LANGCHAIN_PROJECT: str = "ubuntucare"
    LANGGRAPH_STORE_PATH: str = str(Path("data/langgraph").resolve())
    LANGGRAPH_CHECKPOINT_INTERVAL: int = 10

    # ------------------------------------------------------------------
    # Guardrails AI
    # ------------------------------------------------------------------
    GUARDRAILS_AI_ENABLED: bool = True
    GUARDRAILS_AI_RAILS_CONFIG: str = "config/guardrails"
    GUARDRAILS_AI_LOGICAL_FALLBACK: bool = True

    # ------------------------------------------------------------------
    # EMR / FHIR
    # ------------------------------------------------------------------
    FHIR_API_VERSION: str = "R4"
    FHIR_BASE_URL: str = "http://localhost:8082/fhir"
    EMR_SYSTEM: str = Field(default="openmrs", pattern="^(openmrs|fhir)$")
    OPENMRS_BASE_URL: str = "http://localhost:8083/openmrs"

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    SMS_PROVIDER: str = Field(default="africastalking", pattern="^(africastalking|twilio)$")
    AFRICASTALKING_API_KEY: Optional[str] = None
    AFRICASTALKING_USERNAME: str = "ubuntucare"
    EMAIL_BACKEND: str = "smtp"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # ------------------------------------------------------------------
    # Medical Imaging (VNA / PACS)
    # ------------------------------------------------------------------
    DICOM_WEB_URI: str = "http://localhost:8084/dicom-web"
    ORTHANC_URL: str = "http://localhost:8042"

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        # docker-compose/.env use a comma-separated list; pydantic-settings
        # otherwise expects JSON for list fields.
        if isinstance(v, str) and not v.strip().startswith("["):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v in _PLACEHOLDER_SECRETS and os.environ.get("ENVIRONMENT", "").lower() == "production":
            raise ValueError("SECRET_KEY must be a unique secret in production")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT != "production":
            return self
        # A bare import (tests, tooling) must not fail just because the model
        # defaults to production. Enforce the rules when the deployment
        # actually supplies the production configuration.
        if not {"ENVIRONMENT", "SECRET_KEY"} & set(self.model_fields_set):
            return self
        if self.DEBUG:
            raise ValueError("DEBUG must be disabled in production")
        if self.SECRET_KEY in _PLACEHOLDER_SECRETS:
            raise ValueError("SECRET_KEY must not be a repository placeholder in production")
        if not self.CORS_ORIGINS or "*" in self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS must list explicit origins in production")
        return self

    @field_validator("JWT_PUBLIC_KEY", mode="before")
    @classmethod
    def load_public_key(cls, v: Optional[str], info) -> Optional[str]:
        if v:
            return v
        path = info.data.get("JWT_PUBLIC_KEY_PATH")
        if path and Path(path).exists():
            return Path(path).read_text()
        return v


settings = Settings()
