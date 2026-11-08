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

    # THEN stale publish metadata should be cleared
    assert restaged.status == WorkoutDeliveryStatus.DRAFT
    assert restaged.published_payload == []
    assert restaged.published_at is None


@pytest.mark.parametrize(
    ("day", "explicit_date", "expected"),
    [
        ("Tue", None, "2026-05-19T00:00:00"),
        ("Thursday", None, "2026-05-21T00:00:00"),
        ("Saturday, 2026-05-23", None, "2026-05-23T00:00:00"),
        ("2026-05-24", None, "2026-05-24T00:00:00"),
        ("Friday", "2026-05-22", "2026-05-22T00:00:00"),
    ],
)
def test_calendar_date_uses_actual_weekday_or_explicit_date(
    workout_session: Session, training_plan: TrainingPlan, day: str, explicit_date: str | None, expected: str
) -> None:
    """Named weekdays, abbreviations and explicit dates resolve to the selected week."""
    workout = dict(training_plan.workout_data[0])
    workout["day"] = day
    if explicit_date:
        workout["date"] = explicit_date
    training_plan.workout_data = [workout]
    staged = stage_workout_delivery(workout_session, training_plan)
    assert staged.status == WorkoutDeliveryStatus.DRAFT
    assert staged.staged_payload[0]["start_date_local"] == expected


@pytest.mark.parametrize(
    ("day", "explicit_date"),
    [
        ("Some day", None),
        ("Tuesday", "2026-05-20"),
        ("Sunday", "2026-05-31"),
        ("Friday", "2026-05-99"),
    ],
)
def test_invalid_workout_date_keeps_plan_but_blocks_wrong_calendar_export(
    workout_session: Session, training_plan: TrainingPlan, day: str, explicit_date: str | None
) -> None:
    """Bad dates must be visible errors, not silently mapped from array position."""
    workout = dict(training_plan.workout_data[0])
    workout["day"] = day
    if explicit_date:
        workout["date"] = explicit_date
    training_plan.workout_data = [workout]
    staged = stage_workout_delivery(workout_session, training_plan)

    # The LLM output survives for manual revision, without an API request.
    assert training_plan.raw_content == "## Weekly Plan"
    assert staged.status == WorkoutDeliveryStatus.FAILED
    assert staged.staged_payload == []
    assert staged.last_error

    client = MagicMock(spec=IntervalsClient)
    with pytest.raises(ValueError, match="Cannot publish until workout dates are corrected"):
        publish_workout_delivery(workout_session, training_plan, client)
    client.publish_workout_events.assert_not_called()
