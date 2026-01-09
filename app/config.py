"""Config for the FastAPI app."""

from enum import StrEnum
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.planning.coach_prompt import SYSTEM_PROMPT as DEFAULT_SYSTEM_PROMPT
from app.planning.coach_prompt import USER_PROMPT as DEFAULT_USER_PROMPT


class LanguageModel(StrEnum):
    """Language model enum."""

    GPT_5_MINI = "gpt-5-mini-2025-08-07"
    GEMINI_FLASH = "gemini-flash-latest"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"


class Settings(BaseSettings):
    """Settings for the FastAPI app."""

    # Dev settings
    DEV_USER: str | None = None
    DEV_PASSWORD: str | None = None

    # Secret keys
    INTERVALS_ATHLETE_ID: str
    INTERVALS_API_KEY: str
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # App configuration
    LANGUAGE_MODEL: LanguageModel
    CACHE_INTERVALS_HOURS: int = 0

    # Prompt configuration
    SYSTEM_PROMPT: str = Field(DEFAULT_SYSTEM_PROMPT)
    USER_PROMPT: str = Field(DEFAULT_USER_PROMPT)

    # Training constraints
    weekly_hours: float = 8
    weekly_sessions: int = 4

    # Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",  # Only used locally, on prod env vars are used
        env_file_encoding="utf-8",
        validate_assignment=True,
        extra="ignore",
    )

    def update(self, **kwargs: Any) -> None:  # noqa:ANN401
        """Update the settings at runtime with validation."""
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)


GLOBAL_SETTINGS = Settings()  # type: ignore[missing-argument]
