"""Prompt assembly helpers for weekly planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.planning.coach_prompt import user_prompt

if TYPE_CHECKING:
    from app.models.plan import TrainingPhase
    from app.models.user import User


@dataclass(frozen=True)
class PromptSummaryContext:
    """Container for the prompt assembly inputs."""

    user: User
    phase: TrainingPhase
    weekly_hours: float | None
    weekly_sessions: int | None
    weekly_brief: str
    coach_text: str
    specialist_text: str
    task_prompt: str


def build_prompt_summary(context: PromptSummaryContext) -> str:
    """Build the coach prompt payload from the collected planning context.

    Returns:
        The final prompt string.
    """
    constraints_text = (
        f"- Max Hours: {context.weekly_hours if context.weekly_hours is not None else context.user.weekly_hours}\n"
        f"- Max Sessions: {context.weekly_sessions if context.weekly_sessions is not None else context.user.weekly_sessions}\n"
        f"- Primary Goal: {context.phase.primary_goal}"
    )
    return user_prompt(
        constraints=constraints_text,
        weekly_brief=context.weekly_brief,
        coach_context=context.coach_text,
        specialist_context=context.specialist_text,
        task_prompt=context.task_prompt,
    )


def workout_date_guidance(
    *, week_start: date, today: date, existing_plan: bool, phase_start: date | None = None
) -> str:
    """Build a dated scheduling rule for generation or revision.

    Returns:
        An instruction that prevents *new* workouts on past dates while
        allowing previously planned sessions to remain unchanged.
    """
    week_end = week_start + timedelta(days=6)
    lines = [
        "Workout date rules (apply to both plan_markdown and structured workouts):",
        f"- Today's date is {today.isoformat()} (UTC).",
        f"- The selected training week runs from {week_start.isoformat()} to {week_end.isoformat()}.",
        "- A structured workout's 'day' is a weekday within that selected week.",
        "- Do not create, move, or schedule any NEW workout on a date before today.",
        "- New workouts must fall on or after today and within the selected week.",
        "- Past days can be shown as history, completed training, or rest; do not prescribe fresh sessions there.",
        "- If the whole selected week is in the past, add no new workouts; do not move them into a later week.",
    ]
    if phase_start is not None:
        earliest_new_workout = max(today, phase_start)
        lines.extend([
            f"- The long-term training phase starts on {phase_start.isoformat()}.",
            (
                f"- The earliest date for NEW workouts is {earliest_new_workout.isoformat()}; "
                "never schedule new workouts before that date, even if Week 1 begins on an earlier Monday."
            ),
        ])
    if existing_plan:
        lines.append(
            "- On an update, existing workouts already assigned to past dates may be retained "
            "unchanged (same day and workout structure); do not alter or reschedule them. "
            "Only add or revise workouts on today or later."
        )
    return "\n".join(lines)
