"""Parse wellness data from intervals.icu."""

import logging
from dataclasses import dataclass
from typing import Any

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParsedWellness:
    """Dataclass for parsed wellness data."""

    date: str
    hrv: float | None = None
    resting_hr: int | None = None
    sleep_score: int | None = None
    sleep_quality: int | None = None
    fatigue: int | None = None
    soreness: int | None = None
    stress: int | None = None
    readiness: int | None = None
    comments: str | None = None


def parse_wellness(w: dict[str, Any]) -> ParsedWellness:
    """Parse a wellness record from intervals.icu.

    Args:
        w: The raw wellness data from intervals.icu.

    Returns:
        The parsed wellness data.
    """
    return ParsedWellness(
        date=w["id"],
        hrv=w.get("hrv"),
        resting_hr=w.get("restingHR"),
        sleep_score=w.get("sleepScore"),
        sleep_quality=w.get("sleepQuality"),
        fatigue=w.get("fatigue"),
        soreness=w.get("soreness"),
        stress=w.get("stress"),
        readiness=w.get("readiness"),
        comments=w.get("comments"),
    )


def parse_wellness_list(wellness_list: list[dict[str, Any]]) -> list[ParsedWellness]:
    """Parse a list of wellness records from intervals.icu.

    Args:
        wellness_list: The list of raw wellness data from intervals.icu.

    Returns:
        The list of parsed wellness records.
    """
    parsed_wellness: list[ParsedWellness] = []
    for index, record in enumerate(wellness_list):
        try:
            parsed_wellness.append(parse_wellness(record))
        except KeyError, TypeError:
            record_id = record.get("id") if isinstance(record, dict) else None
            _LOGGER.warning("Unable to parse wellness record: index=%s id=%s", index, record_id, exc_info=True)
    return parsed_wellness
