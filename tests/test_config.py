"""Tests for the config module."""

from app.config import Settings


def test_settings_initialization() -> None:
    """Tests that the Settings class initializes correctly with environment variables."""
    # GIVEN environment variables are set (conftest.py)

    # WHEN the Settings class is instantiated
    settings = Settings()  # type: ignore[missing-argument]

    # THEN the settings should have the expected values
    assert settings.INTERVALS_ATHLETE_ID == "test_athlete_id"
    assert settings.INTERVALS_API_KEY == "test_api_key"
    assert settings.JWT_SECRET_KEY == "test_jwt_secret"  # noqa: S105
    assert settings.APP_SECRET_KEY is not None
    assert settings.LANGUAGE_MODEL == "gemini-flash-latest"
