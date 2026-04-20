"""Tests for the wellness parser."""

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


def test_parse_wellness_minimal() -> None:
    """Test parsing minimal wellness data."""
    # GIVEN a wellness record with only mandatory fields (id)
    sample_wellness = {"id": "2026-04-20"}

    # WHEN parsing the wellness record
    parsed = parse_wellness(sample_wellness)

    # THEN the parsed data has None for missing fields
    assert parsed.date == "2026-04-20"
    assert parsed.hrv is None
