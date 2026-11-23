"""Tests for the Intervals.icu activity parser."""

import logging
from typing import TYPE_CHECKING

from app.intervals.parser.activity import parse_activities

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


def test_parse_activities_skips_malformed_record_without_logging_payload(caplog: LogCaptureFixture) -> None:
    """Malformed activity values are skipped and logs avoid exposing full records."""
    # GIVEN one valid activity and one malformed activity with private extra data
    records = [
        {
            "start_date_local": "2026-04-20T08:00:00",
            "moving_time": 3600,
            "icu_training_load": 75,
            "type": "Ride",
            "calories": 600,
            "average_heartrate": "not-a-number",
        },
        {
            "start_date_local": "2026-04-21T08:00:00",
            "moving_time": "not-a-duration",
            "icu_training_load": 75,
            "type": "Ride",
            "calories": 600,
            "description": "private activity note",
        },
        {
            "start_date_local": "2026-04-22T08:00:00",
            "moving_time": 3600,
            "icu_training_load": float("nan"),
            "type": "Ride",
            "calories": 600,
        },
    ]

    # WHEN parsing the activities
    with caplog.at_level(logging.WARNING):
        parsed = parse_activities(records)

    # THEN valid activity metadata survives missing load and malformed records do not leak notes
    assert len(parsed) == 2
    assert parsed[1].training_stress is None
    assert parsed[0].date == "2026-04-20"
    assert parsed[0].avg_hr is None
    assert "Skipping incomplete activity record" in caplog.text
    assert "private activity note" not in caplog.text


def test_parse_activities_skips_intervals_empty_activity_stub(caplog: LogCaptureFixture) -> None:
    """Empty activity stubs from unsupported upstream sources are skipped explicitly."""
    # GIVEN an empty activity stub followed by a valid activity
    records = [
        {},
        {
            "start_date_local": "2026-04-20T08:00:00",
            "moving_time": 3600,
            "icu_training_load": 75,
            "type": "Ride",
            "calories": 600,
        },
    ]

    # WHEN parsing the activities
    with caplog.at_level(logging.WARNING):
        parsed = parse_activities(records)

    # THEN the stub is skipped and a data-quality warning is recorded
    assert len(parsed) == 1
    assert "Skipping incomplete activity record" in caplog.text


def test_parse_activities_preserves_identity_and_unknown_load() -> None:
    """Keep valid duration and identity when stress is unknown; preserve explicit zero."""
    # GIVEN completed activities with absent, negative, invalid or zero load
    records = [
        {
            "id": f"activity-{index}",
            "start_date_local": "2026-04-20T08:00:00",
            "moving_time": 1800,
            "type": "WeightTraining",
            "icu_training_load": load,
        }
        for index, load in enumerate((None, -1, "invalid", float("inf"), True, 0, 25))
    ]

    # WHEN parsing
    parsed = parse_activities(records)

    # THEN activity identity and duration survive and only recorded numeric load is retained
    assert [item.activity_id for item in parsed] == [f"activity-{index}" for index in range(7)]
    assert [item.training_stress for item in parsed] == [None, None, None, None, None, 0, 25]
    assert all(item.duration_h == 0.5 for item in parsed)
