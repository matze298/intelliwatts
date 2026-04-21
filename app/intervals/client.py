"""Client for intervals.icu."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import requests
from requests import Session

_LOGGER = logging.getLogger(__name__)
BASE_URL = "https://intervals.icu/api/v1"


class IntervalsClient:
    """Client for intervals.icu."""

    def __init__(self, api_key: str, athlete_id: str, *, session: Session | None = None) -> None:
        """Initialise the client."""
        self.api_key = api_key
        self.athlete_id = athlete_id
        self.session = session or requests

    def activities(self, days: int = 120) -> list[dict[str, Any]]:
        """Get the activities for the last days.

        Returns:
            The activities.
        """
        params = {"oldest": (datetime.now(tz=UTC).date() - timedelta(days=days)).isoformat()}
        r = self.session.get(
            f"{BASE_URL}/athlete/{self.athlete_id}/activities",
            auth=("API_KEY", self.api_key),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def wellness(self, days: int = 120) -> list[dict[str, Any]]:
        """Get the wellness data for the last days.

        Returns:
            The wellness data.
        """
        params = {"oldest": (datetime.now(tz=UTC).date() - timedelta(days=days)).isoformat()}
        r = self.session.get(
            f"{BASE_URL}/athlete/{self.athlete_id}/wellness",
            auth=("API_KEY", self.api_key),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def power_curves(self, curves: str = "90d", activity_type: str = "Ride") -> list[dict[str, Any]]:
        """Get the power curves for the athlete.

        Args:
            curves: The time range for the curves (e.g., '90d', 'all', 's0').
            activity_type: The activity type (e.g., 'Ride', 'Run').

        Returns:
            The power curves data.
        """
        params = {"curves": curves, "type": activity_type}
        r = self.session.get(
            f"{BASE_URL}/athlete/{self.athlete_id}/power-curves",
            auth=("API_KEY", self.api_key),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
