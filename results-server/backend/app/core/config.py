"""Application configuration using pydantic-settings."""

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

    # Database
    database_url: str = (
        "postgresql+asyncpg://benchpro:benchpro_dev@localhost:5432/benchpro_results"
    )

    # Security
    secret_key: str = "development-secret-key-change-in-production"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # OIDC/SSO (optional for local dev)
    oidc_issuer: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None

    # Rate Limiting
    rate_limit_submissions_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    # Application metadata
    app_name: str = "BenchPRO Results Server"
    app_version: str = "0.1.0"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug

    @property
    def oidc_enabled(self) -> bool:
        """Check if OIDC is configured."""
        return bool(self.oidc_issuer and self.oidc_client_id)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

