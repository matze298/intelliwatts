"""API routes for the app."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from requests_cache import CachedSession
from sqlmodel import Session, select

from app.auth.auth import get_current_user_from_token
from app.config import Settings, get_settings
from app.db import engine
from app.intervals.client import IntervalsClient
from app.models.plan import TrainingPlan
from app.services.long_term_planner import generate_long_term_plan_for_user
from app.services.planner import generate_weekly_plan, get_or_create_active_phase, update_training_plan
from app.services.workout_delivery import publish_workout_delivery
from app.utils.datetime import get_monday

if TYPE_CHECKING:
    from app.models.user import User

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(get_current_user_from_token)])


class UpdatePlanRequest(BaseModel):
    """Request model for updating a training plan."""

    feedback: str


@router.post("/generate-plan")
async def generate_plan_api(user: Annotated[User, Depends(get_current_user_from_token)]) -> dict[str, Any]:
    """Generates the weekly plan.

    Returns:
        The weekly plan and summary.
    """
    return await generate_weekly_plan(user=user)


@router.post("/update-plan")
async def update_plan_api(
    request: UpdatePlanRequest, user: Annotated[User, Depends(get_current_user_from_token)]
) -> dict[str, Any]:
    """Updates the training plan based on feedback.

    Returns:
        The updated weekly plan and summary.
    """
    return await update_training_plan(user=user, feedback=request.feedback)


@router.post("/long-term-plan")
async def create_long_term_plan_api(user: Annotated[User, Depends(get_current_user_from_token)]) -> dict[str, Any]:
    """Creates a long-term artifact for the user's active phase.

    Returns:
        The created long-term artifact payload.
    """
    return generate_long_term_plan_for_user(user)


@router.post("/long-term-plan/regenerate")
async def regenerate_long_term_plan_api(user: Annotated[User, Depends(get_current_user_from_token)]) -> dict[str, Any]:
    """Regenerates the long-term artifact for the user's active phase.

    Returns:
        The regenerated long-term artifact payload.
    """
    return generate_long_term_plan_for_user(user)


@router.post("/publish-workout")
async def publish_workout_api(
    user: Annotated[User, Depends(get_current_user_from_token)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """Publish the current weekly workout draft to Intervals.icu.

    Returns:
        A compact delivery status payload.

    Raises:
        HTTPException: If the current week has no training plan to publish.
    """
    session = requests.Session()
    if settings.CACHE_INTERVALS_HOURS > 0:
        session = CachedSession(
            "intervals_cache",
            backend="sqlite",
            expire_after=timedelta(hours=settings.CACHE_INTERVALS_HOURS),
        )
    client = IntervalsClient(settings.INTERVALS_API_KEY, settings.INTERVALS_ATHLETE_ID, session=session)

    with Session(engine) as db_session:
        phase = get_or_create_active_phase(db_session, user.id)
        monday = get_monday(datetime.now(UTC).date())
        plan = db_session.exec(
            select(TrainingPlan).where(TrainingPlan.phase_id == phase.id, TrainingPlan.week_start == monday)
        ).first()
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No weekly plan exists to publish.")

        delivery = publish_workout_delivery(db_session, plan, client)

    return {"delivery_id": str(delivery.id), "status": delivery.status, "published_at": delivery.published_at}
