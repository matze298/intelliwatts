"""Typed schemas for language-model planning output."""

import json
import logging

from pydantic import BaseModel, ConfigDict, Field, model_validator

_LOGGER = logging.getLogger(__name__)


class LLMOutputModel(BaseModel):
    """Base model that logs and ignores fields outside the response schema."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def log_unexpected_fields(cls, value: object) -> object:
        """Log fields that are ignored during response validation.

        Returns:
            The unmodified input for Pydantic to validate.
        """
        if isinstance(value, dict):
            unexpected = {key: field_value for key, field_value in value.items() if key not in cls.model_fields}
            if unexpected:
                _LOGGER.warning("Ignoring unknown fields in %s: %s", cls.__name__, sorted(unexpected))
                _LOGGER.debug(
                    "Ignored values in %s: %s", cls.__name__, json.dumps(unexpected, ensure_ascii=False)[:1000]
                )
        return value


class WorkoutStep(LLMOutputModel):
    """A single interval step in a workout."""

    duration_m: int = Field(ge=1, description="Step duration in minutes.")
    power_pct: str = Field(description="Power target as a percentage range, such as '85-95' or 'Ramp 50-60'.")
    rpm: str | None = Field(default=None, description="Optional cadence range in rpm, such as '85-95'.")


class WorkoutSegment(LLMOutputModel):
    """A named workout segment containing one or more interval steps."""

    title: str
    repeats: int = Field(ge=1)
    steps: list[WorkoutStep]


class PlannedWorkout(LLMOutputModel):
    """A single planned workout ready for conversion to Intervals.icu format."""

    day: str = Field(description="Day of the week, e.g. Monday.")
    workout_name: str
    description: str
    segments: list[WorkoutSegment]


class WeeklyPlanOutput(LLMOutputModel):
    """Separate human-readable plan from machine-readable workout data."""

    plan_markdown: str = Field(description="The complete human-readable weekly training plan in Markdown.")
    workouts: list[PlannedWorkout] = Field(description="Structured workouts for each training day; omit rest days.")
