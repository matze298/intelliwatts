"""Config for the FastAPI app."""

from enum import StrEnum

from pydantic_settings import BaseSettings
from pydantic import Field
from app.planning.coach_prompt import SYSTEM_PROMPT as DEFAULT_SYSTEM_PROMPT, USER_PROMPT as DEFAULT_USER_PROMPT


class LanguageModel(StrEnum):
    """Language model enum."""

    GPT_5_MINI = "gpt-5-mini-2025-08-07"
    GEMINI_FLASH = "gemini-flash-latest"


class Settings(BaseSettings):
    """Settings for the FastAPI app."""

    INTERVALS_ATHLETE_ID: str
    INTERVALS_API_KEY: str
    OPENAI_API_KEY: str | None
    GEMINI_API_KEY: str | None
    LANGUAGE_MODEL: LanguageModel
    CACHE_INTERVALS_HOURS: int = 0
    SYSTEM_PROMPT: str = Field(DEFAULT_SYSTEM_PROMPT)
    USER_PROMPT: str = Field(DEFAULT_USER_PROMPT)
    weekly_hours: float = 8
    weekly_sessions: int = 4

    class Config:
        """Config for pydantic_settings."""

        env_file = ".env"
        validate_assignment = True

    def update(self, **kwargs) -> None:
        """Update the settings based on kwargs."""
        for key, value in kwargs.items():
            setattr(self, key, value)


GLOBAL_SETTINGS = Settings()  # type: ignore[missing-argument]
