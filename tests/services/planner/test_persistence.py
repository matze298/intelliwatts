"""Tests for planner persistence helpers."""

import logging
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.models.plan import TrainingPlan
from app.planning.llm import LLMResponse
from app.services.planner import PlanData, get_or_create_active_phase, save_and_stage_weekly_plan, save_training_plan

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


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


def test_save_and_stage_weekly_plan_logs_malformed_workout_json(
    session: Session,
    caplog: LogCaptureFixture,
) -> None:
    """Malformed structured LLM output should persist the plan with empty workout data."""
    # GIVEN: A phase and an LLM response with malformed structured workout JSON.
    user_id = uuid.uuid4()
    phase = get_or_create_active_phase(session, user_id)
    response = LLMResponse(
        plan='Readable plan###JSON_START###{"workout_name": "not-a-list"}###JSON_END###',
        prompt=[{"role": "user", "content": "prompt"}],
    )

    # WHEN: Saving and staging the generated plan.
    with caplog.at_level(logging.WARNING):
        saved_plan_id = save_and_stage_weekly_plan(
            session=session,
            phase_id=phase.id,
            week_start=date(2026, 6, 1),
            llm_response=response,
        )

    # THEN: The readable plan is preserved and structured workouts fall back to empty.
    plan = session.exec(select(TrainingPlan).where(TrainingPlan.id == saved_plan_id)).one()
    assert plan.raw_content.startswith("Readable plan")
    assert plan.workout_data == []
    assert "Ignoring malformed workout JSON payload" in caplog.text
