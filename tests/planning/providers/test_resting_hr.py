"""Tests for the resting HR trend provider."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.resting_hr import RestingHRTrendProvider


@pytest.mark.asyncio
async def test_resting_hr_trend_provider_context() -> None:
    """Test that RestingHRTrendProvider returns the correct trend string."""
    # GIVEN: A mocked analysis result with a daily series containing RHR.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.daily_series = [
        {"date": "2026-04-20", "resting_hr": 50},
        {"date": "2026-04-21", "resting_hr": 52},
        {"date": "2026-04-22", "resting_hr": 51},
    ]

    provider = RestingHRTrendProvider()

    # WHEN: Generating RHR trend context.
    daily_df = pl.DataFrame(analysis.daily_series)
    result = provider.calculate(daily_df, client=client, analysis=analysis)
    context = await provider.provide_context(result)

    # THEN: The context should include the trend string from analysis.
    assert "Resting HR Trend (Last 7 days): 50 -> 52 -> 51" in context


@pytest.mark.asyncio
async def test_resting_hr_trend_provider_no_data() -> None:
    """Test that RestingHRTrendProvider handles missing data gracefully."""
    # GIVEN: An analysis result with no daily series.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.daily_series = []

    provider = RestingHRTrendProvider()

    # WHEN: Generating RHR trend context.
    daily_df = pl.DataFrame(analysis.daily_series)
    result = provider.calculate(daily_df, client=client, analysis=analysis)
    context = await provider.provide_context(result)

    # THEN: A helpful message should be returned.
    assert "No resting HR data available." in context
