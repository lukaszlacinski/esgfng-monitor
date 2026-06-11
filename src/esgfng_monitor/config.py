from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def project_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "alembic.ini").is_file():
            return parent
    raise RuntimeError("Could not find project root (alembic.ini)")


def env_file_path() -> Path:
    return project_root() / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MONITOR_",
        env_file=env_file_path(),
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL, e.g. postgresql+psycopg://user:pass@localhost:5432/monitor",
    )
    request_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP request timeout per target",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
