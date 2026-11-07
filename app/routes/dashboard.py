"""Dashboard page routing and view rendering."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import Settings, get_settings
from app.models.user import User
from app.profile import get_profile
from app.services.dashboard import get_next_workout
from app.services.dashboard_data import load_dashboard_analysis
from app.services.plan_loader import load_user_plan

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")


def _today() -> date:
    """Return the current UTC date for the next-workout preview."""
    return datetime.now(UTC).date()


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
    # Fetch the requested range on demand. The loader handles cache and aggregation.
    display_days = max(7, min(365, days if days is not None else settings.DASHBOARD_DAYS))
    analysis = load_dashboard_analysis(settings, display_days=display_days)
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
