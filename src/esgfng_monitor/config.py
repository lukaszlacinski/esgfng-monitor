from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MONITOR_",
        env_file=".env",
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
