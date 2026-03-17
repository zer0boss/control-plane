"""
Control Plane Configuration
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "OpenClaw Control Plane"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, alias="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Security
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./control_plane.db",
        alias="DATABASE_URL",
    )

    # Redis (optional)
    redis_url: Optional[str] = Field(default=None, alias="REDIS_URL")

    # AO Plugin Settings
    ao_plugin_timeout: int = Field(default=30, alias="AO_PLUGIN_TIMEOUT")
    ao_plugin_retry_attempts: int = Field(default=3, alias="AO_PLUGIN_RETRY_ATTEMPTS")

    # Metrics
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.debug


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
