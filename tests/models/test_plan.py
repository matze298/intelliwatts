"""Tests for the TrainingPhase, TrainingPlan, and workout delivery models."""

import uuid
from datetime import UTC, date, datetime

from app.models.plan import LongTermPlanArtifact, TrainingPhase, TrainingPlan, WorkoutDelivery


def test_create_phase_and_plan() -> None:
    """Test creating a TrainingPhase and TrainingPlan."""
    # GIVEN a user ID and phase details
    user_id = uuid.uuid4()

    # WHEN creating a TrainingPhase
    phase = TrainingPhase(
        user_id=user_id,
        primary_goal="Build FTP",
        start_date=date(2026, 4, 20),
        end_date=date(2026, 5, 17),
        target_date=date(2026, 5, 17),
    )

    # THEN it should have the correct status and goal
    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP"
    assert phase.target_date == date(2026, 5, 17)

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


def test_create_long_term_plan_artifact() -> None:
    """Test creating a long-term planning artifact."""
    # GIVEN a training phase
    phase = TrainingPhase(
        user_id=uuid.uuid4(),
        primary_goal="Peak for gran fondo",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 8, 1),
        target_date=date(2026, 8, 1),
    )

    # WHEN creating a long-term artifact for it
    artifact = LongTermPlanArtifact(
        phase_id=phase.id,
        structured_data={"blocks": [{"name": "Base"}]},
        summary_markdown="## Long-term plan",
        prompt_history=[{"role": "user", "content": "Build me to August"}],
    )

    # THEN it should preserve the structured fields and timestamps
    assert artifact.phase_id == phase.id
    assert artifact.structured_data["blocks"][0]["name"] == "Base"
    assert artifact.summary_markdown == "## Long-term plan"
    assert artifact.prompt_history[0]["role"] == "user"
    assert isinstance(artifact.created_at, datetime)
    assert artifact.created_at.tzinfo == UTC
    assert isinstance(artifact.updated_at, datetime)
    assert artifact.updated_at.tzinfo == UTC


def test_create_workout_delivery() -> None:
    """Test creating a workout delivery record for a training plan."""
    # GIVEN a training plan row identifier
    training_plan_id = uuid.uuid4()

    # WHEN creating a workout delivery
    delivery = WorkoutDelivery(
        training_plan_id=training_plan_id,
        status="draft",
        staged_payload=[{"external_id": "plan-1-0"}],
    )

    # THEN it should preserve the staged payload and default timestamps
    assert delivery.training_plan_id == training_plan_id
    assert delivery.status == "draft"
    assert delivery.staged_payload[0]["external_id"] == "plan-1-0"
    assert isinstance(delivery.created_at, datetime)
    assert delivery.created_at.tzinfo == UTC
    assert isinstance(delivery.updated_at, datetime)
    assert delivery.updated_at.tzinfo == UTC


def test_training_phase_defaults_target_date_to_end_date() -> None:
    """TrainingPhase should mirror end_date when target_date is omitted."""
    # GIVEN phase data that omits target_date
    phase = TrainingPhase(
        user_id=uuid.uuid4(),
        primary_goal="Build FTP",
        start_date=date(2026, 4, 20),
        end_date=date(2026, 5, 17),
    )

    # WHEN the TrainingPhase is initialized

    # THEN target_date should mirror end_date for backward compatibility
    assert phase.target_date == date(2026, 5, 17)
