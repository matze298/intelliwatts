"""Web routes for the app."""

from __future__ import annotations

import asyncio
import json
import logging
from copy import copy
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Annotated, NamedTuple
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from requests_cache import CachedSession
from sqlmodel import Session, select

from app.config import LanguageModel, Settings, get_settings
from app.db import engine
from app.intervals.analysis import compute_analysis
from app.intervals.client import IntervalsClient, IntervalsResponseError
from app.intervals.parser.activity import parse_activities
from app.intervals.parser.wellness import parse_wellness_list
from app.models.plan import TrainingPhase, TrainingPlan
from app.models.user import User
from app.profile import get_profile
from app.routes.planner_errors import PlannerErrorRoute
from app.services.dashboard import get_next_workout
from app.services.long_term_planner import (
    LongTermWeekOption,
    generate_long_term_plan_artifact,
    get_active_phase,
    get_current_long_term_plan_artifact,
    get_long_term_week_options,
    is_week_in_long_term_plan,
    replace_active_phase,
)
from app.services.plan_loader import load_user_plan
from app.services.planner import (
    generate_weekly_plan,
    update_training_plan,
)
from app.services.workout_delivery import publish_workout_delivery
from app.utils.datetime import get_monday
from app.utils.markdown import render_markdown

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable


router = APIRouter(tags=["web"])

planner_router = APIRouter(tags=["web"], route_class=PlannerErrorRoute)

templates = Jinja2Templates(directory="app/templates")
_LOGGER = logging.getLogger(__name__)


class WeekSelectionError(ValueError):
    """Raised when the selected week is outside the active long-term plan."""

    def __init__(self) -> None:
        """Create the standard selected-week validation error."""
        super().__init__("Selected planning week must be part of the active long-term plan.")


class WeekSelection(NamedTuple):
    """Validated selected week context for planner rendering."""

    primary_goal: str
    target_date: str
    week_options: list[LongTermWeekOption]
    selected_week_start: date | None
    error: WeekSelectionError | None


def _today() -> date:
    """Return today's UTC date for planner lifecycle validation."""
    return datetime.now(UTC).date()


