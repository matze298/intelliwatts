"""Tests the intervals analysis module."""

from unittest.mock import MagicMock

import pytest

from app.intervals.analysis import (
    calculate_watts_per_kg,
    compute_analysis,
    compute_load,
)
from app.intervals.models import AnalysisResult
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
            max_hr=150.0,
            distance_km=5.0,
            elevation_gain=100.0,
            hr_zone_times=[0, 100, 200, 300, 0, 0, 0],
            power_zone_times=[{"secs": 100}, {"secs": 200}, {"secs": 300}, {"secs": 400}, {"secs": 500}],
            ftp=250.0,
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
    assert "activity" in analysis.provider_results
    assert len(analysis.widgets) > 0


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

    # THEN it returns results
    assert isinstance(analysis, AnalysisResult)
    assert "pmc" in analysis.provider_results


def test_compute_load(activities: list[ParsedActivity]) -> None:
    """Test that training load is computed correctly."""
    # GIVEN dummy activities
    # WHEN computing the training load
    load = compute_load(activities)

    # THEN load values are returned
    assert load.chronic >= 0
    assert load.acute >= 0
    assert load.training_stress_balance == load.chronic - load.acute


def test_compute_analysis_display_days(activities: list[ParsedActivity]) -> None:
    """Test filtering by display days."""
    # GIVEN an activity 10 days ago
    activities[0].date = "2026-04-01"

    # WHEN computing analysis for last 5 days
    analysis = compute_analysis(activities, display_days=5)

    # THEN it returns results
    assert isinstance(analysis, AnalysisResult)


def test_calculate_watts_per_kg_success() -> None:
    """Tests calculating power to weight ratio with valid inputs."""
    # GIVEN valid power (250W) and weight (70kg)
    power = 250.0
    weight = 70.0

    # WHEN calculating power to weight ratio
    result = calculate_watts_per_kg(weight, power)

    # THEN return the correct ratio (250 / 70 = 3.5714...)
    assert result == 3.5714285714285716


def test_calculate_watts_per_kg_zero_weight() -> None:
    """Tests that a zero weight returns 0."""
    # GIVEN a weight of zero
    power = 250.0
    weight = 0.0

    # WHEN calculating power to weight ratio
    result = calculate_watts_per_kg(weight, power)

    # THEN return 0
    assert result == 0.0


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
    assert "ftp_trajectory" in analysis.provider_results


def test_compute_power_curve_summary() -> None:
    """Tests the power curve summary calculation."""
    # GIVEN a mocked client that returns power curve data
    mock_client = MagicMock()
    mock_client.power_curves.return_value = {
        "list": [
            {
                "id": "90d",
                "points": [
                    {"secs": 5, "watts": 900},
                    {"secs": 60, "watts": 500},
                    {"secs": 300, "watts": 350},
                    {"secs": 1200, "watts": 300},
                ],
            }
        ]
    }

    # WHEN computing the analysis
    analysis = compute_analysis(
        [
            ParsedActivity(
                date="2026-04-01",
                duration_h=0.0,
                training_stress=0.0,
                avg_power=0.0,
                type="Ride",
                calories=0,
                avg_hr=0.0,
                max_hr=0.0,
                distance_km=0.0,
                elevation_gain=0.0,
                hr_zone_times=None,
                power_zone_times=None,
                ftp=None,
            )
        ],
        client=mock_client,
    )

    # THEN basic result is returned
    assert isinstance(analysis, AnalysisResult)
    assert "power_curve" in analysis.provider_results


def test_compute_analysis_empty() -> None:
    """Test compute analysis with empty inputs."""
    # GIVEN no inputs
    # WHEN computing analysis
    result = compute_analysis([], wellness_data=[], power_curve=[])
    # THEN returns empty result
    assert isinstance(result, AnalysisResult)
    assert not result.provider_results


def test_compute_load_no_pmc() -> None:
    """Test compute load when PMC provider returns no data."""
    # GIVEN no activities (so no PMC)
    # WHEN computing load
    load = compute_load([])
    # THEN returns zero load
    assert load.chronic == 0.0
    assert load.acute == 0.0
