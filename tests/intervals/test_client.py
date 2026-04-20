"""Tests for the intervals client."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.intervals.client import IntervalsClient, cache_data


@patch("app.intervals.client.requests.get")
def test_intervals_client_wellness(mock_get: MagicMock) -> None:
    """Test fetching wellness data from IntervalsClient."""
    # GIVEN a mock response
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "2026-04-20", "hrv": 70}]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    client = IntervalsClient(api_key="test_key", athlete_id="test_id", cache_expiration_hours=1)

    # WHEN fetching wellness data
    with (
        patch("app.intervals.client.IntervalsClient.read_cache", return_value=None),
        patch("app.intervals.client.cache_data"),
    ):
        result = client.wellness(days=7)

    # THEN requests.get was called with the correct URL
    mock_get.assert_called_once()
    args, _kwargs = mock_get.call_args
    assert "athlete/test_id/wellness" in args[0]
    assert result == [{"id": "2026-04-20", "hrv": 70}]


@patch("app.intervals.client.requests.get")
def test_intervals_client_activities(mock_get: MagicMock) -> None:
    """Test fetching activities data from IntervalsClient."""
    # GIVEN a mock response
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": "act1"}]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    client = IntervalsClient(api_key="test_key", athlete_id="test_id", cache_expiration_hours=1)

    # WHEN fetching activities data
    with (
        patch("app.intervals.client.IntervalsClient.read_cache", return_value=None),
        patch("app.intervals.client.cache_data"),
    ):
        result = client.activities(days=7)

    # THEN requests.get was called with the correct URL
    mock_get.assert_called_once()
    args, _kwargs = mock_get.call_args
    assert "athlete/test_id/activities" in args[0]
    assert result == [{"id": "act1"}]


def test_read_cache_missing() -> None:
    """Test read_cache when the file is missing."""
    # GIVEN an intervals client
    client = IntervalsClient(api_key="test_key", athlete_id="test_id", cache_expiration_hours=1)
    # WHEN reading from a non-existing cache
    # THEN it returns None
    with patch("app.intervals.client.Path.exists", return_value=False):
        assert client.read_cache(Path("nonexistent.json")) is None


def test_read_cache_expired() -> None:
    """Test read_cache when the file is expired."""
    # GIVEN an intervals client with an expired cache
    client = IntervalsClient(api_key="test_key", athlete_id="test_id", cache_expiration_hours=1)
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    # Set mtime to 2 hours ago
    mock_path.stat.return_value.st_mtime = time.time() - (2 * 3600)

    # WHEN reading the cache
    # THEN None is returned
    assert client.read_cache(mock_path) is None


def test_read_cache_hit() -> None:
    """Test read_cache when there is a valid hit."""
    # GIVEN a intervals client with a valid cache
    client = IntervalsClient(api_key="test_key", athlete_id="test_id", cache_expiration_hours=1)
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.stat.return_value.st_mtime = time.time() - 300  # 5 mins ago

    # GIVEN a mocked cache entry
    mock_file = MagicMock()
    mock_file.read.return_value = "[{'id': 'cached'}]"
    mock_file.__enter__.return_value = mock_file
    mock_path.open.return_value = mock_file

    # WHEN reading the cache
    result = client.read_cache(mock_path)

    # THEN the result is as expected
    assert result == [{"id": "cached"}]


@patch("app.intervals.client.requests.get")
def test_fetch_with_cache_api_error(mock_get: MagicMock) -> None:
    """Test fetch_with_cache when API returns an error."""
    # GIVEN a mock response that returns a HTTP Error
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
    mock_get.return_value = mock_response

    # GIVEN an intervals client
    client = IntervalsClient(api_key="test_key", athlete_id="test_id", cache_expiration_hours=1)

    # WHEN reading the cache
    # THEN the HTTP Error is raised
    with patch.object(client, "read_cache", return_value=None), pytest.raises(requests.exceptions.HTTPError):
        client._fetch_with_cache("endpoint", Path("cache.json"), {})


def test_cache_data() -> None:
    """Test cache_data writes to disk."""
    # GIVEN a mock path
    mock_path = MagicMock(spec=Path)
    # mock_open doesn't play well with static methods and Path objects sometimes
    # so we'll use a manual mock for write
    mock_file = MagicMock()
    mock_path.open.return_value = mock_file
    mock_file.__enter__.return_value = mock_file

    # WHEN caching the data
    cache_data(mock_path, [{"data": 1}])

    # THEN the data has been stored in the cache
    mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_file.write.assert_called_once()
    assert "[{'data': 1}]" in mock_file.write.call_args[0][0]