def render_planner_error_response(request: Request) -> HTMLResponse:
    """Render the planner error page with the underlying error message.

    Returns:
        A 500 response with the underlying error message.
    """
    return templates.TemplateResponse(
        request,
        "planner_error.html",
        {
            "settings": request.app.state.settings,
            "user": None,
            "error": getattr(
                request.state,
                "planner_error",
                "No error details available.",
            ),
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_active_phase(session: Session, user: User | None) -> TrainingPhase | None:
    """Return the active phase for the user if one exists."""
    if not user:
        return None

    return get_active_phase(session, user.id)


def _phase_form_values(phase: TrainingPhase | None) -> tuple[str, str]:
    """Return planner form values for the active phase."""
    if not phase:
        return "", ""
    return phase.primary_goal, phase.target_date.isoformat()


def _parse_iso_date(
    raw_value: str, *, error_message: str = "Selected planning week must be a valid date."
) -> tuple[date | None, str | None]:
    """Parse an ISO date string when present.

    Returns:
        The parsed date and an error message if parsing fails.
    """
    if not raw_value:
        return None, None
    try:
        return date.fromisoformat(raw_value), None
    except ValueError:
        return None, error_message


def _parse_weekly_limits(raw_hours: object, raw_sessions: object) -> tuple[float | None, int | None, str | None]:
    """Parse weekly limit form values.

    Returns:
        The parsed hours, parsed sessions, and an error message if parsing failed.
    """
    weekly_hours: float | None = None
    weekly_sessions: int | None = None
    try:
        if isinstance(raw_hours, str) and raw_hours:
            weekly_hours = float(raw_hours)
    except ValueError:
        return None, None, "Weekly planning limits must be numbers."
    try:
        if isinstance(raw_sessions, str) and raw_sessions:
            weekly_sessions = int(raw_sessions)
    except ValueError:
        return None, None, "Weekly planning limits must be numbers."

    return weekly_hours, weekly_sessions, None


def _week_options_for_phase(session: Session, phase: TrainingPhase | None) -> list[LongTermWeekOption]:
    """Return selectable upcoming weeks for a phase."""
    if phase is None:
        return []
    artifact = get_current_long_term_plan_artifact(session, phase_id=phase.id)
    return get_long_term_week_options(phase=phase, artifact=artifact, today=_today())


def _resolve_week_selection(session: Session, user: User, raw_week_start: str) -> WeekSelection:
    """Validate a submitted planning week and return render context.

    Returns:
        The resolved long-term week selection and any validation error.
    """
    phase = _get_active_phase(session, user)
    primary_goal, target_date = _phase_form_values(phase)
    week_options = _week_options_for_phase(session, phase)
    selected_week_start = None
    if raw_week_start:
        try:
            selected_week_start = date.fromisoformat(raw_week_start)
        except ValueError:
            return WeekSelection(primary_goal, target_date, week_options, None, WeekSelectionError())
    elif week_options:
        selected_week_start = week_options[0].week_start

    artifact = get_current_long_term_plan_artifact(session, phase_id=phase.id) if phase is not None else None
    if (
        selected_week_start is None
        or phase is None
        or not is_week_in_long_term_plan(
            phase=phase,
            artifact=artifact,
            week_start=selected_week_start,
        )
    ):
        return WeekSelection(primary_goal, target_date, week_options, selected_week_start, WeekSelectionError())
    return WeekSelection(primary_goal, target_date, week_options, selected_week_start, None)


def _resolve_home_week_selection(session: Session, user: User | None, raw_week_start: str) -> WeekSelection:
    """Resolve the week context used when rendering the planner home page.

    Returns:
        The selected week, form values, week options, and any validation error.
    """
    phase = _get_active_phase(session, user)
    primary_goal, target_date = _phase_form_values(phase)
    week_options = _week_options_for_phase(session, phase)
    selected_week_start = None
    if user and raw_week_start:
        week_selection = _resolve_week_selection(session, user, raw_week_start)
        if week_selection.error:
            return WeekSelection(
                week_selection.primary_goal,
                week_selection.target_date,
                week_selection.week_options,
                None,
                week_selection.error,
            )
        return week_selection
    if user and week_options:
        selected_week_start = week_options[0].week_start
    return WeekSelection(primary_goal, target_date, week_options, selected_week_start, None)


def _settings_page_context(request: Request, user: User) -> dict[str, object]:
    """Build the settings page context for the current user.

    Returns:
        A template context dictionary for the unified settings page.
    """
    app_settings = request.app.state.settings
    prompt_settings = copy(app_settings["settings"])
    prompt_settings.SYSTEM_PROMPT = user.system_prompt_override or app_settings["settings"].SYSTEM_PROMPT
    prompt_settings.USER_PROMPT = user.user_prompt_override or app_settings["settings"].USER_PROMPT
    return {
        "user": user,
        "settings": {**app_settings, "settings": prompt_settings},
        "developer_mode_enabled": user.developer_mode_enabled,
    }


def _render_plan_page(  # ruff: ignore[too-many-arguments]
    request: Request,
    *,
    user: User | None,
    plan_html: str | None,
    long_term_summary_html: str | None,
    delivery_status: str | None,
    delivery_last_error: str | None,
    summary: str | None,
    prompt: list[dict[str, str]] | None,
    primary_goal: str = "",
    target_date: str = "",
    start_date: str | None = None,
    week_options: list[LongTermWeekOption] | None = None,
    selected_week_start: str = "",
    error: str | None = None,
    selected_model: LanguageModel | None = None,
    delivery_links: tuple[object, ...] = (),
    publish_notice: str | None = None,
) -> HTMLResponse:
    """Render the planner page with shared context.

    Returns:
        The rendered planner page.
    """
    settings_context = request.app.state.settings
    if selected_model is not None:
        settings_context = {
            **settings_context,
            "settings": settings_context["settings"].model_copy(update={"LANGUAGE_MODEL": selected_model}),
        }

    if start_date is None:
        with Session(engine) as session:
            phase = _get_active_phase(session, user)
            start_date = phase.start_date.isoformat() if phase is not None else _today().isoformat()

    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "plan_html": plan_html,
            "long_term_summary_html": long_term_summary_html,
            "delivery_status": delivery_status,
            "delivery_last_error": delivery_last_error,
            "delivery_links": delivery_links,
            "publish_notice": publish_notice,
            "summary": summary,
            "prompt": prompt,
            "primary_goal": primary_goal,
            "target_date": target_date,
            "start_date": start_date,
            "week_options": week_options or [],
            "selected_week_start": selected_week_start,
            "error": error,
            "settings": settings_context,
            "user": user,
        },
    )


