"""Tests for the updated summary builder with wellness data."""

from app.intervals.analysis import TrainingLoad
from app.intervals.parser.activity import ParsedActivity
from app.planning.summary import PlanningConstraints, build_weekly_summary


def test_build_weekly_summary_with_wellness() -> None:
    """Test that build_weekly_summary includes wellness data."""
    # GIVEN activities, load, and wellness data
    activities = [
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
    load = TrainingLoad(chronic=50.0, acute=60.0)
    wellness_summary = {"hrv_7d": 65.0, "hrv_42d": 70.0, "resting_hr_7d": 49.0, "resting_hr_42d": 48.0}
    constraints = PlanningConstraints(weekly_hours=10.0, weekly_sessions=5)

    # WHEN building the summary
    summary = build_weekly_summary(activities, load, constraints=constraints, wellness_summary=wellness_summary)

    # THEN the summary contains the wellness data
    assert "wellness" in summary
    assert summary["wellness"] == wellness_summary
