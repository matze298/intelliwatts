"""Tests for planner persistence helpers."""

import uuid
from datetime import date

from sqlmodel import Session, select

from app.models.plan import TrainingPlan
from app.services.planner import PlanData, get_or_create_active_phase, save_training_plan


def test_save_training_plan_overwrite(session: Session) -> None:
    """Test save_training_plan overwrites existing plan for the week."""
    # GIVEN: An active phase and a week start date.
    user_id = uuid.uuid4()
    phase = get_or_create_active_phase(session, user_id)
    week_start = date(2026, 4, 20)

    # WHEN: Saving an initial plan.
    data = PlanData(raw_content="Old Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # THEN: It should be stored in the database.
    statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase.id)
    plan = session.exec(statement).one()
    assert plan.raw_content == "Old Content"

    # WHEN: Saving a new plan for the same week.
    data = PlanData(raw_content="New Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # THEN: It should overwrite the existing plan.
    plan = session.exec(statement).one()
    assert plan.raw_content == "New Content"
