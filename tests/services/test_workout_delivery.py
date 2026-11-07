"""Tests for workout delivery staging and publishing."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.intervals.client import IntervalsClient
from app.models.plan import (
    TrainingPhase,
    TrainingPlan,
    WorkoutDeliveryResult,
    WorkoutDeliveryStatus,
)
from app.models.user import User
from app.services.workout_delivery import publish_workout_delivery, stage_workout_delivery

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture
def workout_session() -> Generator[Session]:
    """Provide a clean in-memory SQLModel session for delivery tests.

    Yields:
        A session backed by an in-memory SQLite database.
    """
    engine: Engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def training_plan(workout_session: Session) -> TrainingPlan:
    """Create a saved weekly plan with one Tuesday workout.

    Returns:
        A persisted training plan row.
    """
    user = User(id=uuid.uuid4())
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
    workout_session.add(user)
    workout_session.add(phase)
    workout_session.add(plan)
    workout_session.commit()
    workout_session.refresh(plan)
    return plan


def test_stage_workout_delivery_creates_payloads(workout_session: Session, training_plan: TrainingPlan) -> None:
    """Stage a workout delivery from a saved plan."""
    # GIVEN a saved weekly plan with a Tuesday workout

    # WHEN the delivery is staged
    delivery = stage_workout_delivery(workout_session, training_plan)

    # THEN the delivery should be persisted as a draft with a workout payload
    assert delivery.training_plan_id == training_plan.id
    assert delivery.status == WorkoutDeliveryStatus.DRAFT
    assert len(delivery.staged_payload) == 1
    payload = delivery.staged_payload[0]
    assert payload["category"] == "WORKOUT"
    assert payload["type"] == "Ride"
    assert payload["external_id"] == f"{training_plan.id}-0"
    assert payload["start_date_local"] == "2026-05-19T00:00:00"
    assert "Tuesday Intervals" in payload["description"]


def test_publish_workout_delivery_updates_status(workout_session: Session, training_plan: TrainingPlan) -> None:
    """Publish a staged workout delivery through Intervals."""
    # GIVEN a staged delivery and a successful Intervals client
    delivery = stage_workout_delivery(workout_session, training_plan)
    client = MagicMock(spec=IntervalsClient)
    published_payload: list[WorkoutDeliveryResult] = [{"id": 123, "external_id": f"{training_plan.id}-0"}]
    client.publish_workout_events.return_value = published_payload

    # WHEN the staged workout is published
    updated = publish_workout_delivery(workout_session, training_plan, client)

    # THEN the delivery is marked as published with the response stored
    assert updated.id == delivery.id
    assert updated.status == WorkoutDeliveryStatus.PUBLISHED
    assert updated.last_error is None
    assert updated.published_payload == [{"id": 123, "external_id": f"{training_plan.id}-0"}]
    assert isinstance(updated.published_at, datetime)
    client.publish_workout_events.assert_called_once()

    # WHEN the plan is restaged after an edit
    restaged = stage_workout_delivery(workout_session, training_plan)

    # THEN previous receipts remain available to reconcile removed workouts on republish.
    assert restaged.status == WorkoutDeliveryStatus.DRAFT
    assert restaged.published_payload == [{"id": 123, "external_id": f"{training_plan.id}-0"}]
    assert restaged.published_at is not None


def test_republish_removes_only_previously_published_obsolete_workouts(
    workout_session: Session, training_plan: TrainingPlan
) -> None:
    """Republishing removes old plan events, never unrelated athlete events."""
    # GIVEN a published plan with two events whose revised draft contains just the first.
    staged = stage_workout_delivery(workout_session, training_plan)
    client = MagicMock(spec=IntervalsClient)
    kept = staged.staged_payload[0]
    old_external_id = f"{training_plan.id}-1"
    staged.published_payload = [
        {"id": 123, "external_id": kept["external_id"]},
        {"id": 124, "external_id": old_external_id},
    ]
    staged.status = WorkoutDeliveryStatus.PUBLISHED
    workout_session.add(staged)
    workout_session.commit()
    stage_workout_delivery(workout_session, training_plan)
    client.publish_workout_events.return_value = [{"id": 123, "external_id": kept["external_id"]}]

    # WHEN the updated plan is republished
    delivery = publish_workout_delivery(workout_session, training_plan, client)

    # THEN only our obsolete event's external ID is deleted.
    assert delivery.status == WorkoutDeliveryStatus.PUBLISHED
    client.publish_workout_events.assert_called_once()
    client.delete_workout_events.assert_called_once_with([old_external_id])


def test_publish_error_preserves_receipts_for_safe_retry(
    workout_session: Session, training_plan: TrainingPlan
) -> None:
    """Failed reconciliation must not lose the IDs needed to retry cleanup."""
    staged = stage_workout_delivery(workout_session, training_plan)
    old_id = f"{training_plan.id}-1"
    staged.published_payload = [{"id": 124, "external_id": old_id}]
    staged.status = WorkoutDeliveryStatus.PUBLISHED
    workout_session.add(staged)
    workout_session.commit()
    stage_workout_delivery(workout_session, training_plan)

    client = MagicMock(spec=IntervalsClient)
    client.publish_workout_events.return_value = [{"id": 123, "external_id": staged.staged_payload[0]["external_id"]}]
    client.delete_workout_events.side_effect = RuntimeError("Intervals unavailable")

    with pytest.raises(RuntimeError, match="Intervals unavailable"):
        publish_workout_delivery(workout_session, training_plan, client)

    failed = workout_session.get(type(staged), staged.id)
    assert failed is not None
    assert failed.status == WorkoutDeliveryStatus.FAILED
    assert failed.published_payload == [{"id": 124, "external_id": old_id}]
    assert failed.last_error == "Intervals unavailable"