def _render_invalid_model_selection(request: Request, user: User, week_start: str) -> HTMLResponse:
    """Render the planner with an error when the submitted model is unsupported.

    Returns:
        The rendered planner page.
    """
    loaded = load_user_plan(user)
    return _render_plan_page(
        request,
        user=user,
        plan_html=loaded.plan_html,
        long_term_summary_html=loaded.long_term_summary_html,
        delivery_status=loaded.delivery_status,
        delivery_last_error=loaded.delivery_last_error,
        summary=None,
        prompt=loaded.prompt,
        selected_week_start=week_start,
        error="The selected language model is not supported.",
    )


def _stream_planner_action(
    request: Request,
    user: User,
    settings: Settings,
    action: Callable[[Request, User, Settings], Awaitable[HTMLResponse]],
) -> StreamingResponse:
    """Stream real backend milestones and return rendered planner HTML when complete.

    Returns:
        A newline-delimited event stream consumed by the in-place Planner UI.
    """
    queue: asyncio.Queue[dict[str, str] | None] = asyncio.Queue()

    def progress(message: str) -> None:
        queue.put_nowait({"kind": "stage", "message": message})

    async def execute() -> None:
        request.state.planner_progress = progress
        try:
            result = await action(request, user, settings)
            queue.put_nowait({"kind": "complete", "html": bytes(result.body).decode("utf-8")})
        except Exception:
            _LOGGER.exception("Planner generation stream failed")
            queue.put_nowait({
                "kind": "error",
                "message": "Plan generation failed. Your existing plan is still available; please try again.",
            })
        finally:
            queue.put_nowait(None)

    async def events() -> AsyncIterator[str]:
        # Work continues to save or stage the plan even if a browser tab disconnects.
        task = asyncio.create_task(execute())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield "data: " + json.dumps(item, ensure_ascii=False) + chr(10) * 2
        finally:
            if task.done():
                await task

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


def _selected_language_model(value: object, default: LanguageModel) -> LanguageModel | None:
    """Parse the selected language model, returning None for unsupported values.

    Returns:
        The selected model, or None for unsupported values.
    """
    try:
        return LanguageModel(value or default)
    except ValueError:
        return None


@planner_router.get("/", response_class=HTMLResponse)
def home(request: Request, user: Annotated[User | None, Depends(get_profile)]) -> HTMLResponse:
    """Home page for the app.

    Returns:
        The home page as HTML.
    """
    plan_html = None
    long_term_summary_html = None
    prompt = None
    delivery_status = None
    delivery_last_error = None
    delivery_links: tuple[object, ...] = ()

    with Session(engine) as session:
        raw_week_start = str(request.query_params.get("week_start", "")).strip()
        week_selection = _resolve_home_week_selection(session, user, raw_week_start)
        active_phase = _get_active_phase(session, user)
        goal_start_date = active_phase.start_date.isoformat() if active_phase else _today().isoformat()

    if user:
        loaded = load_user_plan(
            user,
            week_start=week_selection.selected_week_start,
            include_weekly_plan=week_selection.error is None,
        )
        plan_html = loaded.plan_html
        long_term_summary_html = loaded.long_term_summary_html
        prompt = loaded.prompt
        delivery_status = loaded.delivery_status
        delivery_last_error = loaded.delivery_last_error
        delivery_links = getattr(loaded, "delivery_links", ())
        selected_week_start = week_selection.selected_week_start or loaded.week_start
    else:
        selected_week_start = week_selection.selected_week_start

    return _render_plan_page(
        request,
        user=user,
        plan_html=plan_html,
        long_term_summary_html=long_term_summary_html,
        delivery_status=delivery_status,
        delivery_last_error=delivery_last_error,
        delivery_links=delivery_links,
        publish_notice=request.query_params.get("publish")
        if request.query_params.get("publish") in {"success", "failed"}
        else None,
        summary=None,
        prompt=prompt,
        primary_goal=week_selection.primary_goal,
        target_date=week_selection.target_date,
        start_date=goal_start_date,
        week_options=week_selection.week_options,
        selected_week_start=selected_week_start.isoformat() if selected_week_start else "",
        error=str(week_selection.error) if week_selection.error else None,
    )


