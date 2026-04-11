"""Application settings management."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application-level settings."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    env: str = Field(default="development")
    name: str = Field(default="NewsAgent")
    debug: bool = Field(default=False)


class DatabaseSettings(BaseSettings):
    """Database settings."""

    model_config = SettingsConfigDict(env_prefix="DB_", extra="ignore")

    url: str = Field(default="postgresql+asyncpg://postgres:postgres@localhost:5432/newsagent")


class RedisSettings(BaseSettings):
    """Redis settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    url: str = Field(default="redis://localhost:6379/0")


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    provider: str = Field(default="openai")
    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.openai.com/v1")


class EmbeddingSettings(BaseSettings):
    """Embedding provider settings."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", extra="ignore")

    provider: str = Field(default="openai")


class Settings:
    """Application settings container."""

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.llm = LLMSettings()
        self.embedding = EmbeddingSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
