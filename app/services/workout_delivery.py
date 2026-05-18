"""Helpers for staging and publishing weekly workouts to Intervals.icu."""

import calendar
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.models.plan import TrainingPlan, WorkoutDelivery, WorkoutDeliveryPayload, WorkoutDeliveryStatus
from app.planning.intervals_payload import workout_json_to_icu_txt

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient

DEFAULT_WORKOUT_TYPE = "Ride"
_DAY_OFFSETS = {day.lower(): index for index, day in enumerate(calendar.day_name)}


def build_workout_delivery_payloads(plan: TrainingPlan) -> list[WorkoutDeliveryPayload]:
    """Build Intervals.icu calendar payloads from a saved weekly training plan.

    Returns:
        A list of Intervals.icu calendar event payloads.
    """
    payloads: list[WorkoutDeliveryPayload] = []
    for index, workout in enumerate(plan.workout_data):
        day_name = str(workout.get("day", "")).strip().lower()
        day_offset = _DAY_OFFSETS.get(day_name, index)
        start_date_local = datetime.combine(plan.week_start + timedelta(days=day_offset), datetime.min.time())
        payloads.append({
            "category": "WORKOUT",
            "start_date_local": start_date_local.replace(tzinfo=None).isoformat(timespec="seconds"),
            "type": DEFAULT_WORKOUT_TYPE,
            "name": workout.get("workout_name", f"Workout {index + 1}"),
            "description": workout_json_to_icu_txt(workout),
            "external_id": f"{plan.id}-{index}",
        })
    return payloads


def stage_workout_delivery(session: Session, plan: TrainingPlan) -> WorkoutDelivery:
    """Persist a draft Intervals.icu delivery for a saved weekly plan.

    This stores the staged payload in the SQL database.

    Returns:
        The persisted workout delivery row.
    """
    payloads = build_workout_delivery_payloads(plan)
    statement = select(WorkoutDelivery).where(WorkoutDelivery.training_plan_id == plan.id)
    delivery = session.exec(statement).first()
    now = datetime.now(UTC)
    if delivery:
        delivery.status = WorkoutDeliveryStatus.DRAFT
        delivery.staged_payload = payloads
        delivery.published_payload = []
        delivery.published_at = None
        delivery.last_error = None
        delivery.updated_at = now
    else:
        delivery = WorkoutDelivery(
            training_plan_id=plan.id,
            status=WorkoutDeliveryStatus.DRAFT,
            staged_payload=payloads,
            published_payload=[],
            last_error=None,
        )
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return delivery


def publish_workout_delivery(
    session: Session,
    plan: TrainingPlan,
    client: IntervalsClient,
) -> WorkoutDelivery:
    """Publish a staged weekly workout delivery through the Intervals client.

    Returns:
        The updated workout delivery row.
    """
    statement = select(WorkoutDelivery).where(WorkoutDelivery.training_plan_id == plan.id)
    delivery = session.exec(statement).first()
    if not delivery:
        delivery = stage_workout_delivery(session, plan)

    now = datetime.now(UTC)
    delivery.status = WorkoutDeliveryStatus.PUBLISHING
    delivery.last_error = None
    delivery.updated_at = now
    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    try:
        published_payload = client.publish_workout_events(delivery.staged_payload)
    except Exception as exc:  # pragma: no cover - exercised in integration/unit tests
        delivery.status = WorkoutDeliveryStatus.FAILED
        delivery.last_error = str(exc)
        delivery.updated_at = datetime.now(UTC)
        session.add(delivery)
        session.commit()
        session.refresh(delivery)
        raise

    delivery.status = WorkoutDeliveryStatus.PUBLISHED
    delivery.published_payload = published_payload
    delivery.published_at = datetime.now(UTC)
    delivery.last_error = None
    delivery.updated_at = datetime.now(UTC)
    session.add(delivery)
    session.commit()
    session.refresh(delivery)
    return delivery
