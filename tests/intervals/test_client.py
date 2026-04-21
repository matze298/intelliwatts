"""Tests for the intervals client."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
import requests
from requests_cache import CachedSession

if TYPE_CHECKING:
    from requests_mock import Mocker

from app.intervals.client import BASE_URL, IntervalsClient


def test_intervals_client_caching(requests_mock: Mocker) -> None:
    """Test that the client uses the cache on the second call."""
    # GIVEN a CachedSession with a memory backend
    session = CachedSession(backend="memory", expire_after=3600)
    client = IntervalsClient(api_key="test_key", athlete_id="test_id", session=session)
    # AND a mocked API endpoint
    params = {"oldest": (datetime.now(tz=UTC).date() - timedelta(days=7)).isoformat()}
    matcher = requests_mock.get(f"{BASE_URL}/athlete/test_id/wellness", json=[{"id": "2026-04-20", "hrv": 70}])

    # WHEN fetching wellness data twice
    response1 = client.wellness(days=7)
    response2 = client.wellness(days=7)

    # THEN the API was only called once
    assert matcher.call_count == 1
    # AND the results are the same
    assert response1 == [{"id": "2026-04-20", "hrv": 70}]
    assert response2 == response1
    # AND the second response was from the cache
    cached_response = session.get(
        f"{BASE_URL}/athlete/test_id/wellness",
        auth=("API_KEY", "test_key"),
        params=params,
    )
    assert cached_response.from_cache


def test_intervals_client_no_session(requests_mock: Mocker) -> None:
    """Test that the client makes two requests when no session is provided."""
    # GIVEN a client without a session
    client = IntervalsClient(api_key="test_key", athlete_id="test_id")
    # AND a mocked API endpoint
    matcher = requests_mock.get(f"{BASE_URL}/athlete/test_id/wellness", json=[{"id": "2026-04-20", "hrv": 70}])

    # WHEN fetching wellness data twice
    response1 = client.wellness(days=7)
    response2 = client.wellness(days=7)

    # THEN the API was called twice
    assert matcher.call_count == 2
    # AND the results are the same
    assert response1 == [{"id": "2026-04-20", "hrv": 70}]
    assert response2 == response1


def test_intervals_client_api_error(requests_mock: Mocker) -> None:
    """Test that API errors are propagated."""
    # GIVEN a client
    session = CachedSession(backend="memory")
    client = IntervalsClient(api_key="test_key", athlete_id="test_id", session=session)
    # AND a mocked API endpoint that returns an error
    requests_mock.get(f"{BASE_URL}/athlete/test_id/wellness", status_code=500)

    # WHEN fetching data
    # THEN the HTTPError is raised
    with pytest.raises(requests.exceptions.HTTPError):
        client.wellness(days=7)
