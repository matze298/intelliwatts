"""API routes for the app."""

from typing import Any, Annotated

from fastapi import APIRouter, Depends

from app.services.planner import generate_weekly_plan
from app.models.user import User
from app.auth.deps import get_current_user


router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(get_current_user)])


@router.post("/generate-plan")
def generate_plan_api(user: Annotated[User, Depends(get_current_user)]) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    return generate_weekly_plan(user=user)
