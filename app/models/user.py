"""Persistent profile settings used by the single-user application."""

import uuid

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """The application's single persistent athlete profile."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    weekly_hours: float = 8.0
    weekly_sessions: int = 4
    developer_mode_enabled: bool = False
    system_prompt_override: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    user_prompt_override: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    login_failure_timestamps: list[float] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
