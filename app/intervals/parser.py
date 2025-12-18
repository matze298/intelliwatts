"""Parse an activity from intervals.icu."""

import logging
from typing import Any

from app.intervals.definitions import ParsedActivity

_LOGGER = logging.getLogger(__name__)


def parse_activity(a: dict[str, Any]) -> ParsedActivity:
    """Parse an activity from intervals.icu.

    Returns:
        The activity data as dict.
    """
    return ParsedActivity(
        date=a["start_date_local"][:10],
        duration_h=a.get("moving_time", 0) / 3600,
        training_stress=a.get("icu_training_load", 0),
        normalized_power=0,
        avg_power=a.get("icu_average_watts", 0),
        type=a.get("type", ""),
        calories=a.get("calories", 0),
    )
