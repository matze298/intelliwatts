"""Tests for workout delivery staging and publishing."""

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock

from sqlmodel import Session, create_engine

from app.models.plan import TrainingPhase, TrainingPlan, WorkoutDelivery
from app.models.user import User
from app.services.workout_delivery import publish_workout_delivery, stage_workout_delivery


def _create_plan(session: Session) -> TrainingPlan:
    user = User(id=uuid.uuid4(), email="athlete@example.com", password_hash="hash")  # noqa: S106
    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Peak for race",
        start_date=date(2026, 5, 18),
        end_date=date(2026, 7, 27),
        target_date=date(2026, 7, 27),
    )
    plan = TrainingPlan(
        phase_id=phase.id,
        week_start=date(2026, 5, 18),
        raw_content="## Weekly Plan",
        workout_data=[
            {
                "day": "Tuesday",
                "workout_name": "Tuesday Intervals",
                "description": "Quality work",
                "segments": [
                    {
                        "title": "Main Set",
                        "repeats": 1,
                        "steps": [{"duration_m": 10, "power_pct": "85-95"}],
                    }
                ],
            }
        ],
        prompt_history=[{"role": "user", "content": "generate"}],
    )
    session.add(user)
    session.add(phase)
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def test_stage_workout_delivery_creates_payloads() -> None:
    """Stage a workout delivery from a saved plan."""
    # GIVEN a saved weekly plan with a Tuesday workout
    engine = create_engine("sqlite://")
    TrainingPhase.metadata.create_all(engine)
    TrainingPlan.metadata.create_all(engine)
    WorkoutDelivery.metadata.create_all(engine)

    with Session(engine) as session:
        plan = _create_plan(session)

        # WHEN the delivery is staged
        delivery = stage_workout_delivery(session, plan)

        # THEN the delivery should be persisted as a draft with a workout payload
        assert delivery.training_plan_id == plan.id
        assert delivery.status == "draft"
        assert len(delivery.staged_payload) == 1
        payload = delivery.staged_payload[0]
        assert payload["category"] == "WORKOUT"
        assert payload["external_id"] == f"{plan.id}-0"
        assert payload["start_date_local"] == "2026-05-19T00:00:00"
        assert "Tuesday Intervals" in payload["description"]


def test_publish_workout_delivery_updates_status() -> None:
    """Publish a staged workout delivery through Intervals."""
    # GIVEN a staged delivery and a successful Intervals client
    engine = create_engine("sqlite://")
    TrainingPhase.metadata.create_all(engine)
    TrainingPlan.metadata.create_all(engine)
    WorkoutDelivery.metadata.create_all(engine)

    with Session(engine) as session:
        plan = _create_plan(session)
        delivery = stage_workout_delivery(session, plan)
        client = MagicMock()
        client.publish_workout_events.return_value = [{"id": 123, "external_id": f"{plan.id}-0"}]

        # WHEN the staged workout is published
        updated = publish_workout_delivery(session, plan, client)

        # THEN the delivery is marked as published with the response stored
        assert updated.id == delivery.id
        assert updated.status == "published"
        assert updated.last_error is None
        assert updated.published_payload == [{"id": 123, "external_id": f"{plan.id}-0"}]
        assert isinstance(updated.published_at, datetime)
        client.publish_workout_events.assert_called_once()

        # WHEN the plan is restaged after an edit
        restaged = stage_workout_delivery(session, plan)

        # THEN stale publish metadata should be cleared
        assert restaged.status == "draft"
        assert restaged.published_payload == []
        assert restaged.published_at is None
