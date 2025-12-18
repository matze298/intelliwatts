"""Client for intervals.icu."""

from typing import Any

import requests

BASE_URL = "https://intervals.icu/api/v1"


class IntervalsClient:
    """Client for intervals.icu."""

    def __init__(self, api_key: str) -> None:
        """Initialise the client."""
        self.headers = {"Authorization": api_key}

    def activities(self, days: int = 28) -> list[dict[str, Any]]:
        """Get the activities for the last days.

        Returns:
            The activities.
        """
        r = requests.get(
            f"{BASE_URL}/activities",
            headers=self.headers,
            params={"days": days},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
