"""SQL Database used for the app."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import create_engine

from app.config import get_settings


def normalize_database_url(url: str) -> str:
    """Select psycopg for standard Postgres connection URLs.

    Returns:
        The SQLAlchemy database URL.

    Raises:
        ValueError: If the URL does not select PostgreSQL.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    if url.startswith("postgresql+psycopg://"):
        return url
    msg = "DATABASE_URL must be a PostgreSQL connection URL"
    raise ValueError(msg)


DATABASE_URL = normalize_database_url(get_settings().DATABASE_URL)
MIGRATION_DATABASE_URL = normalize_database_url(get_settings().DATABASE_URL_UNPOOLED or get_settings().DATABASE_URL)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def _build_alembic_config() -> Config:
    """Build an Alembic config bound to the active runtime database.

    Returns:
        An Alembic config targeting the current application database.
    """
    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    config.attributes["database_url"] = MIGRATION_DATABASE_URL
    return config


def init_db() -> None:
    """Initialize the database and apply schema migrations."""
    command.upgrade(_build_alembic_config(), "head")
