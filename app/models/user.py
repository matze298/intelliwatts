"""Legacy database profile and secret table definitions."""

import uuid

from sqlmodel import Field, SQLModel


class UserSecrets(SQLModel, table=True):
    """Legacy table retained until the database migration."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    intervals_athlete_id: str
    intervals_api_key: bytes
    openai_api_key: bytes | None = None
    gemini_api_key: bytes | None = None


class User(SQLModel, table=True):
    """Internal profile, using existing columns until the database migration."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str
    password_hash: str
    weekly_hours: float = 8.0
    weekly_sessions: int = 4
    developer_mode_enabled: bool = False
