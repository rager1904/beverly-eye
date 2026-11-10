import os

from pydantic import model_validator
from pydantic_settings import BaseSettings

_PLACEHOLDER_SECRETS = {
    "change-me-in-production",
    "change-me-in-production!!-32chars!",
    "ubuntucare-railway-demo-app-secret-replace-before-production-0001",
}


class Settings(BaseSettings):
    app_name: str = "UbuntuCare Zambia"
    debug: bool = False
    log_level: str = "info"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ubuntucare"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "RS256"
    jwt_expire_minutes: int = 480
    uvicorn_workers: int = 4
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    smartcare_api_url: str = ""
    smartcare_api_key: str = ""

    africas_talking_api_key: str = ""
    africas_talking_username: str = ""
    africas_talking_sender_id: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_number: str = ""

    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@ubuntucare.zm"

    zmw_usd_exchange_rate: float = 25.0

    nhima_api_url: str = ""
    nhima_api_key: str = ""

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "ubuntucare"

    keycloak_server_url: str = "http://localhost:8080"
    keycloak_realm: str = "ubuntucare"
    keycloak_client_id: str = "api-gateway"
    keycloak_client_secret: str = ""

    webrtc_stun_servers: str = "stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302"
    webrtc_turn_url: str = ""
    # Shared secret for a coturn server configured with use-auth-secret.
    # The backend derives short-lived client credentials; never put the secret
    # itself in an ICE configuration returned to browsers.
    webrtc_turn_secret: str = ""
    cloudflare_turn_key_id: str = ""
    cloudflare_turn_api_token: str = ""

    telemetry_enabled: bool = True
    otlp_endpoint: str = ""

    rate_limit_enabled: bool = True
    rate_limit_redis_enabled: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        # The deployment .env is shared with docker-compose and therefore
        # contains infrastructure keys that are not part of this service.
        extra = "ignore"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if os.environ.get("ENVIRONMENT", "").lower() != "production":
            return self
        if self.secret_key in _PLACEHOLDER_SECRETS:
            raise ValueError("SECRET_KEY must be a unique secret in production")
        if self.debug:
            raise ValueError("DEBUG must be disabled in production")
        if not self.cors_origins or "*" in [o.strip() for o in self.cors_origins.split(",")]:
            raise ValueError("CORS_ORIGINS must list explicit origins in production")
        return self


settings = Settings()
