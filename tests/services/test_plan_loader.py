"""Tests for the plan loader service."""

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from sqlmodel import Session, create_engine

from app.models.plan import SQLModel, TrainingPhase, TrainingPlan
from app.models.user import User
from app.services.plan_loader import load_user_plan

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def session() -> Generator[Session]:
    """Provides a clean in-memory database session.

    Yields:
        The database session.
    """
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_load_user_plan(session: Session) -> None:
    """Test loading a user plan for the current week."""
    # GIVEN a user and an active phase with a plan for the current week
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106
    session.add(user)

    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Test",
        start_date=date(2026, 4, 20),
        end_date=date(2026, 5, 17),
    )
    session.add(phase)

    monday = date(2026, 4, 20)
    plan = TrainingPlan(
        phase_id=phase.id,
        week_start=monday,
        raw_content="# Weekly Plan",
        prompt_history=[{"role": "user", "content": "hi"}],
    )
    session.add(plan)
    session.commit()

    # WHEN loading the user plan (mocking current date to be in that week)
    with (
        patch("app.services.plan_loader.Session", return_value=session),
        patch("app.services.plan_loader.get_utc_now") as mock_now,
    ):
        mock_now.return_value = datetime(2026, 4, 21, tzinfo=UTC)  # Tuesday
        loaded = load_user_plan(user)

    # THEN it should return the rendered HTML and prompt history
    assert loaded.plan_html is not None
    assert "<h1>Weekly Plan</h1>" in loaded.plan_html
    assert loaded.prompt == [{"role": "user", "content": "hi"}]


def test_load_user_plan_none(session: Session) -> None:
    """Test loading a user plan when none exists."""
    # GIVEN a user with no plans
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106
    session.add(user)
    session.commit()

    # WHEN loading the user plan
    with patch("app.services.plan_loader.Session", return_value=session):
        loaded = load_user_plan(user)

    # THEN it should return None values
    assert loaded.plan_html is None
    assert loaded.prompt is None