def _render_long_term_goal_error(  # ruff: ignore[too-many-arguments]
    request: Request,
    user: User,
    *,
    primary_goal: str,
    raw_start_date: str,
    raw_target_date: str,
    error: str,
) -> HTMLResponse:
    """Render a validation error without discarding the submitted goal dates.

    Returns:
        The long-term goal form with the submitted values and validation error.
    """
    return _render_plan_page(
        request,
        user=user,
        plan_html=None,
        long_term_summary_html=None,
        delivery_status=None,
        delivery_last_error=None,
        summary=None,
        prompt=None,
        primary_goal=primary_goal,
        start_date=raw_start_date,
        target_date=raw_target_date,
        week_options=[],
        error=error,
    )


@planner_router.post("/long-term-plan", response_class=HTMLResponse)
async def long_term_plan(  # ruff: ignore[too-many-return-statements, complex-structure]
    request: Request,
    user: Annotated[User, Depends(get_profile)],
) -> Response:
    """Persist a long-term goal with an optional future starting date.

    Returns:
        A redirect on success, or the form with validation errors.
    """
    input_data = await request.form()
    primary_goal = str(input_data.get("primary_goal", "")).strip()
    raw_target_date = str(input_data.get("target_date", "")).strip()
    # Missing values preserve compatibility with clients that do not send start_date.
    today = _today()
    raw_start_date = str(input_data.get("start_date", "")).strip() or today.isoformat()

    def invalid(message: str) -> HTMLResponse:
        return _render_long_term_goal_error(
            request,
            user,
            primary_goal=primary_goal,
            raw_start_date=raw_start_date,
            raw_target_date=raw_target_date,
            error=message,
        )

    if not primary_goal:
        return invalid("Primary goal is required.")

    start_date, date_error = _parse_iso_date(raw_start_date, error_message="Start date must be a valid date.")
    if date_error is not None:
        return invalid(date_error)
    if start_date is None:
        return invalid("Start date is required.")

    target_date, date_error = _parse_iso_date(raw_target_date, error_message="Target date must be a valid date.")
    if date_error is not None:
        return invalid(date_error)
    if target_date is None:
        return invalid("Target date is required.")

    if start_date < get_monday(today):
        with Session(engine) as session:
            active_phase = _get_active_phase(session, user)
        if active_phase is None or active_phase.start_date != start_date:
            return invalid("Start date must be in the current week or later.")

    if target_date < today:
        return invalid("Target date cannot be in the past.")
    if target_date <= start_date:
        return invalid("Target date must be after the start date.")

    with Session(engine) as session:
        phase = replace_active_phase(
            session,
            user_id=user.id,
            primary_goal=primary_goal,
            target_date=target_date,
            start_date=start_date,
        )
        generate_long_term_plan_artifact(session, phase=phase)
        session.commit()

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: Annotated[User, Depends(get_profile)],
    settings: Annotated[Settings, Depends(get_settings)],
    days: int | None = None,
) -> HTMLResponse:
    """Dashboard page for the app.

    Returns:
        The dashboard page as HTML.
    """
    # The normal Dashboard retains its short default window. A larger API
    # request is only issued when the athlete explicitly selects a longer range.
    display_days = max(7, min(365, days if days is not None else settings.DASHBOARD_DAYS))
    lookback_days = max(settings.ANALYSIS_DAYS, display_days)

    session = requests.Session()
    if settings.CACHE_INTERVALS_HOURS > 0:
        session = CachedSession(
            "intervals_cache",
            backend="sqlite",
            expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
        )
    elif settings.DASHBOARD_CACHE_MINUTES > 0:
        # Cache identical Intervals.icu queries across Dashboard reloads/range changes.
        # Request URLs include the oldest date, so distinct windows stay independent.
        session = CachedSession(
            "dashboard_intervals_cache",
            backend="sqlite",
            expire_after=timedelta(minutes=settings.DASHBOARD_CACHE_MINUTES),
        )

    client = IntervalsClient(
        settings.INTERVALS_API_KEY,
        settings.INTERVALS_ATHLETE_ID,
        session=session,
    )
    raw_activities = client.activities(days=lookback_days)
    activities = parse_activities(raw_activities)

    raw_wellness = client.wellness(days=lookback_days)
    wellness = parse_wellness_list(raw_wellness)

    analysis = compute_analysis(
        activities,
        display_days=display_days,
        wellness_data=wellness,
        client=client,
    )
    current_plan = load_user_plan(user)
    next_workout = get_next_workout(current_plan.workout_data, _today())

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "analysis": analysis.to_dict(),
            "display_days": display_days,
            "next_workout": next_workout,
            "has_weekly_plan": current_plan.plan_html is not None,
            "settings": request.app.state.settings,
        },
    )


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, user: Annotated[User, Depends(get_profile)]) -> HTMLResponse:
    """Settings page for the app.

    Returns:
        The settings page as HTML.
    """
    return templates.TemplateResponse(request, "settings.html", _settings_page_context(request, user))


