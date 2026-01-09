"""Web routes for the app."""

from typing import Annotated

import markdown
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth.auth import create_access_token, hash_password, verify_password
from app.auth.deps import get_current_user
from app.config import GLOBAL_SETTINGS
from app.db import engine
from app.models.user import User
from app.services.planner import generate_weekly_plan

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: User | None = Depends(get_current_user)) -> HTMLResponse:
    """Home page for the app.

    Returns:
        The home page as HTML.
    """
    return templates.TemplateResponse(
        "plan.html",
        {
            "request": request,
            "plan_html": None,
            "summary": None,
            "settings": request.app.state.settings,
            "user": user,
        },
    )


@router.get("/register", response_class=HTMLResponse)
def register(request: Request) -> HTMLResponse:
    """Register page for the app.

    Returns:
        The register page as HTML.
    """
    return templates.TemplateResponse("register.html", {"request": request, "user": None})


# TODO(mr): Extract common code between web.py and auth.py
@router.post("/register", response_class=Response)
async def register_post(request: Request) -> Response:
    """Handle register form submission."""
    form = await request.form()
    email = form.get("email")
    password = form.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        msg = "Email and password must be strings."
        return templates.TemplateResponse("register.html", {"request": request, "user": None, "error": msg})

    try:
        with Session(engine) as session:
            existing = session.exec(select(User).where(User.email == email)).first()
            if existing:
                raise HTTPException(400, "User exists")

            user = User(email=email, password_hash=hash_password(password))
            session.add(user)
            session.commit()

    except Exception as e:
        return templates.TemplateResponse("register.html", {"request": request, "user": None, "error": str(e)})

    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
def login(request: Request) -> HTMLResponse:
    """Login page for the app.

    Returns:
        The login page as HTML.
    """
    return templates.TemplateResponse("login.html", {"request": request, "user": None})


# TODO(mr): Extract common code between web.py and auth.py
@router.post("/login", response_class=Response)
async def login_post(request: Request) -> Response:
    """Handle login form submission."""
    form = await request.form()
    email = form.get("email")
    password = form.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        msg = "Email and password must be strings."
        return templates.TemplateResponse("login.html", {"request": request, "user": None, "error": msg})

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
def secrets(request: Request, user: Annotated[User, Depends(get_current_user)]) -> HTMLResponse:
    """Secrets page for the app.

    Returns:
        The secrets page as HTML.
    """
    return templates.TemplateResponse("secrets.html", {"request": request, "user": user})


@router.post("/generate", response_class=HTMLResponse)
async def generate(request: Request, user: Annotated[User, Depends(get_current_user)]) -> HTMLResponse:
    """Generates the weekly plan for the athlete.

    Returns:
        The weekly plan and summary as HTML.
    """
    input_data = await request.form()
    GLOBAL_SETTINGS.update(
        LANGUAGE_MODEL=str(input_data.get("language_model", GLOBAL_SETTINGS.LANGUAGE_MODEL)),
        SYSTEM_PROMPT=str(input_data.get("system_prompt", GLOBAL_SETTINGS.SYSTEM_PROMPT)),
        USER_PROMPT=str(input_data.get("user_prompt", GLOBAL_SETTINGS.USER_PROMPT)),
        weekly_hours=input_data.get("max_hours", GLOBAL_SETTINGS.weekly_hours),
        weekly_sessions=input_data.get("max_sessions", GLOBAL_SETTINGS.weekly_sessions),
    )

    result = generate_weekly_plan(settings=GLOBAL_SETTINGS, user=user)

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
        "plan.html",
        {
            "request": request,
            "plan_html": plan_html,
            "summary": summary_html,
            "settings": request.app.state.settings,
        },
    )
