"""Builds the weekly summary of the intervals.icu activities."""

from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any


def build_weekly_summary(
    activities: Iterable[dict[str, Any]], load: dict[str, Any]
) -> dict[str, Any]:
    """Builds the weekly summary of the intervals.icu activities.

    Returns:
        The weekly summary.
    """
    last_7d = [a for a in activities if a["date"] >= str(date.today() - timedelta(days=7))]

    return {
        "recent_metrics": {
            "last_7d": {
                "tss": sum(a["tss"] for a in last_7d),
                "hours": round(sum(a["duration_h"] for a in last_7d), 1),
            },
            "last_28d": load,
        },
        "constraints": {
            "max_hours_week": 8,
            "sessions_per_week": 4,
        },
        "goals": {
            "primary": "increase_ftp",
        },
    }
