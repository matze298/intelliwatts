"""Builds the weekly summary of the intervals.icu activities."""

from datetime import date, timedelta
from typing import Any

from app.intervals.load import TrainingLoad
from app.intervals.parser.activity import ParsedActivity


def build_weekly_summary(
    activities: list[ParsedActivity],
    load: TrainingLoad,
    weekly_hours: float,
    weekly_sessions: int,
    primary_goal: str = "increase_ftp",
) -> dict[str, Any]:
    """Builds the weekly summary of the intervals.icu activities used for the LLM prompt.

    Returns:
        The weekly summary.
    """
    last_7d = [a for a in activities if a.date >= str(date.today() - timedelta(days=7))]

    return {
        "recent_metrics": {
            "last_7d": {
                "tss": sum(a.training_stress for a in last_7d),
                "hours": round(sum(a.duration_h for a in last_7d), 1),
            },
            "last_42d": load,
        },
        "constraints": {
            "max_hours_week": weekly_hours,
            "sessions_per_week": weekly_sessions,
        },
        "goals": {
            "primary": primary_goal,
        },
    }
