"""Service for loading training plans."""

from typing import TYPE_CHECKING, NamedTuple, cast

import markdown
from sqlalchemy import desc
from sqlmodel import Session, select

from app.db import engine
from app.models.plan import LongTermPlanArtifact, TrainingPlan, WorkoutDelivery
from app.services.long_term_planner import get_or_create_active_phase
from app.utils.datetime import get_monday, get_utc_now

if TYPE_CHECKING:
    from datetime import date, datetime

    from sqlalchemy.sql.elements import ColumnElement

    from app.models.user import User


class LoadedPlan(NamedTuple):
    """Container for a loaded training plan."""

    plan_html: str | None
    long_term_summary_html: str | None
    prompt: list[dict[str, str]] | None
    delivery_status: str | None
    delivery_last_error: str | None
    week_start: date | None


def load_user_plan(user: User, *, week_start: date | None = None, include_weekly_plan: bool = True) -> LoadedPlan:
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

    with Session(engine) as session:
        phase = get_or_create_active_phase(session, user.id)
        artifact_statement = (
            select(LongTermPlanArtifact)
            .where(LongTermPlanArtifact.phase_id == phase.id)
            .order_by(desc(cast("ColumnElement[datetime]", LongTermPlanArtifact.created_at)))
            .order_by(desc(cast("ColumnElement[datetime]", LongTermPlanArtifact.updated_at)))
        )
        artifact = session.exec(artifact_statement).first()
        if artifact:
            long_term_summary_html = markdown.markdown(
                artifact.summary_markdown,
                extensions=["tables", "fenced_code"],
            )

        if include_weekly_plan:
            monday = week_start or get_monday(get_utc_now().date())
            statement = select(TrainingPlan).where(TrainingPlan.week_start == monday, TrainingPlan.phase_id == phase.id)
            plan = session.exec(statement).first()
            if plan:
                plan_html = markdown.markdown(
                    plan.raw_content,
                    extensions=["tables", "fenced_code"],
                )
                prompt = plan.prompt_history
                delivery_statement = select(WorkoutDelivery).where(WorkoutDelivery.training_plan_id == plan.id)
                delivery = session.exec(delivery_statement).first()
                if delivery:
                    delivery_status = delivery.status
                    delivery_last_error = delivery.last_error
                week_start = plan.week_start

    return LoadedPlan(
        plan_html=plan_html,
        long_term_summary_html=long_term_summary_html,
        prompt=prompt,
        delivery_status=delivery_status,
        delivery_last_error=delivery_last_error,
        week_start=week_start,
    )
