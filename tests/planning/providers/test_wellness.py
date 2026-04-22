"""Tests for the wellness provider."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.wellness import WellnessProvider, WellnessResult


@pytest.mark.asyncio
async def test_wellness_provider_context() -> None:
    """Test that WellnessProvider returns the correct context string."""
    # GIVEN: A result object for testing provide_context.

    result = WellnessResult(
        hrv_7d=60.0,
        hrv_42d=65.0,
        rhr_7d=50.0,
        rhr_42d=52.0,
    )

    provider = WellnessProvider()

    # WHEN: Generating wellness context.
    context = await provider.provide_context(result)

    # THEN: The context should include HRV and RHR averages from analysis.
    assert "Wellness Trends:" in context
    assert "HRV (7d avg): 60.0" in context
    assert "HRV (42d avg): 65.0" in context
    assert "Resting HR (7d avg): 50.0" in context
    assert "Resting HR (42d avg): 52.0" in context


def test_wellness_provider_no_data() -> None:
    """Test that WellnessProvider handles missing data gracefully."""
    # GIVEN: An empty daily series.
    client = MagicMock(spec=IntervalsClient)
    daily_df = pl.DataFrame([])

    provider = WellnessProvider()

    # WHEN: Calculating wellness result with no data.
    result = provider.calculate(daily_df, client=client)

    # THEN: Result should be None.
    assert result is None
