"""Tests for the wellness provider."""

import polars as pl
import pytest

from app.planning.providers.wellness import WellnessProvider, WellnessResult


def test_wellness_provider_name() -> None:
    """Tests that the provider name is correct."""
    provider = WellnessProvider()
    assert provider.get_name() == "wellness"


def test_wellness_calculation() -> None:
    """Tests the wellness calculation and rolling averages."""
    # GIVEN a daily_df with 10 days of wellness data
    dates = [f"2026-04-{i + 1:02d}" for i in range(10)]
    hrv = [50.0, 52.0, 54.0, 56.0, 58.0, 60.0, 62.0, 64.0, 66.0, 68.0]
    resting_hr = [60.0] * 10

    daily_df = pl.DataFrame({
        "date": pl.Series(dates).str.to_date("%Y-%m-%d"),
        "hrv": hrv,
        "resting_hr": resting_hr,
    })

    provider = WellnessProvider()

    # WHEN calculating wellness metrics
    result = provider.calculate(daily_df)

    # THEN the result should contain correct time series data
    assert result is not None
    assert len(result.dates) == 10
    assert result.hrv == hrv
    assert result.resting_hr == resting_hr

    # Check 7d rolling average (last value should be mean of 62, 64, 66, 68, 60, 58, 56... no wait)
    # Mean of [56, 58, 60, 62, 64, 66, 68] = 62.0
    assert result.hrv_7d[-1] == 62.0

    # Check trend (Improving because 62.0 > 59.0 * 1.05)
    # Overall average = mean of [50...68] = 59.0
    assert result.hrv_trend == "improving"


def test_wellness_widget() -> None:
    """Tests the dashboard widget formatting."""
    # GIVEN a successful wellness calculation
    provider = WellnessProvider()
    result = WellnessResult(
        dates=["2026-04-01"],
        hrv=[60.0],
        hrv_7d=[60.0],
        resting_hr=[50.0],
        resting_hr_7d=[50.0],
        avg_hrv=60.0,
        avg_resting_hr=50.0,
        hrv_trend="improving",
        recent_hrv_trend=[55.0, 60.0],
    )

    # WHEN formatting for dashboard
    widget = provider.get_dashboard_widget(result)

    # THEN returns a widget with custom template and data
    assert widget is not None
    assert widget.name == "wellness"
    assert widget.custom_template == "widgets/wellness_chart.html"
    assert widget.data is not None
    assert widget.data["avg_hrv"] == 60.0
    assert widget.data["hrv_trend"] == "improving"


@pytest.mark.asyncio
async def test_wellness_context() -> None:
    """Tests context generation for the LLM coach."""
    # GIVEN an IntensityResult (wait, WellnessResult)
    provider = WellnessProvider()
    result = WellnessResult(
        dates=["2026-04-01"],
        hrv=[60.0],
        hrv_7d=[60.0],
        resting_hr=[50.0],
        resting_hr_7d=[50.0],
        avg_hrv=60.0,
        avg_resting_hr=50.0,
        hrv_trend="stable",
        recent_hrv_trend=[60.0, 60.0],
    )

    # WHEN generating context
    context = await provider.provide_context(result)

    # THEN it contains key metrics
    assert "Average HRV: 60.0" in context
    assert "Average Resting HR: 50.0 bpm" in context
    assert "Status: Stable" in context
