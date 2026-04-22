"""Tests for the power curve provider."""

from unittest.mock import MagicMock

import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.power_curve import PowerCurveProvider


@pytest.mark.asyncio
async def test_power_curve_provider_context() -> None:
    """Test that PowerCurveProvider returns the correct context string."""
    # GIVEN: An IntervalsClient mocked to return a 90d power curve in the expected dictionary format.
    client = MagicMock(spec=IntervalsClient)
    client.power_curves.return_value = {
        "list": [
            {
                "id": "90d",
                "lookback_days": 90,
                "secs": [5, 60, 300, 1200],
                "watts": [800, 400, 300, 250],
            }
        ]
    }

    provider = PowerCurveProvider()

    # WHEN: Generating power curve context.
    context = await provider.provide_context(client, days=7)

    # THEN: The context should include peak power values for key durations.
    assert "Power Curve (Last 90 Days):" in context
    assert "5s Peak: 800W" in context
    assert "1m Peak: 400W" in context
    assert "5m Peak: 300W" in context
    assert "20m Peak: 250W" in context


@pytest.mark.asyncio
async def test_power_curve_provider_no_data() -> None:
    """Test that PowerCurveProvider handles missing data gracefully."""
    # GIVEN: An IntervalsClient returning no power curve data.
    client = MagicMock(spec=IntervalsClient)
    client.power_curves.return_value = {"list": []}

    provider = PowerCurveProvider()

    # WHEN: Generating power curve context.
    context = await provider.provide_context(client, days=7)

    # THEN: A helpful message should be returned.
    assert "No power curve data available." in context
