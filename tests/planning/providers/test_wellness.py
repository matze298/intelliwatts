"""Tests for the wellness provider."""

from unittest.mock import MagicMock

import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.wellness import WellnessProvider


@pytest.mark.asyncio
async def test_wellness_provider_context() -> None:
    """Test that WellnessProvider returns the correct context string."""
    # GIVEN: An IntervalsClient mocked to return 42 days of wellness data.
    client = MagicMock(spec=IntervalsClient)
    mock_wellness = []
    for i in range(42):
        date_str = f"2026-04-{22 - i:02d}" if 22 - i > 0 else f"2026-03-{31 - (i - 22):02d}"
        mock_wellness.append({
            "id": date_str,
            "hrv": 60.0,
            "restingHR": 50.0,
        })
    client.wellness.return_value = mock_wellness

    provider = WellnessProvider()

    # WHEN: Generating wellness context for the last 7 days.
    context = await provider.provide_context(client, days=7)

    # THEN: The context should include HRV and RHR averages.
    assert "Wellness Trends:" in context
    assert "HRV (7d avg): 60.0" in context
    assert "HRV (42d avg): 60.0" in context
    assert "Resting HR (7d avg): 50.0" in context
    assert "Resting HR (42d avg): 50.0" in context


@pytest.mark.asyncio
async def test_wellness_provider_no_data() -> None:
    """Test that WellnessProvider handles missing data gracefully."""
    # GIVEN: An IntervalsClient returning no wellness data.
    client = MagicMock(spec=IntervalsClient)
    client.wellness.return_value = []

    provider = WellnessProvider()

    # WHEN: Generating wellness context.
    context = await provider.provide_context(client, days=7)

    # THEN: A helpful message should be returned.
    assert "No wellness data available." in context
