"""Tests for the TrainingPhase and TrainingPlan models."""

import uuid
from datetime import date

from app.models.plan import TrainingPhase, TrainingPlan


def test_create_phase_and_plan() -> None:
    """Test creating a TrainingPhase and TrainingPlan."""
    # GIVEN a user ID and phase details
    user_id = uuid.uuid4()

    # WHEN creating a TrainingPhase
    phase = TrainingPhase(
        user_id=user_id, primary_goal="Build FTP", start_date=date(2026, 4, 20), end_date=date(2026, 5, 17)
    )

    # THEN it should have the correct status and goal
    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP"

    # WHEN creating a TrainingPlan linked to that phase
    plan = TrainingPlan(
        phase_id=phase.id,
        week_start=date(2026, 4, 20),
        raw_content="Test plan",
        workout_data=[{"workout_name": "Test", "segments": []}],
        prompt_history=[{"role": "user", "content": "hi"}],
    )

    # THEN it should store the content and structured data correctly
    assert plan.raw_content == "Test plan"
    assert len(plan.workout_data) == 1
    assert plan.workout_data[0]["workout_name"] == "Test"
    assert plan.prompt_history[0]["content"] == "hi"
