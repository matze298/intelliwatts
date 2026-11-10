"""Native strength persistence foundation; no source import or logging routes yet."""

import uuid
from datetime import date  # ruff: ignore[typing-only-standard-library-import] - SQLModel resolves at runtime
from typing import Any

from sqlalchemy import JSON, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class Exercise(SQLModel, table=True):
    """An athlete-owned exercise with an optional stable legacy identifier."""

    __table_args__ = (UniqueConstraint("user_id", "source_id", name="uq_exercise_user_source"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    source_id: str | None = None
    name: str
    primary_metric: str | None = None
    active: bool = True


class StrengthTemplate(SQLModel, table=True):
    """A versioned workout definition; historical versions remain independent."""

    __table_args__ = (UniqueConstraint("user_id", "name", "variant", "version", name="uq_strengthtemplate_version"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    name: str
    variant: str
    version: str
    active: bool = True
    # Preserve ordered exercise slots and source template rows until the logger
    # needs a more specific structure; never mutate a used historical version.
    definition: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))


class StrengthSession(SQLModel, table=True):
    """One performed strength session, distinct from any planned workout."""

    __table_args__ = (UniqueConstraint("user_id", "source_id", name="uq_strengthsession_user_source"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    template_id: uuid.UUID | None = Field(default=None, foreign_key="strengthtemplate.id")
    source_id: str | None = None
    session_date: date
    workout_type: str
    variant: str | None = None
    template_version: str | None = None
    status: str = "completed"
    duration_minutes: float | None = None
    session_rpe: float | None = None
    readiness: str | None = None
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # Optional original row values support lossless legacy auditing without
    # making Sheet-specific calculated/formula fields first-class columns.
    source_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))


class StrengthSet(SQLModel, table=True):
    """One performed set; missing measurements remain NULL rather than zero."""

    __table_args__ = (UniqueConstraint("source_id", name="uq_strengthset_source"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="strengthsession.id", index=True)
    exercise_id: uuid.UUID = Field(foreign_key="exercise.id")
    source_id: str | None = None
    set_number: int
    side: str | None = None
    reps: float | None = None
    load_kg: float | None = None
    duration_seconds: float | None = None
    distance_m: float | None = None
    rir: float | None = None
    band_id: str | None = None
    band_setup: str | None = None
    variation_setup: str | None = None
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    source_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
