"""Tests for planner persistence helpers."""

import uuid
from datetime import date

from sqlmodel import Session, select

from app.models.plan import TrainingPlan
from app.planning.llm import LLMResponse
from app.services.planner import PlanData, get_or_create_active_phase, save_and_stage_weekly_plan, save_training_plan


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


def test_save_and_stage_weekly_plan_persists_structured_output(session: Session) -> None:
    """Persist the narrative and structured workouts as separate plan fields."""
    # GIVEN: A phase and a typed LLM response containing both output fields.
    user_id = uuid.uuid4()
    phase = get_or_create_active_phase(session, user_id)
    workouts: list[dict[str, object]] = [
        {
            "day": "Tuesday",
            "workout_name": "Tempo",
            "description": "Steady intervals.",
            "segments": [
                {
                    "title": "Main set",
                    "repeats": 1,
                    "steps": [{"duration_m": 20, "power_pct": "85-90", "rpm": None}],
                },
            ],
        },
    ]
    response = LLMResponse(
        plan="# Readable plan",
        prompt=[{"role": "user", "content": "prompt"}],
        workouts=workouts,
    )

    # WHEN: Saving and staging the generated plan.
    saved_plan_id = save_and_stage_weekly_plan(
        session=session,
        phase_id=phase.id,
        week_start=date(2026, 6, 1),
        llm_response=response,
    )

    # THEN: The readable plan and structured workouts are persisted independently.
    plan = session.exec(select(TrainingPlan).where(TrainingPlan.id == saved_plan_id)).one()
    assert plan.raw_content == "# Readable plan"
    assert plan.workout_data == workouts
