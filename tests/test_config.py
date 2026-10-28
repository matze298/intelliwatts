"""Tests for the config module."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_initialization() -> None:
    """Tests that the Settings class initializes correctly with environment variables."""
    # GIVEN environment variables are set (conftest.py)

    # WHEN the Settings class is instantiated
    settings = Settings()

    # THEN the settings should have the expected values
    assert settings.INTERVALS_ATHLETE_ID == "test_athlete_id"
    assert settings.INTERVALS_API_KEY == "test_api_key"
    assert settings.LANGUAGE_MODEL == "gemini-flash-latest"


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unset database URL cannot silently use ephemeral storage."""
    # GIVEN no configured database URL
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # WHEN constructing the application settings
    # THEN configuration fails without consulting a local .env file
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None)
