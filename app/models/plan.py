"""Defines the TrainingPhase and TrainingPlan models."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class TrainingPhase(SQLModel, table=True):
    """Macro container for a specific training objective."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    primary_goal: str
    start_date: date
    end_date: date
    status: str = Field(default="active")  # active, completed, archived


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
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
