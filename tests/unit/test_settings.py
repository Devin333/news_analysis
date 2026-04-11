"""Tests for settings module."""

import os

import pytest


def test_app_settings_defaults():
    """Test AppSettings default values."""
    from app.bootstrap.settings import AppSettings

    settings = AppSettings()
    assert settings.env == "development"
    assert settings.name == "NewsAgent"
    assert settings.debug is False


def test_app_settings_from_env(monkeypatch):
    """Test AppSettings reads from environment."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("APP_DEBUG", "true")

    from app.bootstrap.settings import AppSettings

    settings = AppSettings()
    assert settings.env == "production"
    assert settings.name == "TestApp"
    assert settings.debug is True


def test_database_settings_defaults():
    """Test DatabaseSettings default values."""
    from app.bootstrap.settings import DatabaseSettings

    settings = DatabaseSettings()
    assert "postgresql" in settings.url
    assert "asyncpg" in settings.url


def test_get_settings_cached():
    """Test get_settings returns cached instance."""
    from app.bootstrap.settings import get_settings

    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
