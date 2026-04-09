"""Tests the intervals analysis module."""

import math

import pytest

from app.intervals.analysis import compute_analysis, compute_load
from app.intervals.parser.activity import ParsedActivity


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
    assert math.isclose(analysis.daily_series[1]["ctl"], 50.47, rel_tol=0.001)
    assert math.isclose(analysis.daily_series[1]["atl"], 52.66, rel_tol=0.001)
    assert math.isclose(analysis.daily_series[1]["tsb"], -2.192, rel_tol=0.001)

    # THEN the weekly entries aggreagte as expected
    assert len(analysis.weekly_series) == 1
    assert analysis.weekly_series[0]["week"] == "2026-03-30"
    assert math.isclose(analysis.weekly_series[0]["duration_h"], 1.5, rel_tol=0.001)
    assert math.isclose(analysis.weekly_series[0]["training_stress"], 120.0, rel_tol=0.001)
    assert math.isclose(analysis.weekly_series[0]["distance_km"], 15.0, rel_tol=0.001)
    assert math.isclose(analysis.weekly_series[0]["elevation_gain"], 150.0, rel_tol=0.001)


def test_compute_load(activities: list[ParsedActivity]) -> None:
    """Tests the compute_load function."""
    # GIVEN dummy activities

    # WHEN computing the load
    load = compute_load(activities)

    # THEN the load is the load of the last day
    assert math.isclose(load.chronic, 50.47, rel_tol=0.001)
    assert math.isclose(load.acute, 52.66, rel_tol=0.001)
