"""Application configuration using environment variables and an optional .env file.

Configuration is loaded from the shell environment and an optional .env file
(shell environment wins) with ``python-dotenv`` and validated with plain
pydantic (``pydantic-settings`` is declared in requirements.txt but is not
required at runtime). The resulting ``settings`` object exposes the same
attribute names used throughout the application.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values, load_dotenv
from pydantic import BaseModel, Field

# Load .env if present. load_dotenv(override=False) never clobbers the shell
# environment, which is where real secrets live at runtime.
load_dotenv()

_ENV_FILE = Path(".env")


def _read_env() -> dict[str, Any]:
    """Return environment values: shell env takes precedence over .env."""
    file_values = {k: v for k, v in dotenv_values(_ENV_FILE).items() if v is not None}
    return {**file_values, **os.environ}


class Settings(BaseModel):
    """Environment-driven configuration for TransitPulse."""

    # Application
    app_host: str = Field("0.0.0.0", validation_alias="APP_HOST")
    app_port: int = Field(8000, validation_alias="APP_PORT")
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field("json", validation_alias="LOG_FORMAT")

    # Database
    # ``postgresql+asyncpg`` uses the async asyncpg driver. Fall back to
    # ``postgresql+psycopg2`` (psycopg2-binary, synchronous) if asyncpg is
    # unavailable in your environment.
    database_url: str = Field(
        "postgresql+asyncpg://transitpulse:transitpulse@localhost:5432/transitpulse",
        validation_alias="DATABASE_URL",
    )

    # ML Model
    model_path: str = Field("./models/latest.pkl", validation_alias="MODEL_PATH")
    model_retrain_enabled: bool = Field(
        False, validation_alias="MODEL_RETRAIN_ENABLED"
    )

    # CORS (comma-separated origins; "*" means allow all)
    cors_origins: str = Field("*", validation_alias="CORS_ORIGINS")

    # Synthetic data
    synthetic_data_days: int = Field(365, validation_alias="SYNTHETIC_DATA_DAYS")
    synthetic_seed: int = Field(42, validation_alias="SYNTHETIC_SEED")

    # Ingestion
    ingest_batch_size: int = Field(1000, validation_alias="INGEST_BATCH_SIZE")

    @property
    def cors_origin_list(self) -> list[str]:
        """Split the comma-separated CORS origins into a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


def _load() -> Settings:
    """(Re)load settings from the environment. Useful from tests."""
    return Settings.model_validate(_read_env())


settings: Settings = _load()


def reload() -> Settings:
    """Reload settings from the environment and update the module singleton."""
    global settings
    settings = _load()
    return settings


__all__ = ["Settings", "settings", "reload"]
