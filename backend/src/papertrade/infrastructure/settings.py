"""Application settings and configuration.

Uses pydantic-settings to load configuration from environment variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Attributes:
        # JWT Configuration
        jwt_secret_key: Secret key for JWT signing
        jwt_algorithm: JWT algorithm (default: HS256)
        access_token_expire_minutes: Access token expiry in minutes
        refresh_token_expire_days: Refresh token expiry in days

        # Database Configuration
        database_url: Database connection URL

        # Application Configuration
        app_env: Environment (development/production)
        app_debug: Debug mode flag
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # JWT Configuration
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Database Configuration
    database_url: str = "sqlite+aiosqlite:///./papertrade.db"

    # Application Configuration
    app_env: str = "development"
    app_debug: bool = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application settings singleton
    """
    return Settings()
