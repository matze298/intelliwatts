"""Tests for the TrainingPhase and TrainingPlan models."""

import uuid
from datetime import date

from app.models.plan import TrainingPhase, TrainingPlan


def test_create_phase_and_plan() -> None:
    """Test creating a TrainingPhase and TrainingPlan."""
    user_id = uuid.uuid4()
    phase = TrainingPhase(
        user_id=user_id, primary_goal="Build FTP", start_date=date(2026, 4, 20), end_date=date(2026, 5, 17)
    )
    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP"

    plan = TrainingPlan(
        phase_id=phase.id,
        week_start=date(2026, 4, 20),
        raw_content="Test plan",
        workout_data=[{"workout_name": "Test", "segments": []}],
        prompt_history=[{"role": "user", "content": "hi"}],
    )
    assert plan.raw_content == "Test plan"
    assert len(plan.workout_data) == 1
    assert plan.workout_data[0]["workout_name"] == "Test"
    assert plan.prompt_history[0]["content"] == "hi"
