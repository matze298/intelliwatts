"""Builds the weekly summary of the intervals.icu activities."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.intervals.analysis import TrainingLoad
    from app.intervals.parser.activity import ParsedActivity


@dataclass(frozen=True)
class PlanningConstraints:
    """Constraints for the planning."""

    weekly_hours: float
    weekly_sessions: int
    primary_goal: str = "increase_ftp"


def build_weekly_summary(
    activities: list[ParsedActivity],
    load: TrainingLoad,
    constraints: PlanningConstraints,
    wellness_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Builds the weekly summary of the intervals.icu activities used for the LLM prompt.

    Args:
        activities: The list of parsed activities.
        load: The current training load.
        constraints: The planning constraints.
        wellness_summary: Optional wellness trends summary.

    Returns:
        The weekly summary as a dictionary.
    """
    last_7d = [a for a in activities if a.date >= str(datetime.now(tz=UTC).date() - timedelta(days=7))]

    summary = {
        "recent_metrics": {
            "last_7d": {
                "tss": sum(a.training_stress for a in last_7d),
                "hours": round(sum(a.duration_h for a in last_7d), 1),
            },
            "last_42d": load,
        },
        "constraints": {
            "max_hours_week": constraints.weekly_hours,
            "sessions_per_week": constraints.weekly_sessions,
        },
        "goals": {
            "primary": constraints.primary_goal,
        },
    }

    if wellness_summary:
        summary["wellness"] = wellness_summary

    return summary
