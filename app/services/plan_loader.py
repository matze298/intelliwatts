"""Service for loading training plans."""

from typing import TYPE_CHECKING, NamedTuple

import markdown
from sqlmodel import Session, select

from app.db import engine
from app.models.plan import TrainingPlan
from app.services.planner import get_or_create_active_phase
from app.utils.datetime import get_monday, get_utc_now

if TYPE_CHECKING:
    from app.models.user import User


class LoadedPlan(NamedTuple):
    """Container for a loaded training plan."""

    plan_html: str | None
    prompt: list[dict[str, str]] | None


def load_user_plan(user: User) -> LoadedPlan:
    """Loads the training plan for a user for the current week.

    Args:
        user: The user to load the plan for.

    Returns:
        A LoadedPlan instance.
    """
    plan_html = None
    prompt = None

    with Session(engine) as session:
        phase = get_or_create_active_phase(session, user.id)
        monday = get_monday(get_utc_now().date())
        statement = select(TrainingPlan).where(TrainingPlan.week_start == monday, TrainingPlan.phase_id == phase.id)
        plan = session.exec(statement).first()
        if plan:
            plan_html = markdown.markdown(
                plan.raw_content,
                extensions=["tables", "fenced_code"],
            )
            prompt = plan.prompt_history

    return LoadedPlan(plan_html=plan_html, prompt=prompt)
