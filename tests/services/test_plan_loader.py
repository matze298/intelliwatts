"""Tests for the plan loader service."""

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, NamedTuple
from unittest.mock import patch

import pytest
from sqlmodel import Session, create_engine, select

from app.models.plan import (
    LongTermPlanArtifact,
    LongTermPlanBlock,
    LongTermPlanStructuredData,
    SQLModel,
    TrainingPhase,
    TrainingPlan,
)
from app.models.user import User
from app.services.plan_loader import load_user_plan

if TYPE_CHECKING:
    from collections.abc import Generator


class PlanLoaderPhaseContext(NamedTuple):
    """Persisted user and active phase for plan-loader tests."""

    user: User
    phase: TrainingPhase


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


@pytest.fixture
def phase_context(session: Session) -> PlanLoaderPhaseContext:
    """Persist a user, active phase, and long-term artifact for plan-loader tests.

    Returns:
        The persisted user and phase.
    """
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106
    session.add(user)

    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Test",
        start_date=date(2026, 4, 20),
        end_date=date(2026, 5, 17),
    )
    session.add(phase)
    long_term_blocks: list[LongTermPlanBlock] = [{"name": "Base", "focus": "Aerobic durability", "weeks": 2}]
    long_term_data: LongTermPlanStructuredData = {
        "goal": "Test",
        "start_date": "2026-04-20",
        "target_date": "2026-05-17",
        "duration_weeks": 2,
        "blocks": long_term_blocks,
    }
    session.add(
        LongTermPlanArtifact(
            phase_id=phase.id,
            structured_data=long_term_data,
            summary_markdown="# Current long-term plan",
            prompt_history=[],
            created_at=datetime(2026, 4, 22, tzinfo=UTC),
            updated_at=datetime(2026, 4, 22, tzinfo=UTC),
        )
    )
    session.commit()
    return PlanLoaderPhaseContext(user=user, phase=phase)


def test_load_user_plan(session: Session, phase_context: PlanLoaderPhaseContext) -> None:
    """Test loading a user plan for the current week."""
    # GIVEN a user and an active phase with a plan for the current week
    monday = date(2026, 4, 20)
    plan = TrainingPlan(
        phase_id=phase_context.phase.id,
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
        loaded = load_user_plan(phase_context.user)

    # THEN it should return the rendered HTML and prompt history
    assert loaded.plan_html is not None
    assert "<h1>Weekly Plan</h1>" in loaded.plan_html
    assert loaded.long_term_summary_html is not None
    assert "<h1>Current long-term plan</h1>" in loaded.long_term_summary_html
    assert loaded.prompt == [{"role": "user", "content": "hi"}]
    assert loaded.delivery_status is None
    assert loaded.delivery_last_error is None


def test_load_user_plan_for_selected_week(session: Session, phase_context: PlanLoaderPhaseContext) -> None:
    """Test loading a user plan for an explicitly selected week."""
    # GIVEN a user and an active phase with plans for two different weeks
    session.add(
        TrainingPlan(
            phase_id=phase_context.phase.id,
            week_start=date(2026, 4, 20),
            raw_content="# Current Week Plan",
            prompt_history=[],
        )
    )
    session.add(
        TrainingPlan(
            phase_id=phase_context.phase.id,
            week_start=date(2026, 4, 27),
            raw_content="# Selected Week Plan",
            prompt_history=[{"role": "user", "content": "selected"}],
        )
    )
    session.commit()

    # WHEN loading the user plan for the selected week
    with patch("app.services.plan_loader.Session", return_value=session):
        loaded = load_user_plan(phase_context.user, week_start=date(2026, 4, 27))

    # THEN it should return the selected week's rendered plan
    assert loaded.plan_html is not None
    assert "<h1>Selected Week Plan</h1>" in loaded.plan_html
    assert "Current Week Plan" not in loaded.plan_html
    assert loaded.prompt == [{"role": "user", "content": "selected"}]
    assert loaded.week_start == date(2026, 4, 27)


def test_load_user_plan_can_skip_weekly_plan(session: Session, phase_context: PlanLoaderPhaseContext) -> None:
    """Test loading only the long-term summary when weekly plan rendering is disabled."""
    # GIVEN a user and an active phase with a current weekly plan
    session.add(
        TrainingPlan(
            phase_id=phase_context.phase.id,
            week_start=date(2026, 4, 20),
            raw_content="# Current Week Plan",
            prompt_history=[],
        )
    )
    session.commit()

    # WHEN loading the user plan without weekly plan content
    with patch("app.services.plan_loader.Session", return_value=session):
        loaded = load_user_plan(phase_context.user, week_start=date(2026, 4, 20), include_weekly_plan=False)

    # THEN it should return the long-term summary without the weekly plan
    assert loaded.plan_html is None
    assert loaded.long_term_summary_html is not None
    assert "<h1>Current long-term plan</h1>" in loaded.long_term_summary_html
    assert loaded.prompt is None
    assert loaded.week_start == date(2026, 4, 20)


def test_load_user_plan_none(session: Session) -> None:
    """Test loading a user plan when none exists."""
    # GIVEN a user with no plans
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106
    session.add(user)
    session.commit()

    # WHEN loading the user plan
    with patch("app.services.plan_loader.Session", return_value=session):
        loaded = load_user_plan(user)

    # THEN it should return None values without creating a default phase
    assert loaded.plan_html is None
    assert loaded.long_term_summary_html is None
    assert loaded.prompt is None
    assert loaded.delivery_status is None
    assert loaded.delivery_last_error is None
    assert session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user.id)).all() == []
