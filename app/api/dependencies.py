"""FastAPI dependency providers."""

from app.bootstrap.settings import Settings, get_settings


def get_app_settings() -> Settings:
    """Provide shared application settings."""
    return get_settings()
