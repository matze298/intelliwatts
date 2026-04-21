"""Tests for the training plan iterative updates."""

import uuid
from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, create_engine, select

from app.models.plan import SQLModel, TrainingPhase, TrainingPlan
from app.models.user import User
from app.services.planner import PlanData, save_training_plan, update_training_plan

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture
def session() -> Generator[Session]:
    """Provides a clean in-memory database session.

    Yields:
        The database session.
    """
    engine: Engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@patch("app.services.planner.generate_plan")
def test_update_training_plan_uses_history(mock_generate_plan: MagicMock, session: Session) -> None:
    """Test update_training_plan retrieves history and calls LLM with it."""
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106
    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Test",
        start_date=date(2026, 4, 20),
        end_date=date(2026, 5, 17),
    )
    session.add(phase)
    session.commit()

    monday = date(2026, 4, 20)
    initial_history = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    data = PlanData(raw_content="Initial Plan", workout_data=[], prompt_history=initial_history)
    save_training_plan(session, phase.id, monday, data)

    # Mock LLM response for update
    mock_llm_response = MagicMock()
    mock_llm_response.plan = "Updated Plan ###JSON_START### [] ###JSON_END###"
    mock_llm_response.prompt = [
        *initial_history,
        {"role": "user", "content": "make it harder"},
        {"role": "assistant", "content": "ok"},
    ]
    mock_generate_plan.return_value = mock_llm_response

    with (
        patch("app.services.planner.Session", return_value=session),
        patch("app.services.planner.get_monday", return_value=monday),
    ):
        update_training_plan(user, "make it harder")

    # Verify generate_plan was called with history
    mock_generate_plan.assert_called_once()
    passed_messages = mock_generate_plan.call_args.kwargs["messages"]
    assert len(passed_messages) == 3
    assert passed_messages[2]["content"] == "make it harder"

    # Verify plan was updated in DB
    plan = session.exec(select(TrainingPlan)).one()
    assert "Updated Plan" in plan.raw_content
    assert len(plan.prompt_history) == 4
