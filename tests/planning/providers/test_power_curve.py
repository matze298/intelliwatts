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


def test_power_curve_provider_calculate_multiple_curves() -> None:
    """Test that calculate fetches and processes multiple curves in a single call."""
    # GIVEN: A mocked client that returns all curves in one response.
    client = MagicMock(spec=IntervalsClient)
    client.power_curves.return_value = {
        "list": [
            {"id": "90d", "secs": [1, 1200], "watts": [1000, 300]},
            {"id": "s0", "secs": [1, 1200], "watts": [1100, 310]},
            {"id": "all", "secs": [1, 1200], "watts": [1200, 320]},
        ]
    }
    daily_df = pl.DataFrame([])

    provider = PowerCurveProvider()

    # WHEN: Calculating power curve result.
    result = provider.calculate(daily_df, client=client)

    # THEN: All curves should be captured.
    assert result is not None
    assert result.peak_1s == 1000
    assert result.peak_20m == 300
    assert result.recent_90d == [{"secs": 1, "watts": 1000}, {"secs": 1200, "watts": 300}]
    assert result.season == [{"secs": 1, "watts": 1100}, {"secs": 1200, "watts": 310}]
    assert result.all_time == [{"secs": 1, "watts": 1200}, {"secs": 1200, "watts": 320}]

    # AND: Client should have been called exactly once with all curve types.
    client.power_curves.assert_called_once_with(curves="90d,s0,all")


def test_power_curve_provider_get_dashboard_widget() -> None:
    """Test that get_dashboard_widget returns the heatmap widget."""
    # GIVEN: A result object with full curve data.
    result = PowerCurveResult(
        peak_1s=1000,
        peak_15s=800,
        peak_1m=400,
        peak_5m=300,
        peak_20m=250,
        peak_60m=220,
        recent_90d=[{"secs": 1, "watts": 1000}],
        season=[{"secs": 1, "watts": 1100}],
        all_time=[{"secs": 1, "watts": 1200}],
    )
    provider = PowerCurveProvider()

    # WHEN: Getting the dashboard widget.
    widget = provider.get_dashboard_widget(result)

    # THEN: It should return the heatmap widget.
    assert widget is not None
    assert widget.name == "power_curve"
    assert widget.title == "Critical Power Heatmap"
    assert widget.custom_template == "widgets/power_curve_chart.html"
    assert widget.data is not None
    assert widget.data["recent_90d"] == result.recent_90d
    assert widget.data["season"] == result.season
    assert widget.data["all_time"] == result.all_time
    assert widget.data["peak_20m"] == result.peak_20m


def test_power_curve_provider_no_data() -> None:
    """Test that PowerCurveProvider handles missing data gracefully."""
    # GIVEN: An analysis result with no power curve.
    client = MagicMock(spec=IntervalsClient)
    client.power_curves.return_value = {"list": []}
    daily_df = pl.DataFrame([])

    provider = PowerCurveProvider()

    # WHEN: Calculating power curve result with no data.
    result = provider.calculate(daily_df, client=client)

    # THEN: Result should be None.
    assert result is None


def test_power_curve_provider_missing_optional_curves() -> None:
    """Test calculate when optional curves (season, all-time) are missing."""
    # GIVEN: A mocked client that returns only the 90d curve.
    client = MagicMock(spec=IntervalsClient)
    client.power_curves.return_value = {
        "list": [
            {"id": "90d", "secs": [1], "watts": [1000]},
        ]
    }
    daily_df = pl.DataFrame([])
    provider = PowerCurveProvider()

    # WHEN: Calculating power curve result.
    result = provider.calculate(daily_df, client=client)

    # THEN: Only the 90d curve should be captured.
    assert result is not None
    assert result.peak_1s == 1000
    assert result.season is None
    assert result.all_time is None


def test_power_curve_provider_missing_90d_curve() -> None:
    """Test calculate when mandatory 90d curve is missing."""
    # GIVEN: A mocked client that returns only optional curves.
    client = MagicMock(spec=IntervalsClient)
    client.power_curves.return_value = {
        "list": [
            {"id": "s0", "secs": [1], "watts": [1100]},
        ]
    }
    daily_df = pl.DataFrame([])
    provider = PowerCurveProvider()

    # WHEN: Calculating power curve result.
    result = provider.calculate(daily_df, client=client)

    # THEN: Result should be None because 90d is mandatory.
    assert result is None


def test_power_curve_provider_no_client() -> None:
    """Test calculate when client is None."""
    # GIVEN: No client.
    daily_df = pl.DataFrame([])
    provider = PowerCurveProvider()

    # WHEN: Calculating power curve result.
    result = provider.calculate(daily_df, client=None)

    # THEN: Result should be None.
    assert result is None
