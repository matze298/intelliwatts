"""Database used for the app."""

from sqlmodel import SQLModel, create_engine

DATABASE_URL = "sqlite:///./intervals.db"
engine = create_engine(DATABASE_URL)


def init_db() -> None:
    """Initialize the database."""
    SQLModel.metadata.create_all(engine)
