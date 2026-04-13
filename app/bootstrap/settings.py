"""Application settings management."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application-level settings."""

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: str = Field(default="development")
    name: str = Field(default="NewsAgent")
    debug: bool = Field(default=False)


class DatabaseSettings(BaseSettings):
    """Database settings."""

    model_config = SettingsConfigDict(env_prefix="DB_", env_file=".env", extra="ignore")

    url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/newsagent")


class RedisSettings(BaseSettings):
    """Redis settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file=".env", extra="ignore")

    url: str = Field(default="redis://localhost:6379/0")


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", extra="ignore")

    provider: str = Field(default="openai")
    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.openai.com/v1")


class EmbeddingSettings(BaseSettings):
    """Embedding provider settings."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", env_file=".env", extra="ignore")

    provider: str = Field(default="openai")


class SchedulerSettings(BaseSettings):
    """Scheduler settings."""

    model_config = SettingsConfigDict(env_prefix="SCHEDULER_", env_file=".env", extra="ignore")

    enabled: bool = Field(default=True)
    daily_workflow_enabled: bool = Field(default=True)
    daily_workflow_cron: str = Field(default="0 6 * * *")  # 6:00 AM daily
    collection_enabled: bool = Field(default=False)
    collection_cron: str = Field(default="0 */4 * * *")  # Every 4 hours
    trend_hunter_enabled: bool = Field(default=False)
    trend_hunter_cron: str = Field(default="0 8,20 * * *")  # 8 AM and 8 PM
    writer_enrichment_enabled: bool = Field(default=False)
    writer_enrichment_cron: str = Field(default="0 7 * * *")  # 7:00 AM
    daily_report_enabled: bool = Field(default=False)
    daily_report_cron: str = Field(default="0 9 * * *")  # 9:00 AM


class Settings:
    """Application settings container."""

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.llm = LLMSettings()
        self.embedding = EmbeddingSettings()
        self.scheduler = SchedulerSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
