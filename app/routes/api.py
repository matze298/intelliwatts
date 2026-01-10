"""API routes for the app."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.auth.auth import get_current_user_from_token
from app.models.user import User
from app.services.planner import generate_weekly_plan

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(get_current_user_from_token)])


@router.post("/generate-plan")
def generate_plan_api(user: Annotated[User, Depends(get_current_user_from_token)]) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    return generate_weekly_plan(user=user)
