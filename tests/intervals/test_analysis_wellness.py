"""Tests for wellness trend analysis."""

import pytest

from app.intervals.analysis import compute_analysis
from app.intervals.parser.activity import ParsedActivity
from app.intervals.parser.wellness import ParsedWellness


@pytest.fixture(name="activities")
def fixture_activities() -> list[ParsedActivity]:
    """Return dummy activities for testing."""
    return [
        ParsedActivity(
            date="2026-04-20",
            duration_h=1.0,
            training_stress=100.0,
            avg_power=200.0,
            type="Ride",
            calories=800,
            avg_hr=140.0,
            max_hr=160.0,
            distance_km=30.0,
            elevation_gain=300.0,
            hr_zone_times=None,
            power_zone_times=None,
        )
    ]


@pytest.fixture(name="wellness_data")
def fixture_wellness_data() -> list[ParsedWellness]:
    """Return dummy wellness data for testing."""
    # Creating a series of wellness data to test rolling averages
    # We need at least 42 days for a full 42d average, but we can test with fewer
    return [
        ParsedWellness(date="2026-04-19", hrv=60.0, resting_hr=50),
        ParsedWellness(date="2026-04-20", hrv=70.0, resting_hr=48),
    ]


def test_compute_analysis_with_wellness(activities: list[ParsedActivity], wellness_data: list[ParsedWellness]) -> None:
    """Test that compute_analysis correctly processes wellness data."""
    # WHEN computing analysis with wellness data
    # (We expect compute_analysis to accept wellness_data as an optional argument)
    analysis = compute_analysis(activities, wellness_data=wellness_data)

    # THEN the analysis result contains wellness info
    assert hasattr(analysis, "wellness_summary")
    assert analysis.wellness_summary is not None

    # Check 7-day averages (simple average of the two points provided)
    # (70 + 60) / 2 = 65.0
    assert analysis.wellness_summary["hrv_7d"] == 65.0
    # (48 + 50) / 2 = 49.0
    assert analysis.wellness_summary["resting_hr_7d"] == 49.0


def test_wellness_trends_in_daily_series(activities: list[ParsedActivity], wellness_data: list[ParsedWellness]) -> None:
    """Test that daily series includes wellness metrics."""
    analysis = compute_analysis(activities, wellness_data=wellness_data)

    # Check the last day in the daily series
    last_day = analysis.daily_series[-1]
    assert "hrv" in last_day
    assert last_day["hrv"] == 70.0
    assert "resting_hr" in last_day
    assert last_day["resting_hr"] == 48
