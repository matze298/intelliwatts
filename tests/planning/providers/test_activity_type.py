"""Tests for the activity type provider."""

import polars as pl

from app.planning.providers.activity_type import ActivityTypeProvider


def test_activity_type_calculation() -> None:
    """Tests that activity types are correctly aggregated."""
    # GIVEN a daily_df with multiple sports on the same day
    daily_df = pl.DataFrame({
        "date": ["2026-04-01", "2026-04-01"],
        "types": [["Ride"], ["Run"]],
        "activity_durations": [[1.5], [0.5]],
        "training_stress": [100.0, 50.0],
        "duration_h": [1.5, 0.5],
        "distance_km": [40.0, 5.0],
    }).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    provider = ActivityTypeProvider()

    # WHEN calculating
    result = provider.calculate(daily_df)

    # THEN it sums durations by type
    assert result is not None
    assert result.type_durations["Ride"] == 1.5
    assert result.type_durations["Run"] == 0.5
    assert result.primary_sport == "Ride"
    assert result.total_hours == 2.0


def test_activity_type_provider_name() -> None:
    """Tests that the provider name is correct."""
    provider = ActivityTypeProvider()
    assert provider.get_name() == "activity_type"
