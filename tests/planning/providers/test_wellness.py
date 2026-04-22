"""Tests for the wellness provider."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.wellness import WellnessProvider


@pytest.mark.asyncio
async def test_wellness_provider_context() -> None:
    """Test that WellnessProvider returns the correct context string."""
    # GIVEN: A mocked analysis result with wellness trends.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.wellness_summary = {
        "hrv_7d": 60.0,
        "hrv_42d": 65.0,
        "resting_hr_7d": 50.0,
        "resting_hr_42d": 52.0,
    }
    analysis.daily_series = []

    provider = WellnessProvider()

    # WHEN: Generating wellness context.
    daily_df = pl.DataFrame(analysis.daily_series)
    result = provider.calculate(daily_df, client=client, analysis=analysis)
    context = await provider.provide_context(result)

    # THEN: The context should include HRV and RHR averages from analysis.
    assert "Wellness Trends:" in context
    assert "HRV (7d avg): 60.0" in context
    assert "HRV (42d avg): 65.0" in context
    assert "Resting HR (7d avg): 50.0" in context
    assert "Resting HR (42d avg): 52.0" in context


@pytest.mark.asyncio
async def test_wellness_provider_no_data() -> None:
    """Test that WellnessProvider handles missing data gracefully."""
    # GIVEN: An analysis result with no wellness summary.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.wellness_summary = None
    analysis.daily_series = []

    provider = WellnessProvider()

    # WHEN: Generating wellness context.
    daily_df = pl.DataFrame(analysis.daily_series)
    result = provider.calculate(daily_df, client=client, analysis=analysis)
    context = await provider.provide_context(result)

    # THEN: A helpful message should be returned.
    assert "No wellness data available." in context
