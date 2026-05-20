"""Prompt assembly helpers for weekly planning."""

from __future__ import annotations

from dataclasses import dataclass
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
