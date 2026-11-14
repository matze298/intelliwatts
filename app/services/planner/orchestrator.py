"""Service for generating the weekly plan."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import requests
from requests_cache import CachedSession
from sqlmodel import Session, select
from starlette.concurrency import run_in_threadpool

from app.config import LanguageModel, Settings, get_settings
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
from app.services.planner.calendar import load_week_commitments
from app.services.planner.continuity import load_previous_week_plan_context
from app.services.planner.manual import parse_manual_response
from app.services.planner.persistence import save_and_stage_weekly_plan
from app.services.planner.preferences import preferred_model
from app.services.planner.prompt import PromptSummaryContext, build_prompt_summary, workout_date_guidance
from app.utils.datetime import get_monday

if TYPE_CHECKING:
    from app.models.plan import LongTermPlanArtifact, TrainingPhase
    from app.models.user import User

_get_analysis = get_analysis

ProgressCallback = Callable[[str], None]


def _report(progress: ProgressCallback | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _make_intervals_client(settings: Settings) -> IntervalsClient:
    """Build the same Intervals client for generation and revision.

    Returns:
        An API client with the configured request cache, when enabled.
    """
    session = requests.Session()
    if settings.CACHE_INTERVALS_HOURS > 0:
        session = CachedSession(
            "intervals_cache",
            backend="sqlite",
            expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
        )
    return IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, session=session)


async def _fresh_revision_context(
    *, settings: Settings, phase: TrainingPhase, artifact: LongTermPlanArtifact | None, week_start: date
) -> str:
    """Refresh only concise completed-training, recovery and calendar context.

    Returns:
        Observations for the latest week, not a new copy of every historical prompt.
    """
    client = _make_intervals_client(settings)
    analysis = await run_in_threadpool(_get_analysis, client, settings.ANALYSIS_DAYS)
    coach = build_coach_context(
        daily_records=analysis.daily_records,
        phase=phase,
        artifact=artifact,
        week_start=week_start,
    )
    recent_rows = coach.daily_ledger[-7:]
    rows = "\n".join(
        f"- {row.date}: {row.activity_type}, {row.duration_h:.1f}h, {row.training_stress:.0f} TSS"
        for row in recent_rows
    )
    calendar = await run_in_threadpool(
        load_week_commitments, client, week_start=week_start, today=datetime.now(UTC).date()
    )
    return f"{coach.brief_context}\nLast recorded 7 days:\n{rows or '- No completed activity records.'}\n{calendar}"


async def update_training_plan(  # ruff: ignore[too-many-arguments]
    user: User,
    feedback: str,
    settings: Settings | None = None,
    *,
    week_start: date | None = None,
    progress: ProgressCallback | None = None,
    prompt_only: bool = False,
    manual_response: str | None = None,
) -> dict[str, Any]:
    """Updates the training plan based on user feedback.

    Returns:
        The updated weekly plan and summary.

    Raises:
        ValueError: If manual mode is selected without a pasted response.
    """
    if settings is None:
        settings = get_settings()
    if user.preferred_language_model:
        settings = settings.model_copy(
            update={"LANGUAGE_MODEL": preferred_model(user.preferred_language_model, settings.LANGUAGE_MODEL)}
        )

    _report(progress, "Loading the current training week")
    with Session(engine) as session:
        phase = get_or_create_active_phase(session, user.id)
        monday = week_start or get_monday(datetime.now(UTC).date())

        statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase.id, TrainingPlan.week_start == monday)
        plan = session.exec(statement).first()

        if not plan:
            if prompt_only or manual_response is not None:
                return await generate_weekly_plan(
                    user,
                    settings,
                    week_start=monday,
                    progress=progress,
                    prompt_only=prompt_only,
                    manual_response=manual_response,
                )
            if progress is not None:
                return await generate_weekly_plan(user, settings, week_start=monday, progress=progress)
            return await generate_weekly_plan(user, settings, week_start=monday)

        history = [
            *plan.prompt_history,
            {
                "role": LLMRole.ASSISTANT,
                "content": json.dumps(
                    {"plan_markdown": plan.raw_content, "workouts": plan.workout_data},
                    ensure_ascii=False,
                ),
            },
        ]
        date_rules = workout_date_guidance(
            week_start=monday,
            today=datetime.now(UTC).date(),
            existing_plan=True,
            phase_start=phase.start_date,
        )
        artifact = get_current_long_term_plan_artifact(session, phase_id=phase.id)
        preceding_plan = load_previous_week_plan_context(session=session, phase_id=phase.id, week_start=monday)

    # Release the database session before slow Intervals.icu and model calls.
    _report(progress, "Refreshing training, recovery and scheduled activities")
    try:
        latest_context = await _fresh_revision_context(
            settings=settings,
            phase=phase,
            artifact=artifact,
            week_start=monday,
        )
    except requests.RequestException, ValueError:
        # Keep revising saved plans if Intervals.icu is temporarily unavailable.
        latest_context = "Fresh Intervals.icu context unavailable; use saved plan and athlete feedback."
    history.append({
        "role": LLMRole.USER,
        "content": (
            f"{feedback}\n\n"
            f"Latest recorded context (supersedes older observations):\n{latest_context}\n\n"
            f"{date_rules}\n\n"
            f"{preceding_plan + chr(10) + chr(10) if preceding_plan else ''}"
            f"Available cycling days: {', '.join(user.available_cycling_days)}; "
            f"at most {user.weekly_sessions} cycling sessions and {user.weekly_hours} cycling hours. "
            "Other sports affect recovery/timing, never the cycling budget. "
            "Keep past workouts unchanged; only NEW workouts must use an available day."
        ),
    })

    if prompt_only:
        return {"prompt": history, "week_start": monday}
    if manual_response is not None:
        _report(progress, "Validating the pasted revision")
        llm_response = parse_manual_response(manual_response, messages=history, week_start=monday)
    else:
        if settings.LANGUAGE_MODEL == LanguageModel.MANUAL:
            msg = "Manual mode requires a pasted LLM response."
            raise ValueError(msg)
        _report(progress, "Requesting a revised plan from the selected model")
        llm_response = await run_in_threadpool(
            generate_plan,
            messages=history,
            language_model=settings.LANGUAGE_MODEL,
        )

    _report(progress, "Saving the revision and staging workouts")
    with Session(engine) as session:
        saved_plan_id = save_and_stage_weekly_plan(
            session=session,
            phase_id=phase.id,
            week_start=monday,
            llm_response=llm_response,
        )

    _report(progress, "Revised plan ready for review")
    return {"plan": llm_response.plan, "plan_id": saved_plan_id, "week_start": monday}


async def generate_weekly_plan(  # ruff: ignore[too-many-arguments]
    user: User,
    settings: Settings | None = None,
    *,
    weekly_hours: float | None = None,
    weekly_sessions: int | None = None,
    week_start: date | None = None,
    progress: ProgressCallback | None = None,
    prompt_only: bool = False,
    manual_response: str | None = None,
) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The generated plan payload, summary, prompt, and saved identifiers.

    Raises:
        ValueError: If manual mode is selected without a pasted response.
    """
    if settings is None:
        settings = get_settings()
    prompt_updates = {}
    if user.preferred_language_model:
        prompt_updates["LANGUAGE_MODEL"] = preferred_model(user.preferred_language_model, settings.LANGUAGE_MODEL)
    if user.system_prompt_override is not None:
        prompt_updates["SYSTEM_PROMPT"] = user.system_prompt_override
    if user.user_prompt_override is not None:
        prompt_updates["USER_PROMPT"] = user.user_prompt_override
    if prompt_updates:
        settings = settings.model_copy(update=prompt_updates)

    client = _make_intervals_client(settings)

    _report(progress, "Retrieving recent training and recovery data")
    analysis = await run_in_threadpool(_get_analysis, client, settings.ANALYSIS_DAYS)
    week_start = week_start or get_monday(datetime.now(UTC).date())

    _report(progress, "Building goals, availability, and training constraints")
    with Session(engine) as db_session:
        phase = get_or_create_active_phase(db_session, user.id)
        artifact = get_current_long_term_plan_artifact(db_session, phase_id=phase.id)
        coach_context = build_coach_context(
            daily_records=analysis.daily_records,
            phase=phase,
            artifact=artifact,
            week_start=week_start,
        )
        weekly_brief = derive_weekly_brief(
            phase=phase,
            artifact=artifact,
            analysis_context=coach_context.brief_context,
            week_start=week_start,
        )
        specialist_text = await registry.get_specialist_context(analysis.provider_results)
        full_summary = build_prompt_summary(
            PromptSummaryContext(
                user=user,
                phase=phase,
                weekly_hours=weekly_hours,
                weekly_sessions=weekly_sessions,
                weekly_brief=weekly_brief,
                coach_text="\n\n".join(
                    filter(
                        None,
                        (
                            coach_context.render(),
                            load_previous_week_plan_context(
                                session=db_session, phase_id=phase.id, week_start=week_start
                            ),
                        ),
                    )
                ),
                specialist_text=specialist_text,
                task_prompt=settings.USER_PROMPT,
            )
        )

    _report(progress, "Checking upcoming sports and race commitments")
    # Add date rules even when athletes override the default coach prompt.
    full_summary = (
        f"{full_summary}\n\n"
        + workout_date_guidance(
            week_start=week_start,
            today=datetime.now(UTC).date(),
            existing_plan=False,
            phase_start=phase.start_date,
        )
        + "\n\n"
        + await run_in_threadpool(load_week_commitments, client, week_start=week_start, today=datetime.now(UTC).date())
    )

    messages = [
        {"role": LLMRole.SYSTEM, "content": settings.SYSTEM_PROMPT},
        {"role": LLMRole.USER, "content": full_summary},
    ]
    if prompt_only:
        return {"summary": full_summary, "prompt": messages, "week_start": week_start}

    if manual_response is not None:
        _report(progress, "Validating the pasted structured workouts")
        llm_response = parse_manual_response(manual_response, messages=messages, week_start=week_start)
    else:
        if settings.LANGUAGE_MODEL == LanguageModel.MANUAL:
            msg = "Manual mode requires a pasted LLM response."
            raise ValueError(msg)
        _report(progress, "Requesting structured workouts from the selected model")
        llm_response = await run_in_threadpool(
            generate_plan,
            messages=messages,
            language_model=settings.LANGUAGE_MODEL,
        )

    _report(progress, "Validating and saving the generated workouts")
    with Session(engine) as db_session:
        saved_plan_id = save_and_stage_weekly_plan(
            session=db_session,
            phase_id=phase.id,
            week_start=week_start,
            llm_response=llm_response,
        )

    _report(progress, "Plan saved and ready to review")
    return {
        "plan": llm_response.plan,
        "summary": full_summary,
        "prompt": llm_response.prompt,
        "plan_id": saved_plan_id,
        "week_start": week_start,
    }
