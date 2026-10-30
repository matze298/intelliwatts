"""Parse an activity from intervals.icu."""

import logging
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, cast

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParsedActivity:
    """Dataclass for parsed activities."""

    date: str
    duration_h: float
    training_stress: float
    avg_power: float | None
    type: str
    calories: int | float | None
    avg_hr: float | None
    max_hr: float | None
    distance_km: float | None
    elevation_gain: float | None
    hr_zone_times: list[int] | None
    power_zone_times: list[dict[str, int]] | None
    ftp: float | None = None


def parse_activity(a: dict[str, Any]) -> ParsedActivity | None:
    """Parse an activity from intervals.icu.

    Returns:
        The activity data as dict.
    """
    date_value = a.get("start_date_local")
    duration = _number(a.get("moving_time"))
    training_stress = _number(a.get("icu_training_load"))
    activity_type = a.get("type")
    if not isinstance(date_value, str) or not isinstance(activity_type, str):
        _LOGGER.warning("Skipping incomplete activity record: missing or invalid analysis fields")
        return None
    if duration is None or duration <= 0 or training_stress is None or training_stress < 0:
        _LOGGER.warning("Skipping incomplete activity record: missing or invalid analysis fields")
        return None

    try:
        datetime.fromisoformat(date_value)
    except ValueError:
        _LOGGER.warning("Skipping malformed activity record: invalid start date")
        return None

    hr_zone_times = a.get("icu_hr_zone_times")
    if not _valid_number_list(hr_zone_times):
        hr_zone_times = None
    power_zone_times = a.get("icu_zone_times")
    if not _valid_power_zone_times(power_zone_times):
        power_zone_times = None

    return ParsedActivity(
        date=date_value[:10],
        duration_h=duration / 3600,
        training_stress=training_stress,
        avg_power=_number(a.get("icu_average_watts")),
        type=activity_type,
        calories=_number(a.get("calories")),
        avg_hr=_number(a.get("average_heartrate")),
        max_hr=_number(a.get("max_heartrate")),
        distance_km=(distance / 1000 if (distance := _number(a.get("icu_distance"))) is not None else None),
        elevation_gain=_number(a.get("total_elevation_gain")),
        hr_zone_times=cast("list[int] | None", hr_zone_times),
        power_zone_times=cast("list[dict[str, int]] | None", power_zone_times),
        ftp=_number(a.get("icu_ftp")),
    )


def parse_activities(activities: list[object]) -> list[ParsedActivity]:
    """Parse a list of activities from intervals.icu.

    Returns:
        The list of parsed activities.
    """
    parsed_activities = []
    for index, activity in enumerate(activities):
        if not isinstance(activity, dict):
            _LOGGER.warning("Skipping malformed activity record: index=%s expected=object", index)
            continue
        parsed_activities.append(parse_activity(activity))
    return [a for a in parsed_activities if a is not None]


def _number(value: object) -> int | float | None:
    """Keep a finite numeric metric and treat other optional values as absent.

    Returns:
        The finite number, or None for malformed values.
    """
    if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(value):
        return None
    return value


def _valid_number_list(value: object) -> bool:
    return isinstance(value, list) and all((number := _number(item)) is not None and number >= 0 for item in value)


def _valid_power_zone_times(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) and (secs := _number(item.get("secs"))) is not None and secs >= 0 for item in value
    )
