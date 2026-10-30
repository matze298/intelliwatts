"""Config for the FastAPI app."""

from enum import StrEnum
from functools import lru_cache
from typing import Any, cast
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.planning.coach_prompt import SYSTEM_PROMPT as DEFAULT_SYSTEM_PROMPT
from app.planning.coach_prompt import USER_PROMPT as DEFAULT_USER_PROMPT


class LanguageModel(StrEnum):
    """Language model enum."""

    GPT_5_MINI = "gpt-5-mini-2025-08-07"
    GEMINI_FLASH = "gemini-flash-latest"
    GEMINI_2_5_PRO = "gemini-2.5-pro"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"


class Settings(BaseSettings):
    """Settings for the FastAPI app.

    Attributes:
        INTERVALS_ATHLETE_ID: Default athlete ID for Intervals.icu.
        INTERVALS_API_KEY: API key for Intervals.icu.
        OPENAI_API_KEY: API key for OpenAI.
        GEMINI_API_KEY: API key for Google Gemini.
        LANGUAGE_MODEL: The LLM model to use for planning.
        CACHE_INTERVALS_HOURS: How long to cache Intervals.icu API responses.
        ANALYSIS_DAYS: Number of days of history to analyze for the coach.
        DASHBOARD_DAYS: Number of days to display on the dashboard.
        SYSTEM_PROMPT: The core coaching logic prompt.
        USER_PROMPT: The template for athlete-specific data.
    """

    APP_PASSWORD: str = Field(min_length=12)
    SESSION_SECRET: str = Field(min_length=32)
    APP_ORIGIN: str = Field(min_length=1)
    SESSION_COOKIE_SECURE: bool = True
    DATABASE_URL: str = Field(min_length=1, repr=False)
    DATABASE_URL_UNPOOLED: str | None = Field(default=None, repr=False)

    @field_validator("APP_ORIGIN")
    @classmethod
    def validate_app_origin(cls, value: str) -> str:
        """Require an origin with no path, credentials, query, or fragment.

        Returns:
            The normalized origin.

        Raises:
            ValueError: If the value is not an HTTP origin.
        """
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.path not in {"", "/"}
            or bool(parsed.query or parsed.fragment)
        ):
            msg = "APP_ORIGIN must be an HTTP(S) origin without a path"
            raise ValueError(msg)
        return value.rstrip("/")

    # User secrets
    INTERVALS_ATHLETE_ID: str
    INTERVALS_API_KEY: str
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # App configuration
    LANGUAGE_MODEL: LanguageModel
    CACHE_INTERVALS_HOURS: int = 0
    ANALYSIS_DAYS: int = 120
    DASHBOARD_DAYS: int = 42

    # Prompt configuration
    SYSTEM_PROMPT: str = Field(DEFAULT_SYSTEM_PROMPT)
    USER_PROMPT: str = Field(DEFAULT_USER_PROMPT)

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",  # Only used locally, on prod env vars are used
        env_file_encoding="utf-8",
        validate_assignment=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Returns a cached singleton of the application settings.

    Returns:
        The application settings.
    """
    return Settings(**cast("dict[str, Any]", {}))
