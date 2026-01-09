"""Web routes for the app."""

from typing import Annotated

import markdown
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth.deps import get_current_user
from app.config import GLOBAL_SETTINGS
from app.models.user import User
from app.services.planner import generate_weekly_plan

router = APIRouter(tags=["web"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """Home page for the app.

    Returns:
        The home page as HTML.
    """
    return templates.TemplateResponse(
        "plan.html",
        {"request": request, "plan_html": None, "summary": None, "settings": request.app.state.settings},
    )


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
