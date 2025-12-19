"""Config for the FastAPI app."""

from enum import StrEnum

from pydantic_settings import BaseSettings


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

    class Config:
        """Config for pydantic_settings."""

        env_file = ".env"


settings = Settings()  # type: ignore[missing-argument]
