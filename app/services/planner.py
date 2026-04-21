"""Service for generating the weekly plan."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import requests
from requests_cache import CachedSession
from sqlmodel import Session, select

from app.config import GLOBAL_SETTINGS, Settings
from app.db import engine
from app.intervals.analysis import compute_athlete_status
from app.intervals.client import IntervalsClient
from app.intervals.parser.activity import parse_activities
from app.intervals.parser.power_curve import parse_power_curves
from app.intervals.parser.wellness import parse_wellness_list
from app.models.plan import TrainingPhase, TrainingPlan
from app.planning.llm import generate_plan
from app.planning.llm_to_icu import extract_workout_json, llm_json_to_icu_txt
from app.planning.summary import PlanningConstraints, build_weekly_summary

if TYPE_CHECKING:
    import uuid

    from app.models.user import User


@dataclass
class PlanData:
    """Container for plan content and structured data."""

    raw_content: str
    workout_data: list[dict[str, Any]]
    prompt_history: list[dict[str, str]]


def get_monday(d: date) -> date:
    """Returns the Monday of the week for the given date."""
    return d - timedelta(days=d.weekday())


def get_or_create_active_phase(session: Session, user_id: uuid.UUID) -> TrainingPhase:
    """Gets the active training phase for a user or creates a default one.

    TODO: In the future, we should ask the user for their specific goal and duration
    when starting a new phase instead of assuming defaults.

    Returns:
        The active training phase.
    """
    statement = select(TrainingPhase).where(TrainingPhase.user_id == user_id, TrainingPhase.status == "active")
    phase = session.exec(statement).first()
    if not phase:
        # Create default 4-week phase
        start = datetime.now(UTC).date()
        end = start + timedelta(weeks=4)
        phase = TrainingPhase(
            user_id=user_id, primary_goal="Build FTP (Default)", start_date=start, end_date=end, status="active"
        )
        session.add(phase)
        session.commit()
        session.refresh(phase)
    return phase


def save_training_plan(
    session: Session,
    phase_id: uuid.UUID,
    week_start: date,
    data: PlanData,
) -> TrainingPlan:
    """Saves the training plan to the database, overwriting if it exists for that week.

    Returns:
        The saved training plan.
    """
    statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase_id, TrainingPlan.week_start == week_start)
    plan = session.exec(statement).first()
    if plan:
        plan.raw_content = data.raw_content
        plan.workout_data = data.workout_data
        plan.prompt_history = data.prompt_history
        plan.updated_at = datetime.now(UTC)
    else:
        plan = TrainingPlan(
            phase_id=phase_id,
            week_start=week_start,
            raw_content=data.raw_content,
            workout_data=data.workout_data,
            prompt_history=data.prompt_history,
        )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def generate_weekly_plan(
    user: User, settings: Settings = GLOBAL_SETTINGS, *, use_wellness: bool = True
) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    session = requests.Session()
    if settings.CACHE_INTERVALS_HOURS > 0:
        session = CachedSession(
            "intervals_cache",
            backend="sqlite",
            expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
        )

    client = IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, session=session)

    # Fetch and parse activities
    raw_activities = client.activities(days=settings.ANALYSIS_DAYS)
    activities = parse_activities(raw_activities)

    # Fetch and parse wellness data if requested
    wellness = None
    if use_wellness:
        raw_wellness = client.wellness(days=settings.ANALYSIS_DAYS)
        wellness = parse_wellness_list(raw_wellness)

    # Fetch and parse power curve data
    raw_power_curves = client.power_curves(curves="90d")
    power_curves = parse_power_curves(raw_power_curves)

    # Compute athlete status (load, wellness, ftp trends, and power curve)
    status = compute_athlete_status(activities, wellness_data=wellness, power_curve=power_curves)

    summary = build_weekly_summary(
        activities,
        status.load,
        constraints=PlanningConstraints(
            weekly_hours=settings.weekly_hours,
            weekly_sessions=settings.weekly_sessions,
            primary_goal="increase_ftp",  # Default for now
        ),
        wellness_summary=status.wellness,
        ftp_trajectory=status.ftp_trajectory,
        power_curve=status.power_curve,
    )
    llm_response = generate_plan(summary=summary, language_model=settings.LANGUAGE_MODEL, user=user)

    # Persist the plan
    with Session(engine) as db_session:
        phase = get_or_create_active_phase(db_session, user.id)
        saved_plan = save_training_plan(
            db_session,
            phase.id,
            get_monday(datetime.now(UTC).date()),
            PlanData(
                raw_content=llm_response.plan,
                workout_data=extract_workout_json(llm_response.plan),
                prompt_history=llm_response.prompt,
            ),
        )

    plan = (
        llm_response.plan
        + "\n\n"
        + "## intervals.icu workout file (txt)\n\n```text\n\n"
        + llm_json_to_icu_txt(llm_response.plan)
        + "\n```"
    )
    return {"plan": plan, "summary": summary, "prompt": llm_response.prompt, "plan_id": saved_plan.id}
