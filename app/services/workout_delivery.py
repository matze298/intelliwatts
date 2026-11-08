"""Helpers for staging and publishing weekly workouts to Intervals.icu."""

import calendar
import re
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.models.plan import TrainingPlan, WorkoutDelivery, WorkoutDeliveryPayload, WorkoutDeliveryStatus
from app.planning.intervals_payload import workout_json_to_icu_txt

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient

DEFAULT_WORKOUT_TYPE = "Ride"
_DAY_OFFSETS = {day.lower(): index for index, day in enumerate(calendar.day_name)}
_DAY_OFFSETS.update({day[:3].lower(): index for index, day in enumerate(calendar.day_name)})
_DAY_OFFSETS["tues"] = 1
_DAY_OFFSETS["thurs"] = 3
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _workout_calendar_date(workout: dict[str, object], week_start: date) -> date:
    """Resolve an exact selected-week date without guessing from list position.

    Returns:
        The local date for a workout within the selected training week.

    Raises:
        ValueError: For an unrecognized or conflicting day/date.
    """
    raw_day = str(workout.get("day", "")).strip()
    name = workout.get("workout_name", "Workout")
    explicit = workout.get("date")
    embedded_date = _ISO_DATE.search(raw_day)
    raw_date = explicit if isinstance(explicit, str) and explicit else embedded_date.group() if embedded_date else None
    weekday_token = raw_day.split(",", 1)[0].split()[0].strip(".").lower() if raw_day else ""
    weekday = _DAY_OFFSETS.get(weekday_token)

    if raw_date is not None:
        try:
            planned_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            msg = f"{name}: invalid workout date {raw_date!r}"
            raise ValueError(msg) from exc
        if weekday is not None and planned_date.weekday() != weekday:
            msg = f"{name}: day {raw_day!r} disagrees with date {raw_date!r}"
            raise ValueError(msg)
    elif weekday is not None:
        planned_date = week_start + timedelta(days=weekday)
    else:
        msg = f"{name}: unknown workout day {raw_day!r}; use Monday-Sunday or a YYYY-MM-DD date"
        raise ValueError(msg)

    if not week_start <= planned_date <= week_start + timedelta(days=6):
        msg = f"{name}: {planned_date.isoformat()} is outside the selected week {week_start.isoformat()}"
        raise ValueError(msg)
    return planned_date


def build_workout_delivery_payloads(plan: TrainingPlan) -> list[WorkoutDeliveryPayload]:
    """Build Intervals.icu calendar payloads from a saved weekly training plan.

    Returns:
        A list of Intervals.icu calendar event payloads.
    """
    payloads: list[WorkoutDeliveryPayload] = []
    for index, workout in enumerate(plan.workout_data):
        calendar_date = _workout_calendar_date(workout, plan.week_start)
        start_date_local = datetime.combine(calendar_date, datetime.min.time())
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
    try:
        payloads = build_workout_delivery_payloads(plan)
        staging_error = None
    except ValueError as exc:
        # The generated plan remains saved for review; never silently move a
        # workout to a different day or publish an incorrect calendar date.
        payloads = []
        staging_error = str(exc)
    statement = select(WorkoutDelivery).where(WorkoutDelivery.training_plan_id == plan.id)
    delivery = session.exec(statement).first()
    now = datetime.now(UTC)
    if delivery:
        delivery.status = WorkoutDeliveryStatus.FAILED if staging_error else WorkoutDeliveryStatus.DRAFT
        delivery.staged_payload = payloads
        delivery.published_payload = []
        delivery.published_at = None
        delivery.last_error = staging_error
        delivery.updated_at = now
    else:
        delivery = WorkoutDelivery(
            training_plan_id=plan.id,
            status=WorkoutDeliveryStatus.FAILED if staging_error else WorkoutDeliveryStatus.DRAFT,
            staged_payload=payloads,
            published_payload=[],
            last_error=staging_error,
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

    Raises:
        ValueError: When an invalid local date has blocked staging.
    """
    statement = select(WorkoutDelivery).where(WorkoutDelivery.training_plan_id == plan.id)
    delivery = session.exec(statement).first()
    if not delivery:
        delivery = stage_workout_delivery(session, plan)

    if delivery.status == WorkoutDeliveryStatus.FAILED and delivery.last_error and not delivery.staged_payload:
        msg = f"Cannot publish until workout dates are corrected: {delivery.last_error}"
        raise ValueError(msg)

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
