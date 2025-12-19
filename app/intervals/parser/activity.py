"""Parse an activity from intervals.icu."""

import logging
from dataclasses import dataclass
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParsedActivity:
    """Dataclass for parsed activities."""

    date: str
    duration_h: float
    training_stress: float
    avg_power: float | None
    type: str
    calories: int | float


def parse_activity(a: dict[str, Any]) -> ParsedActivity | None:
    """Parse an activity from intervals.icu.

    Returns:
        The activity data as dict.
    """
    try:
        parsed_activity = ParsedActivity(
            date=a["start_date_local"][:10],
            duration_h=a["moving_time"] / 3600,
            training_stress=a["icu_training_load"],
            avg_power=a["icu_average_watts"],
            type=a["type"],
            calories=a["calories"],
        )
    except KeyError:
        _LOGGER.exception("Unable to parse activity: %s", a)
        _LOGGER.warning("Available keys: %s. Required keys: %s", a.keys(), ParsedActivity.__annotations__.keys())
        parsed_activity = None

    return parsed_activity


def parse_activities(activities: list[dict[str, Any]]) -> list[ParsedActivity]:
    """Parse a list of activities from intervals.icu.

    Returns:
        The list of parsed activities.
    """
    parsed_activities = [parse_activity(a) for a in activities]
    return [a for a in parsed_activities if a is not None]
