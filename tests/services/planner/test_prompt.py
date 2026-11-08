"""Tests for planner prompt assembly helpers."""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

from app.models.plan import TrainingPhase
from app.models.user import User
from app.services.planner.prompt import PromptSummaryContext, build_prompt_summary, workout_date_guidance


@patch("app.services.planner.prompt.user_prompt")
def test_build_prompt_summary_uses_user_prompt(mock_user_prompt: MagicMock) -> None:
    """The prompt helper should forward the expected context fields."""
    # GIVEN: A user, phase, and prompt context.
    user = User(
        id=uuid.uuid4(),
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
        constraints="- Max Cycling Hours: 8.0\n- Max Cycling Sessions: 4\n- Non-cycling sports do not consume this cycling budget; use them only for recovery and scheduling.\n- Available cycling days: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday (only schedule NEW workouts on these days).\n- Primary Goal: Peak for hill climb",
        weekly_brief="Weekly brief",
        coach_context="Coach context",
        specialist_context="Specialist context",
        task_prompt="Custom task prompt",
    )


def test_new_workouts_cannot_be_planned_before_today() -> None:
    """The prompt names exact dates and excludes new sessions on past weekdays."""
    # GIVEN a Saturday during the selected training week.
    guidance = workout_date_guidance(
        week_start=date(2026, 11, 2),
        today=date(2026, 11, 7),
        existing_plan=False,
    )

    # THEN only today and Sunday can receive newly prescribed workouts.
    assert "2026-11-07" in guidance
    assert "2026-11-02 to 2026-11-08" in guidance
    assert "Do not create, move, or schedule any NEW workout on a date before today." in guidance
    assert "plan_markdown and structured workouts" in guidance
    assert "within the selected week" in guidance
    assert "existing workouts already assigned" not in guidance


def test_revisions_preserve_existing_past_workouts() -> None:
    """An edited plan may keep prior sessions without adding or changing past days."""
    guidance = workout_date_guidance(
        week_start=date(2026, 11, 2),
        today=date(2026, 11, 7),
        existing_plan=True,
    )

    assert "existing workouts already assigned to past dates may be retained unchanged" in guidance
    assert "do not alter or reschedule them" in guidance
    assert "Only add or revise workouts on today or later." in guidance


def test_past_training_week_does_not_shift_new_workouts_into_another_week() -> None:
    """A week already over must not be filled with retroactive workouts."""
    guidance = workout_date_guidance(
        week_start=date(2026, 11, 2),
        today=date(2026, 11, 16),
        existing_plan=False,
    )

    assert "If the whole selected week is in the past, add no new workouts" in guidance
    assert "do not move them into a later week" in guidance


def test_future_midweek_phase_start_prevents_early_week_workouts() -> None:
    """The exact phase start date, not only Week 1's Monday, limits new sessions."""
    guidance = workout_date_guidance(
        week_start=date(2026, 11, 16),
        today=date(2026, 11, 7),
        phase_start=date(2026, 11, 19),
        existing_plan=False,
    )

    assert "long-term training phase starts on 2026-11-19" in guidance
    assert "earliest date for NEW workouts is 2026-11-19" in guidance
    assert "even if Week 1 begins on an earlier Monday" in guidance


def test_existing_phase_start_uses_today_when_later() -> None:
    """An older goal does not allow new workouts on elapsed dates."""
    guidance = workout_date_guidance(
        week_start=date(2026, 11, 2),
        today=date(2026, 11, 7),
        phase_start=date(2026, 10, 12),
        existing_plan=True,
    )

    assert "long-term training phase starts on 2026-10-12" in guidance
    assert "earliest date for NEW workouts is 2026-11-07" in guidance
    assert "existing workouts already assigned to past dates may be retained unchanged" in guidance
