"""Persistent profile settings used by the single-user application."""

import uuid

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """The application's single persistent athlete profile."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    weekly_hours: float = 8.0
    weekly_sessions: int = 4
    developer_mode_enabled: bool = False