@planner_router.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    user: Annotated[User, Depends(get_profile)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    """Generates the weekly plan for the athlete.

    Returns:
        The weekly plan and summary as HTML.
    """
    input_data = await request.form()
    raw_model = input_data.get("language_model")
    selected_model = None
    if raw_model:
        selected_model = _selected_language_model(raw_model, settings.LANGUAGE_MODEL)
        if selected_model is None:
            return _render_invalid_model_selection(request, user, str(input_data.get("week_start", "")))
        settings = settings.model_copy(update={"LANGUAGE_MODEL": selected_model})
    raw_week_start = str(input_data.get("week_start", "")).strip()

    weekly_hours, weekly_sessions, limit_error = _parse_weekly_limits(
        input_data.get("max_hours"), input_data.get("max_sessions")
    )
    if limit_error:
        loaded = load_user_plan(user)
        return _render_plan_page(
            request,
            user=user,
            plan_html=loaded.plan_html,
            long_term_summary_html=loaded.long_term_summary_html,
            delivery_status=loaded.delivery_status,
            delivery_last_error=loaded.delivery_last_error,
            summary=None,
            prompt=loaded.prompt,
            primary_goal="",
            target_date="",
            week_options=[],
            selected_week_start=raw_week_start,
            error=limit_error,
            selected_model=selected_model,
        )

    if weekly_hours is not None or weekly_sessions is not None:
        with Session(engine) as session:
            db_user = session.get(User, user.id)
            if db_user:
                if weekly_hours is not None:
                    db_user.weekly_hours = weekly_hours
                if weekly_sessions is not None:
                    db_user.weekly_sessions = weekly_sessions
                session.add(db_user)
                session.commit()
                session.refresh(db_user)
                user = db_user

    with Session(engine) as session:
        week_selection = _resolve_week_selection(session, user, raw_week_start)
        if week_selection.error:
            loaded = load_user_plan(user)
            return _render_plan_page(
                request,
                user=user,
                plan_html=loaded.plan_html,
                long_term_summary_html=loaded.long_term_summary_html,
                delivery_status=loaded.delivery_status,
                delivery_last_error=loaded.delivery_last_error,
                summary=None,
                prompt=loaded.prompt,
                primary_goal=week_selection.primary_goal,
                target_date=week_selection.target_date,
                week_options=week_selection.week_options,
                selected_week_start=raw_week_start,
                error=str(week_selection.error),
                selected_model=selected_model,
            )

    result = await generate_weekly_plan(
        user=user,
        settings=settings,
        weekly_hours=weekly_hours,
        weekly_sessions=weekly_sessions,
        week_start=week_selection.selected_week_start,
        **({"progress": request.state.planner_progress} if hasattr(request.state, "planner_progress") else {}),
    )

    plan_html = render_markdown(result["plan"])
    loaded = load_user_plan(user, week_start=result["week_start"])

    summary_html = render_markdown(str(result["summary"]))
    with Session(engine) as session:
        week_selection = _resolve_week_selection(session, user, result["week_start"].isoformat())

    return _render_plan_page(
        request,
        user=user,
        plan_html=plan_html,
        long_term_summary_html=loaded.long_term_summary_html,
        delivery_status=loaded.delivery_status,
        delivery_last_error=loaded.delivery_last_error,
        summary=summary_html,
        prompt=result["prompt"],
        primary_goal=week_selection.primary_goal,
        target_date=week_selection.target_date,
        week_options=week_selection.week_options,
        selected_week_start=result["week_start"].isoformat(),
        selected_model=selected_model,
    )


@planner_router.post("/update", response_class=HTMLResponse)
async def update(
    request: Request,
    user: Annotated[User, Depends(get_profile)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    """Updates the weekly plan based on feedback.

    Returns:
        The updated weekly plan as HTML.
    """
    input_data = await request.form()
    feedback = str(input_data.get("feedback", ""))
    raw_week_start = str(input_data.get("week_start", "")).strip()
    week_start: date | None = None

    week_start, week_error = _parse_iso_date(raw_week_start)
    if week_error:
        loaded = load_user_plan(user)
        return _render_plan_page(
            request,
            user=user,
            plan_html=loaded.plan_html,
            long_term_summary_html=loaded.long_term_summary_html,
            delivery_status=loaded.delivery_status,
            delivery_last_error=loaded.delivery_last_error,
            summary=None,
            prompt=loaded.prompt,
            primary_goal="",
            target_date="",
            week_options=[],
            selected_week_start=raw_week_start,
            error=week_error,
        )

    result = await update_training_plan(
        user=user,
        feedback=feedback,
        settings=settings,
        week_start=week_start,
        **({"progress": request.state.planner_progress} if hasattr(request.state, "planner_progress") else {}),
    )

    plan_html = render_markdown(result["plan"])
    loaded = load_user_plan(user, week_start=result["week_start"])
    primary_goal, target_date = ("", "")
    with Session(engine) as session:
        phase = _get_active_phase(session, user)
        primary_goal, target_date = _phase_form_values(phase)
        week_options = _week_options_for_phase(session, phase)

    return _render_plan_page(
        request,
        user=user,
        plan_html=plan_html,
        long_term_summary_html=loaded.long_term_summary_html,
        delivery_status=loaded.delivery_status,
        delivery_last_error=loaded.delivery_last_error,
        summary=None,
        prompt=None,
        primary_goal=primary_goal,
        target_date=target_date,
        week_options=week_options,
        selected_week_start=result["week_start"].isoformat(),
    )


@planner_router.post("/generate/stream")
async def stream_generate(
    request: Request,
    user: Annotated[User, Depends(get_profile)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """Generate a plan while streaming server-reported milestones.

    Returns:
        The progress event stream and final rendered planner response.
    """
    await request.form()
    return _stream_planner_action(request, user, settings, generate)


@planner_router.post("/update/stream")
async def stream_update(
    request: Request,
    user: Annotated[User, Depends(get_profile)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StreamingResponse:
    """Revise a plan while streaming server-reported milestones.

    Returns:
        The progress event stream and final rendered planner response.
    """
    await request.form()
    return _stream_planner_action(request, user, settings, update)


@planner_router.post("/publish-workout", response_class=HTMLResponse)
async def publish_workout(
    request: Request,
    user: Annotated[User, Depends(get_profile)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Publish the current week's staged workouts to Intervals.icu.

    Returns:
        A redirect back to the planner page or a rendered error page.

    Raises:
        HTTPException: If the current week has no active phase or no weekly plan.
    """
    input_data = await request.form()
    raw_week_start = str(input_data.get("week_start", "")).strip()
    week_start = get_monday(datetime.now(UTC).date())
    phase: TrainingPhase | None = None
    if raw_week_start:
        week_start, week_error = _parse_iso_date(raw_week_start)
        if week_error or week_start is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(WeekSelectionError()))
    else:
        week_start = get_monday(datetime.now(UTC).date())

    with Session(engine) as session:
        phase = _get_active_phase(session, user)
        if not phase:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active training phase.")
        if raw_week_start:
            week_selection = _resolve_week_selection(session, user, raw_week_start)
            if week_selection.error:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(week_selection.error))

        plan = session.exec(
            select(TrainingPlan).where(TrainingPlan.phase_id == phase.id, TrainingPlan.week_start == week_start)
        ).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No weekly training plan.")

        session_factory = requests.Session()
        if settings.CACHE_INTERVALS_HOURS > 0:
            session_factory = CachedSession(
                "intervals_cache",
                backend="sqlite",
                expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
            )
        client = IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, session=session_factory)

        try:
            publish_workout_delivery(session, plan, client)
            result = "success"
        except requests.RequestException, IntervalsResponseError:
            _LOGGER.exception("Intervals.icu workout publication failed")
            result = "failed"

    query = urlencode({"week_start": week_start.isoformat(), "publish": result})
    return RedirectResponse(url=f"/?{query}", status_code=status.HTTP_303_SEE_OTHER)
