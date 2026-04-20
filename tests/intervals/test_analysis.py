"""Tests the intervals analysis module."""

import math

import pytest

from app.intervals.analysis import compute_analysis, compute_athlete_status, compute_load
from app.intervals.parser.activity import ParsedActivity
from app.intervals.parser.wellness import ParsedWellness


@pytest.fixture(name="activities")
def fixture_activities() -> list[ParsedActivity]:
    """Returns mocked activitites."""
    return [
        ParsedActivity(
            date="2026-04-01",
            duration_h=0.5,
            training_stress=50.0,
            avg_power=100.0,
            type="Run",
            calories=400,
            avg_hr=120.0,
            max_hr=140.0,
            distance_km=5.0,
            elevation_gain=50.0,
            hr_zone_times=[0, 300, 600, 600, 300, 0, 0],
            power_zone_times=[{"secs": 100}, {"secs": 200}, {"secs": 300}, {"secs": 400}, {"secs": 500}],
        ),
        ParsedActivity(
            date="2026-04-02",
            duration_h=1.0,
            training_stress=70.0,
            avg_power=150.0,
            type="Run",
            calories=500,
            avg_hr=130.0,
            max_hr=150.0,
            distance_km=10.0,
            elevation_gain=100.0,
            hr_zone_times=[0, 300, 600, 600, 300, 0, 0],
            power_zone_times=[{"secs": 100}, {"secs": 200}, {"secs": 300}, {"secs": 400}, {"secs": 500}],
        ),
    ]


@pytest.fixture(name="wellness_data")
def fixture_wellness_data() -> list[ParsedWellness]:
    """Return dummy wellness data for testing."""
    # Creating a series of wellness data to test rolling averages
    # We need at least 42 days for a full 42d average, but we can test with fewer
    return [
        ParsedWellness(date="2026-04-01", hrv=60.0, resting_hr=50),
        ParsedWellness(date="2026-04-02", hrv=70.0, resting_hr=48),
    ]


def test_compute_analysis(activities: list[ParsedActivity]) -> None:
    """Tests the compute_analysis function."""
    # GIVEN dummy activities

    # WHEN computing the analysis
    analysis = compute_analysis(activities)

    # THEN the daily entries are as expected
    assert len(analysis.daily_series) == len(activities)
    assert analysis.daily_series[0]["date"] == "2026-04-01"
    assert math.isclose(analysis.daily_series[0]["ctl"], activities[0].training_stress, rel_tol=0.001)
    assert math.isclose(analysis.daily_series[0]["atl"], activities[0].training_stress, rel_tol=0.001)
    assert math.isclose(analysis.daily_series[0]["tsb"], 0.0, rel_tol=0.001)
    assert analysis.daily_series[1]["date"] == "2026-04-02"
    assert math.isclose(analysis.daily_series[1]["ctl"], 50.471, rel_tol=0.001)
    assert math.isclose(analysis.daily_series[1]["atl"], 52.662, rel_tol=0.001)
    assert math.isclose(analysis.daily_series[1]["tsb"], -2.192, rel_tol=0.001)

    # THEN the weekly entries aggreagte as expected
    assert len(analysis.weekly_series) == 1
    assert analysis.weekly_series[0]["week"] == "2026-03-30"
    assert math.isclose(analysis.weekly_series[0]["duration_h"], 1.5, rel_tol=0.001)
    assert math.isclose(analysis.weekly_series[0]["training_stress"], 120.0, rel_tol=0.001)
    assert math.isclose(analysis.weekly_series[0]["distance_km"], 15.0, rel_tol=0.001)
    assert math.isclose(analysis.weekly_series[0]["elevation_gain"], 150.0, rel_tol=0.001)


def test_compute_analysis_empty() -> None:
    """Tests the compute_analysis function with empty activities."""
    # GIVEN no activities
    activities = []

    # WHEN computing the analysis
    analysis = compute_analysis(activities)

    # THEN the result is empty but valid
    assert analysis.daily_series == []
    assert analysis.weekly_series == []
    assert analysis.summary.activity_count == 0


