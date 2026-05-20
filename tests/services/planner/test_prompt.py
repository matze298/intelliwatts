"""Tests for planner prompt assembly helpers."""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from app.models.plan import TrainingPhase
from app.models.user import User
from app.services.planner.prompt import PromptSummaryContext, build_prompt_summary


@patch("app.services.planner.prompt.user_prompt")
def test_build_prompt_summary_uses_user_prompt(mock_user_prompt: MagicMock) -> None:
    """The prompt helper should forward the expected context fields."""
    # GIVEN: A user, phase, and prompt context.
    user = User(
        id=uuid.uuid4(),
        email="prompt@example.com",
        password_hash="hash",  # noqa: S106
        weekly_hours=10.0,
        weekly_sessions=5,
    )
    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Peak for hill climb",
        start_date=date(2026, 5, 5),
        end_date=date(2026, 8, 1),
        target_date=date(2026, 8, 1),
        status="active",
    )
    context = PromptSummaryContext(
        user=user,
        phase=phase,
        weekly_hours=8.0,
        weekly_sessions=4,
        weekly_brief="Weekly brief",
        coach_text="Coach context",
        specialist_text="Specialist context",
        task_prompt="Custom task prompt",
    )
    mock_user_prompt.return_value = "Formatted prompt"

    # WHEN: Building the final prompt summary.
    result = build_prompt_summary(context)

    # THEN: The helper should pass through the normalized planning sections.
    assert result == "Formatted prompt"
    mock_user_prompt.assert_called_once_with(
        constraints="- Max Hours: 8.0\n- Max Sessions: 4\n- Primary Goal: Peak for hill climb",
        weekly_brief="Weekly brief",
        coach_context="Coach context",
        specialist_context="Specialist context",
        task_prompt="Custom task prompt",
    )
