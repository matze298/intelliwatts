"""SQL Database used for the app."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///./intervals.db"
engine = create_engine(DATABASE_URL)


def _build_alembic_config() -> Config:
    """Build an Alembic config bound to the active runtime database.

    Returns:
        An Alembic config targeting the current application database.
    """
    config = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
    return config


def init_db() -> None:
    """Initialize the database and apply schema migrations."""
    SQLModel.metadata.create_all(engine)
    command.upgrade(_build_alembic_config(), "head")