def test_compute_analysis_missing_days(activities: list[ParsedActivity]) -> None:
    """Tests the compute_analysis function with missing days in the sequence."""
    # GIVEN activities with a gap
    activities_with_gap = [
        activities[0],
        ParsedActivity(
            date="2026-04-05",
            duration_h=1.0,
            training_stress=100.0,
            avg_power=200.0,
            type="Ride",
            calories=800,
            avg_hr=140.0,
            max_hr=160.0,
            distance_km=30.0,
            elevation_gain=300.0,
            hr_zone_times=[0, 0, 0, 600, 1200, 1200, 600],
            power_zone_times=[{"secs": 0}, {"secs": 300}, {"secs": 600}, {"secs": 900}, {"secs": 1800}],
        ),
    ]

    # WHEN computing the analysis
    analysis = compute_analysis(activities_with_gap)

    # THEN the series includes the missing days (total 5 days from April 1 to April 5)
    assert len(analysis.daily_series) == 5
    assert analysis.daily_series[0]["date"] == "2026-04-01"
    assert analysis.daily_series[1]["date"] == "2026-04-02"
    assert analysis.daily_series[4]["date"] == "2026-04-05"

    # AND the summary is correct
    assert analysis.summary.activity_count == 2
    assert analysis.summary.total_training_stress == 150.0


def test_compute_analysis_missing_zones() -> None:
    """Tests the compute_analysis function with missing zone data."""
    # GIVEN activity without zone data
    activities = [
        ParsedActivity(
            date="2026-04-01",
            duration_h=0.5,
            training_stress=50.0,
            avg_power=100.0,
            type="Run",
            calories=400,
            avg_hr=120.0,
            max_hr=140.0,
            distance_km=5.0,
            elevation_gain=50.0,
            hr_zone_times=None,
            power_zone_times=None,
        )
    ]

    # WHEN computing the analysis
    analysis = compute_analysis(activities)

    # THEN the distributions are empty/handled
    assert all(v == 0 for v in analysis.hr_intensity_distribution)
    assert analysis.power_intensity_distribution == []


def test_compute_load(activities: list[ParsedActivity]) -> None:
    """Tests the compute_load function."""
    # GIVEN dummy activities

    # WHEN computing the load
    load = compute_load(activities)

    # THEN the load is the load of the last day
    assert math.isclose(load.chronic, 50.471, rel_tol=0.001)
    assert math.isclose(load.acute, 52.662, rel_tol=0.001)


def test_compute_analysis_display_days(activities: list[ParsedActivity]) -> None:
    """Tests the compute_analysis function with display_days."""
    # GIVEN activities over two days
    # WHEN computing analysis with display_days=1
    analysis = compute_analysis(activities, display_days=1)

    # THEN only the last day is in the daily series
    assert len(analysis.daily_series) == 1
    assert analysis.daily_series[0]["date"] == "2026-04-02"

    # AND summary only includes the last day
    assert analysis.summary.activity_count == 1
    assert math.isclose(analysis.summary.total_training_stress, 70.0, rel_tol=0.001)

    # AND CTL/ATL are still computed correctly (using the previous day)
    assert math.isclose(analysis.daily_series[0]["ctl"], 50.471, rel_tol=0.001)
    assert math.isclose(analysis.daily_series[0]["atl"], 52.662, rel_tol=0.001)


def test_compute_analysis_with_wellness(activities: list[ParsedActivity], wellness_data: list[ParsedWellness]) -> None:
    """Test that compute_analysis correctly processes wellness data."""
    # GIVEN dummy activities and wellness data

    # WHEN computing analysis with wellness data
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
    # GIVEN dummy activities and wellness data
    # WHEN computing the analysis
    analysis = compute_analysis(activities, wellness_data=wellness_data)

    # THEN the wellness trends are as expected
    last_day = analysis.daily_series[-1]
    assert "hrv" in last_day
    assert last_day["hrv"] == 70.0
    assert "resting_hr" in last_day
    assert last_day["resting_hr"] == 48


def test_compute_analysis_fewer_than_42_days() -> None:
    """Test that rolling averages work with fewer than 42 days of data."""
    # GIVEN only 2 days of wellness data
    wellness_data = [
        ParsedWellness(date="2026-04-19", hrv=60.0, resting_hr=50),
        ParsedWellness(date="2026-04-20", hrv=70.0, resting_hr=48),
    ]

    # WHEN computing analysis
    analysis = compute_analysis([], wellness_data=wellness_data)

    # THEN wellness_summary is still computed (partial averages)
    assert analysis.wellness_summary is not None
    assert analysis.wellness_summary["hrv_42d"] == 65.0  # Average of 60 and 70
    assert analysis.wellness_summary["resting_hr_42d"] == 49.0  # Average of 50 and 48


def test_compute_athlete_status(activities: list[ParsedActivity], wellness_data: list[ParsedWellness]) -> None:
    """Tests the compute_athlete_status function."""
    # GIVEN dummy activities and wellness data

    # WHEN computing the athlete status
    status = compute_athlete_status(activities, wellness_data=wellness_data)

    # THEN the status contains load and wellness
    assert status.load.chronic == 50.471
    assert status.wellness is not None
    assert math.isclose(status.wellness["hrv_7d"], 65.0, rel_tol=0.001)
