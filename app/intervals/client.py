"""Client for intervals.icu."""

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://intervals.icu/api/v1"


class IntervalsClient:
    """Client for intervals.icu."""

    def __init__(self, api_key: str, athlete_id: str) -> None:
        """Initialise the client."""
        self.api_key = api_key
        self.athlete_id = athlete_id
        self.cache_file = Path("cache/activities.json")
        self.expiration_hours = 1

    def activities(self, days: int = 28) -> list[dict[str, Any]]:
        """Get the activities for the last days.

        Returns:
            The activities.
        """
        # Check if cache exists and is not expired
        if (cached_content := self.read_cache()) is not None:
            return cached_content

        # If not, fetch from intervals.icu
        r = requests.get(
            f"{BASE_URL}/athlete/{self.athlete_id}/activities",
            auth=("API_KEY", self.api_key),
            params={"oldest": (datetime.now(tz=UTC).date() - timedelta(days=days)).isoformat()},
            timeout=10,
        )
        r.raise_for_status()
        json_content: list[dict[str, Any]] = r.json()
        self.cache_activities(json_content)
        return json_content

    def read_cache(self) -> list[dict[str, Any]] | None:
        """Read the activities from the cache.

        Returns:
            The activities if the cache exists and is not expired.
        """
        if not self.cache_file.exists():
            return None
        cache_age_hours = (
            datetime.now(tz=UTC).timestamp() - self.cache_file.stat().st_mtime
        ) / 3600

        if cache_age_hours > self.expiration_hours:
            _LOGGER.debug(
                "Cache expired. Age: %.2f hours >= expiration time of %.2f hours.",
                cache_age_hours,
                self.expiration_hours,
            )
            return None

        _LOGGER.debug(
            "Cache hit. Age %.2f hours < expiration time of %.2f hours.",
            cache_age_hours,
            self.expiration_hours,
        )

        with self.cache_file.open("r") as f:
            return eval(f.read())

    def cache_activities(self, activities: list[dict[str, Any]]) -> None:
        """Cache the activities locally.

        Args:
            activities: The activities to cache.
        """
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with self.cache_file.open("w") as f:
            f.write(str(activities))
