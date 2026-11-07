"""Service for loading training plans."""

from datetime import date
from typing import TYPE_CHECKING, Any, NamedTuple, cast
from urllib.parse import urlencode

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db import engine
from app.models.plan import LongTermPlanArtifact, TrainingPlan, WorkoutDelivery, WorkoutDeliveryStatus
from app.services.long_term_planner import get_active_phase
from app.utils.datetime import get_monday, get_utc_now
from app.utils.markdown import render_markdown

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.sql.elements import ColumnElement

    from app.models.user import User


class PublishedWorkoutLink(NamedTuple):
    """A confirmed Intervals.icu calendar workout deep link."""

    name: str
    date: str
    event_url: str
    calendar_url: str


def published_workout_links(delivery: WorkoutDelivery) -> tuple[PublishedWorkoutLink, ...]:
    """Construct links from confirmed event IDs, never from an unconfirmed draft.

    Returns:
        Links to published workouts, with calendar URLs as a fallback.
    """
    if delivery.status != WorkoutDeliveryStatus.PUBLISHED:
        return ()

    staged_by_external_id = {item["external_id"]: item for item in delivery.staged_payload}
    links: list[PublishedWorkoutLink] = []
    for index, receipt in enumerate(delivery.published_payload):
        event_id = receipt.get("id")
        if not isinstance(event_id, int) or isinstance(event_id, bool) or event_id <= 0:
            continue
        external_id = receipt.get("external_id")
        staged = staged_by_external_id.get(str(external_id)) if external_id else None
        if staged is None and index < len(delivery.staged_payload):
            staged = delivery.staged_payload[index]
        if staged is None:
            continue
        try:
            workout_date = date.fromisoformat(staged["start_date_local"][:10]).isoformat()
        except ValueError, KeyError, TypeError:
            continue
        week_query = urlencode({"w": workout_date})
        links.append(
            PublishedWorkoutLink(
                name=staged["name"],
                date=workout_date,
                event_url=f"https://intervals.icu/?{week_query}&event={event_id}",
                calendar_url=f"https://intervals.icu/?{week_query}",
            )
        )
    return tuple(links)


class LoadedPlan(NamedTuple):
    """Container for a loaded training plan."""

    plan_html: str | None
    long_term_summary_html: str | None
    prompt: list[dict[str, str]] | None
    delivery_status: str | None
    delivery_last_error: str | None
    week_start: date | None
    workout_data: list[dict[str, Any]]
    delivery_links: tuple[PublishedWorkoutLink, ...] = ()


def load_user_plan(  # ruff: ignore[too-many-locals]
    user: User, *, week_start: date | None = None, include_weekly_plan: bool = True
) -> LoadedPlan:
    """Loads the training plan for a user for the selected or current week.

    Args:
        user: The user to load the plan for.
        week_start: The Monday date for the weekly plan to load. Defaults to the current week.
        include_weekly_plan: Whether to load a weekly plan in addition to the long-term summary.

    Returns:
        A LoadedPlan instance.
    """
    plan_html = None
    long_term_summary_html = None
    prompt = None
    delivery_status = None
    delivery_last_error = None
    workout_data: list[dict[str, Any]] = []
    delivery_links: tuple[PublishedWorkoutLink, ...] = ()

    with Session(engine) as session:
        phase = get_active_phase(session, user.id)
        if phase is None:
            return LoadedPlan(None, None, None, None, None, week_start, [])
        artifact_statement = (
            select(LongTermPlanArtifact)
            .where(LongTermPlanArtifact.phase_id == phase.id)
            .order_by(desc(cast("ColumnElement[datetime]", LongTermPlanArtifact.created_at)))
            .order_by(desc(cast("ColumnElement[datetime]", LongTermPlanArtifact.updated_at)))
        )
        artifact = session.exec(artifact_statement).first()
        if artifact:
            long_term_summary_html = render_markdown(artifact.summary_markdown)

        if include_weekly_plan:
            monday = week_start or get_monday(get_utc_now().date())
            statement = select(TrainingPlan).where(TrainingPlan.week_start == monday, TrainingPlan.phase_id == phase.id)
            plan = session.exec(statement).first()
            if plan:
                plan_html = render_markdown(plan.raw_content)
                prompt = plan.prompt_history
                workout_data = plan.workout_data
                delivery_statement = select(WorkoutDelivery).where(WorkoutDelivery.training_plan_id == plan.id)
                delivery = session.exec(delivery_statement).first()
                if delivery:
                    delivery_status = delivery.status
                    delivery_last_error = delivery.last_error
                    delivery_links = published_workout_links(delivery)
                week_start = plan.week_start

    return LoadedPlan(
        plan_html=plan_html,
        long_term_summary_html=long_term_summary_html,
        prompt=prompt,
        delivery_status=delivery_status,
        delivery_last_error=delivery_last_error,
        week_start=week_start,
        workout_data=workout_data,
        delivery_links=delivery_links,
    )
