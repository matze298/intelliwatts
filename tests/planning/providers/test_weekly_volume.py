"""Tests for the weekly volume provider."""

import polars as pl

from app.planning.providers.weekly_volume import WeeklyVolumeProvider


def test_weekly_volume_calculation() -> None:
    """Tests that weekly volume is correctly aggregated by week and type."""
    # GIVEN a daily_df spanning two weeks with different sports
    # Week 1: 2024-01-01 (Mon) to 2024-01-07 (Sun)
    # Week 2: 2024-01-08 (Mon) to 2024-01-14 (Sun)

    daily_df = pl.DataFrame({
        "date": [
            "2024-01-01",  # Mon, W1
            "2024-01-02",  # Tue, W1
            "2024-01-08",  # Mon, W2
            "2024-01-09",  # Tue, W2
        ],
        "types": [
            ["Ride"],
            ["Run", "Swim"],
            ["Ride"],
            ["Ride"],
        ],
        "activity_durations": [
            [2.0],
            [1.0, 0.5],
            [1.5],
            [1.5],
        ],
        "activity_tss": [
            [120.0],
            [60.0, 20.0],
            [90.0],
            [80.0],
        ],
    }).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    provider = WeeklyVolumeProvider()

    # WHEN calculating
    result = provider.calculate(daily_df)

    # THEN it should have two weeks
    assert result.has_data
    assert result.weeks == ["2024-01-01", "2024-01-08"]

    # AND Ride should have values for both weeks
    assert result.duration_by_type["Ride"] == [2.0, 3.0]
    assert result.tss_by_type["Ride"] == [120.0, 170.0]

    # AND Run should have value for W1 and 0 for W2
    assert result.duration_by_type["Run"] == [1.0, 0.0]
    assert result.tss_by_type["Run"] == [60.0, 0.0]

    # AND Swim should have value for W1 and 0 for W2
    assert result.duration_by_type["Swim"] == [0.5, 0.0]
    assert result.tss_by_type["Swim"] == [20.0, 0.0]


def test_weekly_volume_monday_start() -> None:
    """Tests that weeks correctly start on Monday."""
    # 2024-01-07 is Sunday
    # 2024-01-08 is Monday
    daily_df = pl.DataFrame({
        "date": ["2024-01-07", "2024-01-08"],
        "types": [["Ride"], ["Ride"]],
        "activity_durations": [[1.0], [1.0]],
        "activity_tss": [[50.0], [50.0]],
    }).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    provider = WeeklyVolumeProvider()
    result = provider.calculate(daily_df)

    # 2024-01-01 is the Monday of the week containing 2024-01-07
    # 2024-01-08 is the Monday of its own week
    assert result.weeks == ["2024-01-01", "2024-01-08"]


def test_weekly_volume_empty_df() -> None:
    """Tests handling of empty DataFrame."""
    daily_df = pl.DataFrame(
        schema={
            "date": pl.Date,
            "types": pl.List(pl.String),
            "activity_durations": pl.List(pl.Float64),
            "activity_tss": pl.List(pl.Float64),
        }
    )

    provider = WeeklyVolumeProvider()
    result = provider.calculate(daily_df)

    assert not result.has_data
    assert result.weeks == []


def test_weekly_volume_provider_name() -> None:
    """Tests provider name."""
    assert WeeklyVolumeProvider().get_name() == "weekly_volume"
