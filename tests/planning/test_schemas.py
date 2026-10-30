"""Tests for structured weekly plan schemas."""

import pytest
from pydantic import ValidationError

from app.planning.schemas import WeeklyPlanOutput


def test_weekly_plan_output_parses_separate_markdown_and_workouts() -> None:
    """Validate the narrative and machine-readable workout fields independently."""
    # GIVEN a provider response matching the weekly plan schema
    payload = {
        "plan_markdown": "# Weekly plan",
        "workouts": [
            {
                "day": "Tuesday",
                "workout_name": "Intervals",
                "description": "Threshold work",
                "segments": [
                    {
                        "title": "Main set",
                        "repeats": 1,
                        "steps": [{"duration_m": 10, "power_pct": "95-100", "rpm": "85-95"}],
                    },
                ],
            },
        ],
    }

    # WHEN the structured result is validated
    result = WeeklyPlanOutput.model_validate(payload)

    # THEN the two output channels remain independently accessible and typed
    assert result.plan_markdown == "# Weekly plan"
    assert result.workouts[0].segments[0].steps[0].power_pct == "95-100"


def test_weekly_plan_output_rejects_invalid_workout_values() -> None:
    """Reject workout steps that cannot be rendered as valid intervals."""
    # GIVEN a provider response containing a zero-duration step
    payload = {
        "plan_markdown": "# Weekly plan",
        "workouts": [
            {
                "day": "Tuesday",
                "workout_name": "Intervals",
                "description": "Threshold work",
                "segments": [
                    {"title": "Main set", "repeats": 1, "steps": [{"duration_m": 0, "power_pct": "95-100"}]},
                ],
            },
        ],
    }

    # WHEN the structured result is validated
    # THEN invalid workout values are rejected before persistence or delivery
    with pytest.raises(ValidationError):
        WeeklyPlanOutput.model_validate(payload)
