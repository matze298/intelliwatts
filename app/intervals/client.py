"""Client for intervals.icu."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

import requests
from requests import Response, Session

if TYPE_CHECKING:
    from app.models.plan import WorkoutDeliveryPayload, WorkoutDeliveryResult

BASE_URL = "https://intervals.icu/api/v1"


class IntervalsResponseError(ValueError):
    """An Intervals.icu response cannot be used by the requested operation."""


class IntervalsClient:
    """Client for intervals.icu."""

    def __init__(self, api_key: str, athlete_id: str, *, session: Session | None = None) -> None:
        """Initialise the client."""
        self.api_key = api_key
        self.athlete_id = athlete_id
        self.session = session or requests

    @staticmethod
    def _json_payload(response: Response, *, endpoint: str) -> object:
        """Decode a successful response as JSON.

        Returns:
            The decoded JSON value.

        Raises:
            IntervalsResponseError: if the response body is invalid JSON.
        """
        try:
            return response.json()
        except ValueError as exc:
            msg = f"Intervals.icu {endpoint} response was not valid JSON"
            raise IntervalsResponseError(msg) from exc

    @classmethod
    def _json_list(cls, response: Response, *, endpoint: str) -> list[object]:
        """Decode an endpoint response that must be a JSON list.

        Returns:
            The decoded list.

        Raises:
            IntervalsResponseError: if the JSON value is not a list.
        """
        payload = cls._json_payload(response, endpoint=endpoint)
        if not isinstance(payload, list):
            msg = f"Intervals.icu {endpoint} response must be a list"
            raise IntervalsResponseError(msg)
        return payload

    def activities(self, days: int = 120) -> list[object]:
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
        return self._json_list(r, endpoint="activities")

    def wellness(self, days: int = 120) -> list[object]:
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
        return self._json_list(r, endpoint="wellness")

    def power_curves(self, curves: str = "90d", activity_type: str = "Ride") -> dict[str, Any]:
        """Get the power curves for the athlete.

        Args:
            curves: The time range for the curves (e.g., '90d', 'all', 's0').
            activity_type: The activity type (e.g., 'Ride', 'Run').

        Returns:
            The power curves data.

        Raises:
            IntervalsResponseError: if the response body is not an object.
        """
        params = {"curves": curves, "type": activity_type}
        r = self.session.get(
            f"{BASE_URL}/athlete/{self.athlete_id}/power-curves",
            auth=("API_KEY", self.api_key),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        payload = self._json_payload(r, endpoint="power curves")
        if not isinstance(payload, dict):
            msg = "Intervals.icu power curves response must be an object"
            raise IntervalsResponseError(msg)
        return payload

    def publish_workout_events(self, events: list[WorkoutDeliveryPayload]) -> list[WorkoutDeliveryResult]:
        """Create or update planned workouts on the calendar.

        Returns:
            The API response payload.

        Raises:
            IntervalsResponseError: if the API response is malformed or incomplete.
        """
        r = self.session.post(
            f"{BASE_URL}/athlete/{self.athlete_id}/events/bulk",
            auth=("API_KEY", self.api_key),
            params={"upsert": "true"},
            json=cast("list[dict[str, str]]", events),
            timeout=10,
        )
        r.raise_for_status()
        payload = self._json_list(r, endpoint="workout events")
        if len(payload) != len(events):
            msg = f"Intervals.icu workout events response count ({len(payload)}) did not match request count ({len(events)})"
            raise IntervalsResponseError(msg)

        expected_external_ids = {event["external_id"] for event in events}
        results: list[WorkoutDeliveryResult] = []
        returned_external_ids: set[str] = set()
        for index, item in enumerate(payload):
            if not isinstance(item, dict):
                msg = f"Intervals.icu workout events response item {index} must be an object"
                raise IntervalsResponseError(msg)
            event_id = item.get("id")
            external_id = item.get("external_id")
            if not event_id and not external_id:
                msg = f"Intervals.icu workout events response item {index} is missing an identifier"
                raise IntervalsResponseError(msg)
            if external_id is not None:
                if not isinstance(external_id, str) or external_id not in expected_external_ids:
                    msg = "Intervals.icu workout events response contained unknown or duplicate external IDs"
                    raise IntervalsResponseError(msg)
                if external_id in returned_external_ids:
                    msg = "Intervals.icu workout events response contained unknown or duplicate external IDs"
                    raise IntervalsResponseError(msg)
                returned_external_ids.add(external_id)
            results.append(cast("WorkoutDeliveryResult", item))
        return results
