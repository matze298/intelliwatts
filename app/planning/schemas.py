"""Typed schemas for language-model planning output."""

from pydantic import BaseModel, ConfigDict, Field


class WorkoutStep(BaseModel):
    """A single interval step in a workout."""

    model_config = ConfigDict(extra="forbid")

    duration_m: int = Field(gt=0, description="Step duration in minutes.")
    power_pct: str = Field(description="Power target as a percentage range, such as '85-95' or 'Ramp 50-60'.")
    rpm: str | None = Field(default=None, description="Optional cadence range in rpm, such as '85-95'.")


class WorkoutSegment(BaseModel):
    """A named workout segment containing one or more interval steps."""

    model_config = ConfigDict(extra="forbid")

    title: str
    repeats: int = Field(ge=1)
    steps: list[WorkoutStep]


class PlannedWorkout(BaseModel):
    """A single planned workout ready for conversion to Intervals.icu format."""

    model_config = ConfigDict(extra="forbid")

    day: str = Field(description="Day of the week, e.g. Monday.")
    workout_name: str
    description: str
    segments: list[WorkoutSegment]


class WeeklyPlanOutput(BaseModel):
    """Separate human-readable plan from machine-readable workout data."""

    model_config = ConfigDict(extra="forbid")

    plan_markdown: str = Field(description="The complete human-readable weekly training plan in Markdown.")
    workouts: list[PlannedWorkout] = Field(description="Structured workouts for each training day; omit rest days.")
