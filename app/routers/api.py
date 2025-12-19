"""API routes for the app."""

from typing import Any

from fastapi import APIRouter

from app.services.planner import generate_weekly_plan

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/generate-plan")
def generate_plan_api() -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    return generate_weekly_plan()
