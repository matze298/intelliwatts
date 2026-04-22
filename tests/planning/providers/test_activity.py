"""Tests for the activity provider."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.activity import ActivityProvider


@pytest.mark.asyncio
async def test_activity_provider_context() -> None:
    """Test that ActivityProvider returns the correct context string."""
    # GIVEN: An IntervalsClient mocked to return one activity for today.
    client = MagicMock(spec=IntervalsClient)
    today_str = datetime.now(tz=UTC).date().isoformat()
    client.activities.return_value = [
        {
            "start_date_local": f"{today_str}T10:00:00",
            "moving_time": 3600,
            "icu_training_load": 100,
            "type": "Ride",
            "calories": 500,
            "icu_average_watts": 200,
            "average_heartrate": 150,
            "max_heartrate": 180,
            "icu_distance": 30000,
            "total_elevation_gain": 500,
            "icu_hr_zone_times": [0, 0, 0, 0, 0, 0, 3600],
            "icu_zone_times": [{"secs": 3600}],
            "icu_ftp": 250,
        }
    ]

    provider = ActivityProvider()

    # WHEN: Generating activity context for the last 7 days.
    context = await provider.provide_context(client, days=7)

    # THEN: The context should include TSS, hours, and load metrics.
    assert "Recent Training (Last 7 Days):" in context
    assert "Total TSS: 100.0" in context
    assert "Total Hours: 1.0" in context
    assert "Training Load:" in context
    assert "Chronic (CTL):" in context
    assert "Acute (ATL):" in context
    assert "Balance (TSB):" in context
