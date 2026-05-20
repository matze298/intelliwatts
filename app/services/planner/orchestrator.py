"""Service for generating the weekly plan."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import requests
from requests_cache import CachedSession
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.db import engine
from app.intervals.client import IntervalsClient
from app.models.plan import TrainingPlan
from app.planning.llm import LLMRole, generate_plan
from app.planning.providers.registry import registry
from app.services.coach_context import build_coach_context
from app.services.long_term_planner import (
    derive_weekly_brief,
    get_current_long_term_plan_artifact,
    get_or_create_active_phase,
)
from app.services.planner.analysis import get_analysis
from app.services.planner.persistence import save_and_stage_weekly_plan
from app.services.planner.prompt import PromptSummaryContext, build_prompt_summary
from app.utils.datetime import get_monday

if TYPE_CHECKING:
    from app.models.user import User

_get_analysis = get_analysis


async def update_training_plan(
    user: User,
    feedback: str,
    settings: Settings | None = None,
    *,
    week_start: date | None = None,
) -> dict[str, Any]:
    """Updates the training plan based on user feedback.

    Returns:
        The updated weekly plan and summary.
    """
    if settings is None:
        settings = get_settings()

    with Session(engine) as session:
        phase = get_or_create_active_phase(session, user.id)
        monday = week_start or get_monday(datetime.now(UTC).date())

        statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase.id, TrainingPlan.week_start == monday)
        plan = session.exec(statement).first()

        if not plan:
            return await generate_weekly_plan(user, settings, week_start=monday)

        history = plan.prompt_history
        history.append({"role": LLMRole.USER, "content": feedback})

        llm_response = generate_plan(messages=history, language_model=settings.LANGUAGE_MODEL, user=user)

        saved_plan_id = save_and_stage_weekly_plan(
            session=session,
            phase_id=phase.id,
            week_start=monday,
            llm_response=llm_response,
        )

    return {"plan": llm_response.plan, "plan_id": saved_plan_id, "week_start": monday}


async def generate_weekly_plan(
    user: User,
    settings: Settings | None = None,
    *,
    weekly_hours: float | None = None,
    weekly_sessions: int | None = None,
    week_start: date | None = None,
) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The generated plan payload, summary, prompt, and saved identifiers.
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

    analysis = _get_analysis(client, settings.ANALYSIS_DAYS)
    target_week_start = week_start or get_monday(datetime.now(UTC).date())

    with Session(engine) as db_session:
        phase = get_or_create_active_phase(db_session, user.id)
        artifact = get_current_long_term_plan_artifact(db_session, phase_id=phase.id)
        coach_context = build_coach_context(
            daily_records=analysis.daily_records,
            phase=phase,
            artifact=artifact,
            week_start=target_week_start,
        )
        weekly_brief = derive_weekly_brief(
            phase=phase,
            artifact=artifact,
            analysis_context=coach_context.brief_context,
            week_start=target_week_start,
        )
        specialist_text = await registry.get_specialist_context(analysis.provider_results)
        full_summary = build_prompt_summary(
            PromptSummaryContext(
                user=user,
                phase=phase,
                weekly_hours=weekly_hours,
                weekly_sessions=weekly_sessions,
                weekly_brief=weekly_brief,
                coach_text=coach_context.render(),
                specialist_text=specialist_text,
                task_prompt=settings.USER_PROMPT,
            )
        )

    llm_response = generate_plan(
        messages=[
            {"role": LLMRole.SYSTEM, "content": settings.SYSTEM_PROMPT},
            {"role": LLMRole.USER, "content": full_summary},
        ],
        language_model=settings.LANGUAGE_MODEL,
        user=user,
    )

    with Session(engine) as db_session:
        saved_plan_id = save_and_stage_weekly_plan(
            session=db_session,
            phase_id=phase.id,
            week_start=target_week_start,
            llm_response=llm_response,
        )

    return {
        "plan": llm_response.plan,
        "summary": full_summary,
        "prompt": llm_response.prompt,
        "plan_id": saved_plan_id,
        "week_start": target_week_start,
    }
