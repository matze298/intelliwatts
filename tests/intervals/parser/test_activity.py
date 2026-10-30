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

    # THEN the valid activity is preserved and the malformed one is reported without its contents
    assert len(parsed) == 1
    assert parsed[0].date == "2026-04-20"
    assert parsed[0].avg_hr is None
    assert "Skipping malformed activity record" in caplog.text
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
