"""Web routes for the app."""

import markdown
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

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
        {"request": request, "plan_html": None},
    )


@router.post("/generate", response_class=HTMLResponse)
def generate(request: Request) -> HTMLResponse:
    """Generates the weekly plan for the athlete.

    Returns:
        The weekly plan and summary as HTML.
    """
    result = generate_weekly_plan()

    plan_html = markdown.markdown(
        result["plan"],
        extensions=["tables", "fenced_code"],
    )

    return templates.TemplateResponse(
        "plan.html",
        {
            "request": request,
            "plan_html": plan_html,
            "summary": result["summary"],
        },
    )
