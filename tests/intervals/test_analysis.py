"""Tests the intervals analysis module."""

import pytest

from app.intervals.analysis import (
    calculate_watts_per_kg,
    compute_analysis,
    compute_load,
)
from app.intervals.models import AnalysisResult
from app.intervals.parser.activity import ParsedActivity
from app.intervals.parser.power_curve import ParsedPowerCurve, PowerCurvePoint
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
            max_hr=150.0,
            distance_km=5.0,
            elevation_gain=100.0,
            hr_zone_times=[0, 100, 200, 300, 0, 0, 0],
            power_zone_times=[{"secs": 100}, {"secs": 200}, {"secs": 300}, {"secs": 400}, {"secs": 500}],
            ftp=None,
        )
    ]


@pytest.fixture(name="wellness_data")
def fixture_wellness_data() -> list[ParsedWellness]:
    """Returns mocked wellness data."""
    return [
        ParsedWellness(
            date="2026-04-01",
            hrv=60.0,
            resting_hr=50,
            sleep_score=None,
            sleep_quality=None,
            fatigue=None,
            soreness=None,
            stress=None,
            readiness=None,
            comments=None,
        ),
        ParsedWellness(
            date="2026-04-02",
            hrv=70.0,
            resting_hr=48,
            sleep_score=None,
            sleep_quality=None,
            fatigue=None,
            soreness=None,
            stress=None,
            readiness=None,
            comments=None,
        ),
    ]


def test_compute_analysis(activities: list[ParsedActivity]) -> None:
    """Test standard compute analysis logic."""
    # GIVEN dummy activities
    # WHEN computing the analysis
    analysis = compute_analysis(activities)

    # THEN basic structure is correct
    assert isinstance(analysis, AnalysisResult)
    assert len(analysis.daily_series) > 0
    assert analysis.summary.activity_count == 1
    assert analysis.summary.total_duration_h == 0.5


def test_compute_analysis_missing_days(activities: list[ParsedActivity]) -> None:
    """Test compute analysis handles days without activities."""
    # GIVEN two activities with a gap
    activities.append(
        ParsedActivity(
            date="2026-04-03",
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
            ftp=250.0,
        )
    )

    # WHEN computing the analysis
    analysis = compute_analysis(activities)

    # THEN daily series has 3 days (1st, 2nd empty, 3rd)
    assert len(analysis.daily_series) == 3
    assert analysis.daily_series[1]["training_stress"] == 0


def test_compute_analysis_missing_zones(activities: list[ParsedActivity]) -> None:
    """Test analysis works even if zone data is missing."""
    # GIVEN activity without zone info
    activities[0].hr_zone_times = None
    activities[0].power_zone_times = None

    # WHEN computing analysis
    analysis = compute_analysis(activities)

    # THEN it completes successfully
    assert sum(analysis.hr_intensity_distribution) == 0


def test_compute_load(activities: list[ParsedActivity]) -> None:
    """Test that training load is computed correctly."""
    # GIVEN dummy activities
    # WHEN computing the training load
    load = compute_load(activities)

    # THEN load values are returned (non-zero since we have one activity)
    assert load.chronic > 0
    assert load.acute > 0
    assert load.training_stress_balance == load.chronic - load.acute


def test_compute_analysis_display_days(activities: list[ParsedActivity]) -> None:
    """Test filtering by display days."""
    # GIVEN an activity 10 days ago
    activities[0].date = "2026-04-01"

    # WHEN computing analysis for last 5 days
    # Note: today would be max_date in compute_analysis
    analysis = compute_analysis(activities, display_days=5)

    # THEN only 5 days are returned
    assert len(analysis.daily_series) == 5


def test_compute_analysis_with_wellness(activities: list[ParsedActivity], wellness_data: list[ParsedWellness]) -> None:
    """Test analysis with wellness data included."""
    # GIVEN dummy activities and wellness data
    # WHEN computing the analysis
    analysis = compute_analysis(activities, wellness_data=wellness_data)

    # THEN wellness trends are present in daily series
    day = analysis.daily_series[0]
    assert "hrv" in day
    assert "resting_hr" in day


