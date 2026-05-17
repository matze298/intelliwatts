"""Defines the training plan-related SQLModel models."""

import uuid
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, TypedDict

from sqlmodel import JSON, Column, Field, SQLModel


class LongTermPlanBlock(TypedDict):
    """A single macro training block in a long-term plan."""

    name: str
    focus: str
    weeks: int


class LongTermPlanStructuredData(TypedDict):
    """Structured macro-planning content stored with a long-term artifact."""

    goal: str
    start_date: str
    target_date: str
    duration_weeks: int
    blocks: list[LongTermPlanBlock]


class WorkoutDeliveryStatus(StrEnum):
    """Statuses for workout delivery lifecycle."""

    DRAFT = "draft"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class WorkoutDeliveryPayload(TypedDict):
    """Planned workout payload sent to Intervals.icu."""

    category: str
    start_date_local: str
    type: str
    name: str
    description: str
    external_id: str


class WorkoutDeliveryResult(TypedDict, total=False):
    """Intervals.icu response item for a planned workout."""

    id: int
    external_id: str


class TrainingPhase(SQLModel, table=True):
    """Macro container for a specific training objective."""

    def __init__(self, **data: object) -> None:
        """Mirror end_date when target_date is omitted by older call sites."""
        if data.get("target_date") is None and data.get("end_date") is not None:
            data["target_date"] = data["end_date"]
        super().__init__(**data)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    primary_goal: str
    start_date: date
    end_date: date
    target_date: date
    status: str = Field(default="active")  # active, completed, archived


class LongTermPlanArtifact(SQLModel, table=True):
    """Stores structured long-term planning output for a training phase."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phase_id: uuid.UUID = Field(foreign_key="trainingphase.id")
    structured_data: LongTermPlanStructuredData = Field(default_factory=dict, sa_column=Column(JSON))
    summary_markdown: str
    prompt_history: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TrainingPlan(SQLModel, table=True):
    """Micro execution level, storing the LLM-generated workouts."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phase_id: uuid.UUID = Field(foreign_key="trainingphase.id")
    week_start: date
    raw_content: str
    # workout_data: Structured JSON containing list of workouts, segments, and steps.
    workout_data: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    # prompt_history: The full conversation history for this iteration cycle.
    prompt_history: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkoutDelivery(SQLModel, table=True):
    """Tracks a staged or published Intervals.icu workout delivery for a weekly plan."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    training_plan_id: uuid.UUID = Field(foreign_key="trainingplan.id", index=True, unique=True)
    status: WorkoutDeliveryStatus = Field(default=WorkoutDeliveryStatus.DRAFT)
    staged_payload: list[WorkoutDeliveryPayload] = Field(default_factory=list, sa_column=Column(JSON))
    published_payload: list[WorkoutDeliveryResult] = Field(default_factory=list, sa_column=Column(JSON))
    last_error: str | None = None
    published_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
