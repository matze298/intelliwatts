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

    def __init__(self, api_key: str, athlete_id: str, cache_expiration_hours: int) -> None:
        """Initialise the client."""
        self.api_key = api_key
        self.athlete_id = athlete_id
        self.cache_file = Path("cache/activities.json")  # Default for activities
        self.cache_expiration_hours = cache_expiration_hours

    def activities(self, days: int = 120) -> list[dict[str, Any]]:
        """Get the activities for the last days.

        Returns:
            The activities.
        """
        params = {"oldest": (datetime.now(tz=UTC).date() - timedelta(days=days)).isoformat()}
        return self._fetch_with_cache("activities", self.cache_file, params)

    def wellness(self, days: int = 120) -> list[dict[str, Any]]:
        """Get the wellness data for the last days.

        Returns:
            The wellness data.
        """
        cache_file = Path("cache/wellness.json")
        params = {"oldest": (datetime.now(tz=UTC).date() - timedelta(days=days)).isoformat()}
        return self._fetch_with_cache("wellness", cache_file, params)

    def _fetch_with_cache(self, endpoint: str, cache_file: Path, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch data from intervals.icu with local caching.

        Args:
            endpoint: The API endpoint to fetch from.
            cache_file: The path to the cache file.
            params: The query parameters.

        Returns:
            The fetched or cached data.
        """
        # Check if cache exists and is not expired
        if (cached_content := self.read_cache(cache_file)) is not None:
            return cached_content

        # If not, fetch from intervals.icu
        r = requests.get(
            f"{BASE_URL}/athlete/{self.athlete_id}/{endpoint}",
            auth=("API_KEY", self.api_key),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        json_content: list[dict[str, Any]] = r.json()
        self.cache_data(cache_file, json_content)
        return json_content

    def read_cache(self, cache_file: Path | None = None) -> list[dict[str, Any]] | None:
        """Read data from the cache.

        Args:
            cache_file: The path to the cache file. Defaults to self.cache_file.

        Returns:
            The data if the cache exists and is not expired.
        """
        file_path = cache_file or self.cache_file
        if not file_path.exists():
            return None
        cache_age_hours = (datetime.now(tz=UTC).timestamp() - file_path.stat().st_mtime) / 3600

        if cache_age_hours > self.cache_expiration_hours:
            _LOGGER.debug(
                "Cache expired for %s. Age: %.2f hours >= expiration time of %.2f hours.",
                file_path,
                cache_age_hours,
                self.cache_expiration_hours,
            )
            return None

        _LOGGER.debug(
            "Cache hit for %s. Age %.2f hours < expiration time of %.2f hours.",
            file_path,
            cache_age_hours,
            self.cache_expiration_hours,
        )

        with file_path.open("r", encoding="utf-8") as f:
            return eval(f.read())  # noqa:S307

    @staticmethod
    def cache_data(cache_file: Path, data: list[dict[str, Any]]) -> None:
        """Cache data locally.

        Args:
            cache_file: The path to the cache file.
            data: The data to cache.
        """
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as f:
            f.write(str(data))

    def cache_activities(self, activities: list[dict[str, Any]]) -> None:
        """Cache the activities locally. Legacy wrapper.

        Args:
            activities: The activities to cache.
        """
        self.cache_data(self.cache_file, activities)