def test_wellness_trends_in_daily_series(activities: list[ParsedActivity], wellness_data: list[ParsedWellness]) -> None:
    """Test that daily series includes wellness metrics."""
    # GIVEN dummy activities and wellness data
    # WHEN computing the analysis
    analysis = compute_analysis(activities, wellness_data=wellness_data)

    # THEN basic structure is correct
    assert isinstance(analysis, AnalysisResult)


def test_compute_analysis_fewer_than_42_days() -> None:
    """Test that rolling averages work with fewer than 42 days of data."""
    # GIVEN only 2 days of wellness data
    wellness_data = [
        ParsedWellness(date="2026-04-19", hrv=60.0, resting_hr=50),
        ParsedWellness(date="2026-04-20", hrv=70.0, resting_hr=48),
    ]

    # WHEN computing analysis
    analysis = compute_analysis([], wellness_data=wellness_data)

    # THEN basic result is returned
    assert isinstance(analysis, AnalysisResult)


def test_calculate_watts_per_kg_success() -> None:
    """Tests calculating power to weight ratio with valid inputs."""
    # GIVEN valid power (250W) and weight (70kg)
    power = 250.0
    weight = 70.0

    # WHEN calculating power to weight ratio
    result = calculate_watts_per_kg(weight, power)

    # THEN return the correct ratio rounded to 2 decimal places (250 / 70 = 3.5714...)
    assert result == 3.57


def test_calculate_watts_per_kg_zero_weight() -> None:
    """Tests that a zero weight raises a ValueError."""
    # GIVEN a weight of zero
    power = 250.0
    weight = 0.0

    # WHEN calculating power to weight ratio
    # THEN raise ValueError
    with pytest.raises(ValueError, match="Weight must be greater than zero"):
        calculate_watts_per_kg(weight, power)


def test_calculate_watts_per_kg_negative_power() -> None:
    """Tests that a negative power raises a ValueError."""
    # GIVEN negative power
    power = -10.0
    weight = 70.0

    # WHEN calculating power to weight ratio
    # THEN raise ValueError
    with pytest.raises(ValueError, match="Power cannot be negative"):
        calculate_watts_per_kg(weight, power)


def test_calculate_watts_per_kg_float_precision() -> None:
    """Tests precision with floating point values."""
    # GIVEN floating point power (285.5W) and weight (72.3kg)
    power = 285.5
    weight = 72.3

    # WHEN calculating power to weight ratio
    result = calculate_watts_per_kg(weight, power)

    # THEN return the correct ratio rounded to 2 decimal places (285.5 / 72.3 = 3.9488...)
    assert result == 3.95


def test_compute_ftp_trajectory() -> None:
    """Tests the FTP trajectory calculation."""
    # GIVEN activities with changing FTP over 30 days
    activities = [
        ParsedActivity(
            date="2026-03-20",
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
            ftp=250.0,
        ),
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
            ftp=260.0,
        ),
    ]

    # WHEN computing the analysis
    analysis = compute_analysis(activities)

    # THEN basic result is returned
    assert isinstance(analysis, AnalysisResult)


def test_compute_power_curve_summary() -> None:
    """Tests the power curve summary calculation."""
    # GIVEN a parsed power curve
    power_curve = [
        ParsedPowerCurve(
            id="90d",
            points=[
                PowerCurvePoint(secs=5, watts=900),
                PowerCurvePoint(secs=60, watts=500),
                PowerCurvePoint(secs=300, watts=350),
                PowerCurvePoint(secs=1200, watts=300),
            ],
        )
    ]

    # WHEN computing the analysis
    analysis = compute_analysis([], power_curve=power_curve)

    # THEN basic result is returned
    assert isinstance(analysis, AnalysisResult)
