"""Tests for settings module."""


def test_app_settings_defaults():
    """Test AppSettings default values."""
    from app.bootstrap.settings import AppSettings

    settings = AppSettings(_env_file=None)
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

    settings = DatabaseSettings(_env_file=None)
    assert "postgresql" in settings.url
    assert "asyncpg" in settings.url


def test_database_settings_reads_from_dotenv(monkeypatch, tmp_path):
    """Test DatabaseSettings loads DB_URL from the local .env file."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DB_URL", raising=False)
    (tmp_path / ".env").write_text(
        "DB_URL=postgresql+asyncpg://postgres:root@127.0.0.1:5432/newsagent\n",
        encoding="utf-8",
    )

    from app.bootstrap.settings import DatabaseSettings

    settings = DatabaseSettings()
    assert settings.url == "postgresql+asyncpg://postgres:root@127.0.0.1:5432/newsagent"


def test_get_settings_cached():
    """Test get_settings returns cached instance."""
    from app.bootstrap.settings import get_settings

    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
