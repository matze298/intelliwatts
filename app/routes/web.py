"""Web routes for the app."""

from datetime import timedelta
from typing import Annotated

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
from app.intervals.parser.power_curve import parse_power_curves
from app.intervals.parser.wellness import parse_wellness_list
from app.models.user import User
from app.services.plan_loader import load_user_plan
from app.services.planner import (
    generate_weekly_plan,
    update_training_plan,
)

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory="app/templates")


def get_optional_user(request: Request) -> User | None:
    """Helper to get user without raising 401.

    Returns:
        The user if authenticated, else None.
    """
    return get_current_user_from_token(request, auto_error=False)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: Annotated[User | None, Depends(get_optional_user)]) -> HTMLResponse:
    """Home page for the app.

    Returns:
        The home page as HTML.
    """
    plan_html = None
    summary_html = None
    prompt = None

    if user:
        loaded = load_user_plan(user)
        plan_html = loaded.plan_html
        prompt = loaded.prompt

    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "plan_html": plan_html,
            "summary": summary_html,
            "prompt": prompt,
            "settings": request.app.state.settings,
            "user": user,
        },
    )


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

    raw_power_curves = client.power_curves(curves="90d")
    power_curves = parse_power_curves(raw_power_curves)

    analysis = compute_analysis(
        activities,
        display_days=days or settings.DASHBOARD_DAYS,
        wellness_data=wellness,
        power_curve=power_curves,
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

    result = await generate_weekly_plan(
        user=user,
        settings=settings,
        weekly_hours=weekly_hours,
        weekly_sessions=weekly_sessions,
    )

    plan_html = markdown.markdown(
        result["plan"],
        extensions=["tables", "fenced_code"],
    )

    summary_html = markdown.markdown(
        # Pretty print the dict
        f"""{result["summary"]}""",
        extensions=["tables", "fenced_code"],
    )

    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "plan_html": plan_html,
            "summary": summary_html,
            "prompt": result["prompt"],
            "settings": request.app.state.settings,
            "user": user,
        },
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

    result = await update_training_plan(user=user, feedback=feedback, settings=settings)

    plan_html = markdown.markdown(
        result["plan"],
        extensions=["tables", "fenced_code"],
    )

    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "plan_html": plan_html,
            "summary": None,
            "prompt": None,
            "settings": request.app.state.settings,
            "user": user,
        },
    )
