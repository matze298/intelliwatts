"""Tests for the resting HR trend provider."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.resting_hr import RestingHRResult, RestingHRTrendProvider


@pytest.mark.asyncio
async def test_resting_hr_trend_provider_context() -> None:
    """Test that RestingHRTrendProvider returns the correct trend string."""
    # GIVEN: A result object.
    result = RestingHRResult(rhr_7d=51.0, rhr_42d=52.0)

    provider = RestingHRTrendProvider()

    # WHEN: Generating RHR trend context.
    context = await provider.provide_context(result)

    # THEN: The context should include the trend.
    assert "Resting HR Trend:" in context
    assert "7d Average: 51.0 bpm" in context
    assert "42d Average: 52.0 bpm" in context


def test_resting_hr_trend_provider_no_data() -> None:
    """Test that RestingHRTrendProvider handles missing data gracefully."""
    # GIVEN: An empty daily series.
    client = MagicMock(spec=IntervalsClient)
    daily_df = pl.DataFrame({"date": [], "resting_hr": []}, schema={"date": pl.Date, "resting_hr": pl.Float64})

    provider = RestingHRTrendProvider()

    # WHEN: Calculating Resting HR result with no data.
    result = provider.calculate(daily_df, client=client)

    # THEN: Result should be None.
    assert result is None
