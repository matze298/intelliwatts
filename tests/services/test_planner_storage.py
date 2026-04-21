"""Tests for the PlannerService storage logic."""

import uuid
from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, create_engine, select

from app.models.plan import SQLModel, TrainingPlan
from app.models.user import User
from app.services.planner import (
    PlanData,
    generate_weekly_plan,
    get_monday,
    get_or_create_active_phase,
    save_training_plan,
)

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


def test_get_monday() -> None:
    """Test get_monday returns correct Monday."""
    assert get_monday(date(2026, 4, 21)) == date(2026, 4, 20)  # Tuesday -> Monday
    assert get_monday(date(2026, 4, 20)) == date(2026, 4, 20)  # Monday -> Monday


def test_get_or_create_active_phase(session: Session) -> None:
    """Test get_or_create_active_phase creates default if none exists."""
    user_id = uuid.uuid4()
    phase = get_or_create_active_phase(session, user_id)
    assert phase.user_id == user_id
    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP (Default)"

    # Second call should return the same phase
    phase2 = get_or_create_active_phase(session, user_id)
    assert phase2.id == phase.id


def test_save_training_plan_overwrite(session: Session) -> None:
    """Test save_training_plan overwrites existing plan for the week."""
    user_id = uuid.uuid4()
    phase = get_or_create_active_phase(session, user_id)
    week_start = date(2026, 4, 20)

    # Initial save
    data = PlanData(raw_content="Old Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # Verify save
    statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase.id)
    plan = session.exec(statement).one()
    assert plan.raw_content == "Old Content"

    # Overwrite
    data = PlanData(raw_content="New Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # Verify overwrite
    plan = session.exec(statement).one()
    assert plan.raw_content == "New Content"


@patch("app.services.planner.IntervalsClient")
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.engine")
def test_generate_weekly_plan_persists(
    mock_engine: MagicMock,
    mock_generate_plan: MagicMock,
    mock_intervals_client: MagicMock,
    session: Session,
) -> None:
    """Test generate_weekly_plan persists the result."""
    # Setup mocks
    mock_engine.connect.return_value.__enter__.return_value = session.connection()

    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106

    # Mock LLM response
    mock_llm_response = MagicMock()
    mock_llm_response.plan = "Plan content ###JSON_START### [] ###JSON_END###"
    mock_llm_response.prompt = [{"role": "user", "content": "test"}]
    mock_generate_plan.return_value = mock_llm_response

    # Mock IntervalsClient to return empty data
    mock_intervals_client.return_value.activities.return_value = []
    mock_intervals_client.return_value.wellness.return_value = []
    mock_intervals_client.return_value.power_curves.return_value = {}

    # Need to mock the Session used in generate_weekly_plan to use our in-memory DB
    with patch("app.services.planner.Session", return_value=session):
        result = generate_weekly_plan(user)

    assert "plan_id" in result

    # Verify DB entry
    plan = session.exec(select(TrainingPlan)).first()
    assert plan is not None
    assert plan.id == result["plan_id"]
    assert plan.raw_content == mock_llm_response.plan
