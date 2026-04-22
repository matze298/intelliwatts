"""Tests for the resting HR trend provider."""

from unittest.mock import MagicMock

import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.resting_hr import RestingHRTrendProvider


@pytest.mark.asyncio
async def test_resting_hr_trend_provider_context() -> None:
    """Test that RestingHRTrendProvider returns the correct trend string."""
    # GIVEN: An IntervalsClient mocked to return 3 days of wellness data.
    client = MagicMock(spec=IntervalsClient)
    client.wellness.return_value = [
        {"id": "2026-04-20", "restingHR": 50},
        {"id": "2026-04-21", "restingHR": 52},
        {"id": "2026-04-22", "restingHR": 51},
    ]

    provider = RestingHRTrendProvider()

    # WHEN: Generating RHR trend context.
    context = await provider.provide_context(client, days=7)

    # THEN: The context should include the trend string.
    assert "Resting HR Trend (Last 7 days): 50 -> 52 -> 51" in context


@pytest.mark.asyncio
async def test_resting_hr_trend_provider_no_data() -> None:
    """Test that RestingHRTrendProvider handles missing data gracefully."""
    # GIVEN: An IntervalsClient returning no wellness data.
    client = MagicMock(spec=IntervalsClient)
    client.wellness.return_value = []

    provider = RestingHRTrendProvider()

    # WHEN: Generating RHR trend context.
    context = await provider.provide_context(client, days=7)

    # THEN: A helpful message should be returned.
    assert "No wellness data available for RHR trend." in context
