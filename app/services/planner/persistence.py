"""Persistence helpers for weekly planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.models.plan import TrainingPlan
from app.planning.intervals_payload import extract_workout_json
from app.services.workout_delivery import stage_workout_delivery

if TYPE_CHECKING:
    from uuid import UUID

    from app.planning.llm import LLMResponse


@dataclass
class PlanData:
    """Container for plan content and structured data."""

    raw_content: str
    workout_data: list[dict[str, object]]
    prompt_history: list[dict[str, str]]


def save_training_plan(
    session: Session,
    phase_id: UUID,
    week_start: date,
    data: PlanData,
) -> TrainingPlan:
    """Save the training plan to the database, overwriting if it exists for that week.

    Returns:
        The persisted training plan row.
    """
    statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase_id, TrainingPlan.week_start == week_start)
    plan = session.exec(statement).first()
    if plan:
        plan.raw_content = data.raw_content
        plan.workout_data = data.workout_data
        plan.prompt_history = data.prompt_history
        plan.updated_at = datetime.now(UTC)
    else:
        plan = TrainingPlan(
            phase_id=phase_id,
            week_start=week_start,
            raw_content=data.raw_content,
            workout_data=data.workout_data,
            prompt_history=data.prompt_history,
        )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def save_and_stage_weekly_plan(
    *,
    session: Session,
    phase_id: UUID,
    week_start: date,
    llm_response: LLMResponse,
) -> UUID:
    """Persist a generated weekly plan and stage its workout delivery.

    Returns:
        The saved training plan id.
    """
    workout_data = extract_workout_json(llm_response.plan)
    saved_plan = save_training_plan(
        session,
        phase_id,
        week_start,
        PlanData(
            raw_content=llm_response.plan,
            workout_data=workout_data,
            prompt_history=llm_response.prompt,
        ),
    )
    saved_plan_id = saved_plan.id
    stage_workout_delivery(session, saved_plan)
    return saved_plan_id
