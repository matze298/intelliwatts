"""Parse wellness data from intervals.icu."""

import logging
from dataclasses import dataclass
from math import isfinite
from typing import Any

from app.intervals.validation import is_iso_date

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParsedWellness:
    """Dataclass for parsed wellness data."""

    date: str
    hrv: float | None = None
    resting_hr: int | float | None = None
    sleep_score: int | float | None = None
    sleep_quality: int | float | None = None
    fatigue: int | float | None = None
    soreness: int | float | None = None
    stress: int | float | None = None
    readiness: int | float | None = None
    comments: str | None = None


def parse_wellness(w: dict[str, Any]) -> ParsedWellness:
    """Parse a wellness record from intervals.icu.

    Args:
        w: The raw wellness data from intervals.icu.

    Returns:
        The parsed wellness data.

    Raises:
        ValueError: if the record has no valid date.
    """
    record_date = w.get("id")
    if not isinstance(record_date, str) or not is_iso_date(record_date):
        msg = "wellness record has no valid date"
        raise ValueError(msg)
    return ParsedWellness(
        date=record_date,
        hrv=_number(w.get("hrv")),
        resting_hr=_number(w.get("restingHR")),
        sleep_score=_number(w.get("sleepScore")),
        sleep_quality=_number(w.get("sleepQuality")),
        fatigue=_number(w.get("fatigue")),
        soreness=_number(w.get("soreness")),
        stress=_number(w.get("stress")),
        readiness=_number(w.get("readiness")),
        comments=w.get("comments") if isinstance(w.get("comments"), str) else None,
    )


def parse_wellness_list(wellness_list: list[object]) -> list[ParsedWellness]:
    """Parse a list of wellness records from intervals.icu.

    Args:
        wellness_list: The list of raw wellness data from intervals.icu.

    Returns:
        The list of parsed wellness records.
    """
    parsed_wellness: list[ParsedWellness] = []
    for index, record in enumerate(wellness_list):
        if not isinstance(record, dict):
            _LOGGER.warning("Unable to parse wellness record: index=%s expected=object", index)
            continue
        try:
            parsed_wellness.append(parse_wellness(record))
        except ValueError:
            _LOGGER.warning("Unable to parse wellness record: index=%s invalid_date", index)
    return parsed_wellness


def _number(value: object) -> int | float | None:
    """Keep a finite numeric metric and treat other optional values as absent.

    Returns:
        The finite number, or None for malformed values.
    """
    if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(value):
        return None
    return value
