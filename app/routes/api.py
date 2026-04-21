"""API routes for the app."""

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.auth import get_current_user_from_token
from app.services.planner import generate_weekly_plan, update_training_plan

if TYPE_CHECKING:
    from app.models.user import User

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(get_current_user_from_token)])


class UpdatePlanRequest(BaseModel):
    """Request model for updating a training plan."""

    feedback: str


@router.post("/generate-plan")
def generate_plan_api(user: Annotated[User, Depends(get_current_user_from_token)]) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    return generate_weekly_plan(user=user)


@router.post("/update-plan")
def update_plan_api(
    request: UpdatePlanRequest, user: Annotated[User, Depends(get_current_user_from_token)]
) -> dict[str, Any]:
    """Updates the training plan based on feedback.

    Returns:
        The updated weekly plan and summary.
    """
    return update_training_plan(user=user, feedback=request.feedback)
