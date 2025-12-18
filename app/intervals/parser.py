"""Parse an activity from intervals.icu."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedActivity:
    """Dataclass for parsed activities."""

    date: str
    duration_h: float
    training_stress: float
    normalized_power: float | None
    avg_power: float | None
    type: str | None


def parse_activity(a: dict[str, Any]) -> ParsedActivity:
    """Parse an activity from intervals.icu.

    Returns:
        The activity data as dict.
    """
    print(a.keys())
    return ParsedActivity(
        date=a["start_date_local"][:10],
        duration_h=a["moving_time"] / 3600,
        training_stress=a.get("tss", 0),
        normalized_power=a.get("np"),
        avg_power=a.get("avg_power"),
        type=a.get("type"),
    )
