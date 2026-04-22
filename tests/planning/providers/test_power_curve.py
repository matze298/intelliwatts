"""Tests for the power curve provider."""

from unittest.mock import MagicMock

import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.power_curve import PowerCurveProvider


@pytest.mark.asyncio
async def test_power_curve_provider_context() -> None:
    """Test that PowerCurveProvider returns the correct context string."""
    # GIVEN: A mocked analysis result with power curve peaks.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.power_curve = {
        "peak_5s": 800,
        "peak_1m": 400,
        "peak_5m": 300,
        "peak_20m": 250,
    }

    provider = PowerCurveProvider()

    # WHEN: Generating power curve context.
    context = await provider.provide_context(client, days=7, analysis=analysis)

    # THEN: The context should include peak power values from analysis.
    assert "Power Curve (Last 90 Days):" in context
    assert "5s Peak: 800W" in context
    assert "1m Peak: 400W" in context
    assert "5m Peak: 300W" in context
    assert "20m Peak: 250W" in context


@pytest.mark.asyncio
async def test_power_curve_provider_no_data() -> None:
    """Test that PowerCurveProvider handles missing data gracefully."""
    # GIVEN: An analysis result with no power curve.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.power_curve = None

    provider = PowerCurveProvider()

    # WHEN: Generating power curve context.
    context = await provider.provide_context(client, days=7, analysis=analysis)

    # THEN: A helpful message should be returned.
    assert "No power curve data available." in context
