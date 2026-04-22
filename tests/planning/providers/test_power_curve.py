"""Tests for the power curve provider."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.power_curve import PowerCurveProvider, PowerCurveResult


@pytest.mark.asyncio
async def test_power_curve_provider_context() -> None:
    """Test that PowerCurveProvider returns the correct context string."""
    # GIVEN: A mocked result object.
    result = PowerCurveResult(peak_1s=1000, peak_15s=800, peak_1m=400, peak_5m=300, peak_20m=250, peak_60m=220)

    provider = PowerCurveProvider()

    # WHEN: Generating power curve context.
    context = await provider.provide_context(result)

    # THEN: The context should include peak power values.
    assert "Season Peak Power:" in context
    assert "1s: 1000W" in context
    assert "15s: 800W" in context
    assert "1m: 400W" in context
    assert "5m: 300W" in context
    assert "20m: 250W" in context
    assert "60m: 220W" in context


def test_power_curve_provider_no_data() -> None:
    """Test that PowerCurveProvider handles missing data gracefully."""
    # GIVEN: An analysis result with no power curve.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.power_curve = None
    analysis.daily_series = []

    provider = PowerCurveProvider()

    # WHEN: Calculating power curve result with no data.
    daily_df = pl.DataFrame(analysis.daily_series)
    result = provider.calculate(daily_df, client=client, power_curve=None)

    # THEN: Result should be None.
    assert result is None
