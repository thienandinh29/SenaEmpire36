from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """App settings loaded from the repo-root .env, overridable by real env vars."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # .env is copied from .env.example with blank values; blank must mean "use the default".
        env_ignore_empty=True,
    )

    # Default points at the local Docker database from docker-compose.yml.
    database_url: str = "postgresql://postgres:postgres@localhost:54322/nodetrail"


@lru_cache
def get_settings() -> Settings:
    return Settings()
