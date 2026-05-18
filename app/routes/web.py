"""Web routes for the app."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, NamedTuple

import markdown
import requests
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from requests_cache import CachedSession
from sqlmodel import Session, select

from app.auth.auth import (
    create_access_token,
    get_current_user_from_token,
    hash_password,
    verify_password,
)
from app.config import Settings, get_settings
from app.db import engine
from app.intervals.analysis import compute_analysis
from app.intervals.client import IntervalsClient
from app.intervals.parser.activity import parse_activities
from app.intervals.parser.wellness import parse_wellness_list
from app.models.plan import TrainingPhase, TrainingPlan
from app.models.user import User
from app.services.long_term_planner import (
    LongTermWeekOption,
    generate_long_term_plan_artifact,
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

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory="app/templates")


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


def get_optional_user(request: Request) -> User | None:
    """Helper to get user without raising 401.

    Returns:
        The user if authenticated, else None.
    """
    return get_current_user_from_token(request, auto_error=False)


def _get_active_phase(session: Session, user: User | None) -> TrainingPhase | None:
    """Return the active phase for the user if one exists."""
    if not user:
        return None

    return session.exec(
        select(TrainingPhase).where(TrainingPhase.user_id == user.id, TrainingPhase.status == "active")
    ).first()


def _phase_form_values(phase: TrainingPhase | None) -> tuple[str, str]:
    """Return planner form values for the active phase."""
    if not phase:
        return "", ""
    return phase.primary_goal, phase.target_date.isoformat()


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


def _render_publish_workout_error_page(
    request: Request,
    *,
    user: User,
    phase: TrainingPhase,
    error: str,
) -> HTMLResponse:
    """Render the planner page after a workout publish failure.

    Returns:
        The rendered planner page with the publish error.
    """
    loaded = load_user_plan(user)
    primary_goal, target_date = _phase_form_values(phase)
    return _render_plan_page(
        request,
        user=user,
        plan_html=loaded.plan_html,
        long_term_summary_html=loaded.long_term_summary_html,
        delivery_status=loaded.delivery_status,
        delivery_last_error=loaded.delivery_last_error,
        summary=None,
        prompt=loaded.prompt,
        primary_goal=primary_goal,
        target_date=target_date,
        error=error,
    )


def _render_plan_page(  # noqa: PLR0913
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
    week_options: list[LongTermWeekOption] | None = None,
    selected_week_start: str = "",
    error: str | None = None,
) -> HTMLResponse:
    """Render the planner page with shared context.

    Returns:
        The rendered planner page.
    """
    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "plan_html": plan_html,
            "long_term_summary_html": long_term_summary_html,
            "delivery_status": delivery_status,
            "delivery_last_error": delivery_last_error,
            "summary": summary,
            "prompt": prompt,
            "primary_goal": primary_goal,
            "target_date": target_date,
            "week_options": week_options or [],
            "selected_week_start": selected_week_start,
            "error": error,
            "settings": request.app.state.settings,
            "user": user,
        },
    )


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: Annotated[User | None, Depends(get_optional_user)]) -> HTMLResponse:
    """Home page for the app.

    Returns:
        The home page as HTML.
    """
    plan_html = None
    long_term_summary_html = None
    prompt = None
    delivery_status = None
    delivery_last_error = None
    primary_goal = ""
    target_date = ""

    with Session(engine) as session:
        phase = _get_active_phase(session, user)
        primary_goal, target_date = _phase_form_values(phase)
        week_options = _week_options_for_phase(session, phase)

    if user:
        loaded = load_user_plan(user)
        plan_html = loaded.plan_html
        long_term_summary_html = loaded.long_term_summary_html
        prompt = loaded.prompt
        delivery_status = loaded.delivery_status
        delivery_last_error = loaded.delivery_last_error

    return _render_plan_page(
        request,
        user=user,
        plan_html=plan_html,
        long_term_summary_html=long_term_summary_html,
        delivery_status=delivery_status,
        delivery_last_error=delivery_last_error,
        summary=None,
        prompt=prompt,
        primary_goal=primary_goal,
        target_date=target_date,
        week_options=week_options,
    )


@router.post("/long-term-plan", response_class=HTMLResponse)
async def long_term_plan(
    request: Request,
    user: Annotated[User, Depends(get_current_user_from_token)],
) -> Response:
    """Persist a long-term planning goal and render the planner page.

    Returns:
        A redirect on success or the rendered planner page on validation errors.
    """
    input_data = await request.form()
    primary_goal = str(input_data.get("primary_goal", "")).strip()
    raw_target_date = str(input_data.get("target_date", "")).strip()

    if not primary_goal:
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
            target_date=raw_target_date,
            week_options=[],
            error="Primary goal is required.",
        )

    if not raw_target_date:
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
            target_date=raw_target_date,
            week_options=[],
            error="Target date is required.",
        )

    try:
        target_date = date.fromisoformat(raw_target_date)
    except ValueError:
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
            target_date=raw_target_date,
            week_options=[],
            error="Target date must be a valid date.",
        )

    start_date = _today()
    if target_date < start_date:
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
            target_date=raw_target_date,
            week_options=[],
            error="Target date cannot be in the past.",
        )

    if target_date <= start_date:
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
            target_date=raw_target_date,
            week_options=[],
            error="Target date must be after the start date.",
        )

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
    user: Annotated[User, Depends(get_current_user_from_token)],
    settings: Annotated[Settings, Depends(get_settings)],
    days: int | None = None,
) -> HTMLResponse:
    """Dashboard page for the app.

    Returns:
        The dashboard page as HTML.
    """
    session = requests.Session()
    if settings.CACHE_INTERVALS_HOURS > 0:
        session = CachedSession(
            "intervals_cache",
            backend="sqlite",
            expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
        )

    client = IntervalsClient(
        settings.INTERVALS_API_KEY,
        settings.INTERVALS_ATHLETE_ID,
        session=session,
    )
    # Fetch and parse data
    raw_activities = client.activities(days=settings.ANALYSIS_DAYS)
    activities = parse_activities(raw_activities)

    raw_wellness = client.wellness(days=settings.ANALYSIS_DAYS)
    wellness = parse_wellness_list(raw_wellness)

    analysis = compute_analysis(
        activities,
        display_days=days or settings.DASHBOARD_DAYS,
        wellness_data=wellness,
        client=client,
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "analysis": analysis.to_dict(),
            "settings": request.app.state.settings,
        },
    )


@router.get("/register", response_class=HTMLResponse)
def register(request: Request) -> HTMLResponse:
    """Register page for the app.

    Returns:
        The register page as HTML.
    """
    return templates.TemplateResponse(request, "register.html", {"user": None})


# TODO(mr): Extract common code between web.py and auth.py #noqa: TD003
@router.post("/register", response_class=Response)
async def register_post(request: Request) -> Response:
    """Handle register form submission.

    Args:
        request: The FastAPI request object.

    Returns:
        The response after registration.

    Raises:
        HTTPException: If the user already exists.
    """
    form = await request.form()
    email = form.get("email")
    password = form.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        msg = "Email and password must be strings."
        return templates.TemplateResponse(request, "register.html", {"user": None, "error": msg})

    try:
        with Session(engine) as session:
            existing = session.exec(select(User).where(User.email == email)).first()
            if existing:
                raise HTTPException(400, "User exists")

            user = User(email=email, password_hash=hash_password(password))
            session.add(user)
            session.commit()

    except Exception as e:  # noqa: BLE001
        return templates.TemplateResponse(request, "register.html", {"user": None, "error": str(e)})

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
def login(request: Request) -> HTMLResponse:
    """Login page for the app.

    Returns:
        The login page as HTML.
    """
    return templates.TemplateResponse(request, "login.html", {"user": None})


# TODO(mr): Extract common code between web.py and auth.py #noqa: TD003
@router.post("/login", response_class=Response)
async def login_post(request: Request) -> Response:
    """Handle login form submission.

    Args:
        request: The FastAPI request object.

    Returns:
        The response after login.

    Raises:
        HTTPException: If the user does not exist or the password is incorrect.
    """
    form = await request.form()
    email = form.get("email")
    password = form.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        msg = "Email and password must be strings."
        return templates.TemplateResponse(request, "login.html", {"user": None, "error": msg})

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token}",
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout() -> RedirectResponse:
    """Logout the user.

    Returns:
        The logout response.
    """
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response


@router.get("/secrets", response_class=HTMLResponse)
def secrets(request: Request, user: Annotated[User, Depends(get_current_user_from_token)]) -> HTMLResponse:
    """Secrets page for the app.

    Returns:
        The secrets page as HTML.
    """
    return templates.TemplateResponse(request, "secrets.html", {"user": user})


@router.post("/generate", response_class=HTMLResponse)
async def generate(
    request: Request,
    user: Annotated[User, Depends(get_current_user_from_token)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    """Generates the weekly plan for the athlete.

    Returns:
        The weekly plan and summary as HTML.
    """
    input_data = await request.form()

    # Training constraints from form
    raw_hours = input_data.get("max_hours")
    raw_sessions = input_data.get("max_sessions")
    raw_week_start = str(input_data.get("week_start", "")).strip()

    weekly_hours: float | None = None
    if isinstance(raw_hours, str) and raw_hours:
        weekly_hours = float(raw_hours)

    weekly_sessions: int | None = None
    if isinstance(raw_sessions, str) and raw_sessions:
        weekly_sessions = int(raw_sessions)

    # Persist the preferences if provided
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
            )

    result = await generate_weekly_plan(
        user=user,
        settings=settings,
        weekly_hours=weekly_hours,
        weekly_sessions=weekly_sessions,
        week_start=week_selection.selected_week_start,
    )

    plan_html = markdown.markdown(
        result["plan"],
        extensions=["tables", "fenced_code"],
    )
    loaded = load_user_plan(user)

    summary_html = markdown.markdown(
        # Pretty print the dict
        f"""{result["summary"]}""",
        extensions=["tables", "fenced_code"],
    )
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
    )


@router.post("/update", response_class=HTMLResponse)
async def update(
    request: Request,
    user: Annotated[User, Depends(get_current_user_from_token)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HTMLResponse:
    """Updates the weekly plan based on feedback.

    Returns:
        The updated weekly plan as HTML.
    """
    input_data = await request.form()
    feedback = str(input_data.get("feedback", ""))
    raw_week_start = str(input_data.get("week_start", "")).strip()
    week_start = date.fromisoformat(raw_week_start) if raw_week_start else None

    result = await update_training_plan(user=user, feedback=feedback, settings=settings, week_start=week_start)

    plan_html = markdown.markdown(
        result["plan"],
        extensions=["tables", "fenced_code"],
    )
    loaded = load_user_plan(user)
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


@router.post("/publish-workout", response_class=HTMLResponse)
async def publish_workout(
    request: Request,
    user: Annotated[User, Depends(get_current_user_from_token)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Publish the current week's staged workouts to Intervals.icu.

    Returns:
        A redirect back to the planner page or a rendered error page.

    Raises:
        HTTPException: If the current week has no active phase or no weekly plan.
    """
    with Session(engine) as session:
        phase = _get_active_phase(session, user)
        if not phase:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active training phase.")

        monday = get_monday(datetime.now(UTC).date())
        plan = session.exec(
            select(TrainingPlan).where(TrainingPlan.phase_id == phase.id, TrainingPlan.week_start == monday)
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
        except Exception as exc:  # noqa: BLE001
            return _render_publish_workout_error_page(
                request,
                user=user,
                phase=phase,
                error=f"Failed to publish workouts: {exc}",
            )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
