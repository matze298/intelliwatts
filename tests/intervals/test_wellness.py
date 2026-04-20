"""Tests for the wellness parsing and fetching."""

from unittest.mock import MagicMock, patch

from app.intervals.client import IntervalsClient
from app.intervals.parser.wellness import ParsedWellness, parse_wellness


def test_parse_wellness() -> None:
    """Test parsing wellness data from intervals.icu."""
    # GIVEN a sample wellness record from intervals.icu
    sample_wellness = {
        "id": "2026-04-20",
        "hrv": 65.0,
        "restingHR": 52,
        "sleepScore": 85,
        "sleepQuality": 4,
        "fatigue": 3,
        "soreness": 2,
        "stress": 2,
        "readiness": 8,
        "comments": "Feeling good today",
        "updated": "2026-04-20T08:00:00Z",
    }

    # WHEN parsing the wellness record
    parsed = parse_wellness(sample_wellness)

    # THEN the parsed data matches the sample
    assert isinstance(parsed, ParsedWellness)
    assert parsed.date == "2026-04-20"
    assert parsed.hrv == 65.0
    assert parsed.resting_hr == 52
    assert parsed.sleep_score == 85
    assert parsed.sleep_quality == 4
    assert parsed.fatigue == 3
    assert parsed.soreness == 2
    assert parsed.stress == 2
    assert parsed.readiness == 8
    assert parsed.comments == "Feeling good today"


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
    # Mock read_cache to return None to force an API call
    # Mock cache_data to avoid writing to disk
    with patch.object(client, "read_cache", return_value=None), patch.object(client, "cache_data"):
        result = client.wellness(days=7)

    # THEN requests.get was called with the correct URL
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "athlete/test_id/wellness" in args[0]
    assert kwargs["params"]["oldest"] is not None
    assert result == [{"id": "2026-04-20", "hrv": 70}]


def test_parse_wellness_minimal() -> None:
    """Test parsing minimal wellness data."""
    # GIVEN a wellness record with only mandatory fields (id)
    sample_wellness = {"id": "2026-04-20"}

    # WHEN parsing the wellness record
    parsed = parse_wellness(sample_wellness)

    # THEN the parsed data has None for missing fields
    assert parsed.date == "2026-04-20"
    assert parsed.hrv is None
    assert parsed.resting_hr is None
    assert parsed.sleep_score is None
    assert parsed.comments is None
