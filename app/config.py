"""Config for the FastAPI app."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the FastAPI app."""

    DATABASE_URL: str
    INTERVALS_CLIENT_ID: str
    INTERVALS_CLIENT_SECRET: str
    INTERVALS_REDIRECT_URI: str
    OPENAI_API_KEY: str

    class Config:
        """Config for pydantic_settings."""

        env_file = ".env"


settings = Settings()  # type: ignore[missing-argument]
