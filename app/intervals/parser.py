"""Parse an activity from intervals.icu."""

from typing import Any


def parse_activity(a: dict[str, Any]) -> dict[str, Any]:
    """Parse an activity from intervals.icu.

    Returns:
        The activity data as dict.
    """
    return {
        "date": a["start_date_local"][:10],
        "duration_h": a["moving_time"] / 3600,
        "tss": a.get("tss", 0),
        "np": a.get("np"),
        "avg_power": a.get("avg_power"),
        "type": a.get("type"),
    }
