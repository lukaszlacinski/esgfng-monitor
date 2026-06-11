from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, ValidationError
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
    web_host: str = Field(
        default="127.0.0.1",
        description="Host for the web dashboard",
    )
    web_port: int = Field(
        default=8080,
        description="Port for the web dashboard",
    )
    web_results_hours: int = Field(
        default=24,
        description="Hours of probe history shown on target detail pages",
    )


def _load_env_file(env_path: Path) -> None:
    load_dotenv(env_path, override=False)


@lru_cache
def get_settings() -> Settings:
    env_path = env_file_path().resolve()
    if env_path.is_file():
        _load_env_file(env_path)

    try:
        return Settings()
    except ValidationError as exc:
        if not env_path.is_file():
            raise RuntimeError(
                f"Configuration file not found: {env_path}\n"
                "Copy config/monitor.env.example to .env and set MONITOR_DATABASE_URL."
            ) from exc
        raise RuntimeError(
            f"Invalid configuration in {env_path}. "
            "Ensure MONITOR_DATABASE_URL is set."
        ) from exc
