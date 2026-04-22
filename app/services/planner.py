"""Service for generating the weekly plan."""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import requests
from requests_cache import CachedSession
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db import engine
from app.intervals.analysis import compute_analysis
from app.intervals.client import IntervalsClient
from app.intervals.parser.activity import parse_activities
from app.intervals.parser.power_curve import parse_power_curves
from app.intervals.parser.wellness import parse_wellness_list
from app.models.plan import TrainingPhase, TrainingPlan
from app.planning.coach_prompt import SYSTEM_PROMPT, user_prompt
from app.planning.llm import LLMRole, generate_plan
from app.planning.llm_to_icu import extract_workout_json, llm_json_to_icu_txt
from app.planning.providers.registry import registry
from app.utils.datetime import get_monday

if TYPE_CHECKING:
    import uuid

    from app.intervals.models import AnalysisResult
    from app.models.user import User


@dataclass
class PlanData:
    """Container for plan content and structured data."""

    raw_content: str
    workout_data: list[dict[str, Any]]
    prompt_history: list[dict[str, str]]


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


async def update_training_plan(user: User, feedback: str, settings: Settings | None = None) -> dict[str, Any]:
    """Updates the training plan based on user feedback.

    Returns:
        The updated weekly plan and summary.
    """
    if settings is None:
        settings = get_settings()

    with Session(engine) as session:
        phase = get_or_create_active_phase(session, user.id)
        monday = get_monday(datetime.now(UTC).date())

        statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase.id, TrainingPlan.week_start == monday)
        plan = session.exec(statement).first()

        if not plan:
            # Fallback to generating a new plan if none exists
            return await generate_weekly_plan(user, settings)

        # Append feedback to history
        history = plan.prompt_history
        history.append({"role": LLMRole.USER, "content": feedback})

        llm_response = generate_plan(messages=history, language_model=settings.LANGUAGE_MODEL, user=user)

        # Save the updated plan
        try:
            workout_data = extract_workout_json(llm_response.plan)
        except json.JSONDecodeError:
            workout_data = []
        saved_plan = save_training_plan(
            session,
            phase.id,
            monday,
            PlanData(
                raw_content=llm_response.plan,
                workout_data=workout_data,
                prompt_history=llm_response.prompt,
            ),
        )

    full_plan_text = (
        llm_response.plan
        + "\n\n"
        + "## intervals.icu workout file (txt)\n\n```text\n\n"
        + llm_json_to_icu_txt(llm_response.plan)
        + "\n```"
    )
    return {"plan": full_plan_text, "plan_id": saved_plan.id}


def _get_analysis(client: IntervalsClient, analysis_days: int) -> AnalysisResult:
    """Performs the full sports science analysis for the athlete.

    Returns:
        The computed analysis result.
    """
    # Use max required days (e.g. 120d for PMC, 30d for FTP trajectory, 42d for wellness)
    lookback_days = max(analysis_days, 42)
    raw_activities = client.activities(days=lookback_days)
    raw_wellness = client.wellness(days=lookback_days)
    raw_power_curves = client.power_curves(curves="90d")

    return compute_analysis(
        parse_activities(raw_activities),
        wellness_data=parse_wellness_list(raw_wellness),
        power_curve=parse_power_curves(raw_power_curves),
        client=client,
    )


async def generate_weekly_plan(
    user: User,
    settings: Settings | None = None,
    *,
    weekly_hours: float | None = None,
    weekly_sessions: int | None = None,
) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    if settings is None:
        settings = get_settings()

    session = requests.Session()
    if settings.CACHE_INTERVALS_HOURS > 0:
        session = CachedSession(
            "intervals_cache",
            backend="sqlite",
            expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
        )

    client = IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, session=session)

    # Pre-fetch and compute analysis once to be shared among providers
    analysis = _get_analysis(client, settings.ANALYSIS_DAYS)

    # Fetch combined context from all registered providers
    context = await registry.get_combined_context(analysis.provider_results)

    # Build the full summary string
    full_summary = (
        "Training Constraints:\n"
        f"- Max Hours: {weekly_hours if weekly_hours is not None else user.weekly_hours}\n"
        f"- Max Sessions: {weekly_sessions if weekly_sessions is not None else user.weekly_sessions}\n"
        f"- Primary Goal: Build FTP (Default)\n\n"
        f"{context}"
    )

    llm_response = generate_plan(
        messages=[
            {"role": LLMRole.SYSTEM, "content": SYSTEM_PROMPT},
            {"role": LLMRole.USER, "content": user_prompt(full_summary)},
        ],
        language_model=settings.LANGUAGE_MODEL,
        user=user,
    )

    # Persist the plan
    with Session(engine) as db_session:
        phase = get_or_create_active_phase(db_session, user.id)
        try:
            workout_data = extract_workout_json(llm_response.plan)
        except json.JSONDecodeError:
            workout_data = []
        saved_plan = save_training_plan(
            db_session,
            phase.id,
            get_monday(datetime.now(UTC).date()),
            PlanData(
                raw_content=llm_response.plan,
                workout_data=workout_data,
                prompt_history=llm_response.prompt,
            ),
        )

    full_plan_text = (
        llm_response.plan
        + "\n\n"
        + "## intervals.icu workout file (txt)\n\n```text\n\n"
        + llm_json_to_icu_txt(llm_response.plan)
        + "\n```"
    )
    return {"plan": full_plan_text, "summary": full_summary, "prompt": llm_response.prompt, "plan_id": saved_plan.id}
