"""Application settings loaded from environment."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Override via env vars or .env."""

    model_config = SettingsConfigDict(
        env_prefix="AUTONOMY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    database_path: str = ""
    frontend_directory: str = ""
    public_demo: bool = False
    workflow_directory: str = ""
    operator_token: str = ""
    operator_accounts_json: str = ""
    operations_directory: str = ""
    traces_directory: str = ""
    semantic_python: str = ""
    semantic_index: str = ""


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
