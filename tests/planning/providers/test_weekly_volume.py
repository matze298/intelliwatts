"""Tests for the weekly volume provider."""

import polars as pl
import pytest

from app.planning.providers.weekly_volume import WeeklyVolumeProvider, WeeklyVolumeResult


def test_weekly_volume_calculation() -> None:
    """Tests that weekly volume is correctly aggregated by week and type."""
    # GIVEN a daily_df spanning two weeks with different sports
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
    # GIVEN a daily_df spanning a week boundary (Sunday to Monday)
    # 2024-01-07 is Sunday
    # 2024-01-08 is Monday
    daily_df = pl.DataFrame({
        "date": ["2024-01-07", "2024-01-08"],
        "types": [["Ride"], ["Ride"]],
        "activity_durations": [[1.0], [1.0]],
        "activity_tss": [[50.0], [50.0]],
    }).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    provider = WeeklyVolumeProvider()

    # WHEN calculating
    result = provider.calculate(daily_df)

    # THEN it should group by Monday of each week
    # 2024-01-01 is the Monday of the week containing 2024-01-07
    # 2024-01-08 is the Monday of its own week
    assert result.weeks == ["2024-01-01", "2024-01-08"]


def test_weekly_volume_gaps_and_display_days() -> None:
    """Tests that weekly volume handles gaps and display_days correctly."""
    # GIVEN a daily_df spanning 4 weeks, but only having activities in Week 1 and Week 4
    # Max date is 2024-01-22
    daily_df = pl.DataFrame({
        "date": [
            "2024-01-01",  # Mon W1
            "2024-01-22",  # Mon W4
        ],
        "types": [
            ["Ride"],
            ["Ride"],
        ],
        "activity_durations": [
            [2.0],
            [2.0],
        ],
        "activity_tss": [
            [100.0],
            [100.0],
        ],
    }).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    provider = WeeklyVolumeProvider()

    # WHEN calculating with display_days=28 (4 weeks)
    # display_days=28 from 2024-01-22 should cover 4 weeks starting 2024-01-01
    result = provider.calculate(daily_df, display_days=28)

    # THEN it should have four weeks
    assert result.has_data
    assert result.weeks == ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22"]

    # AND Ride should have 0.0 for the middle weeks
    assert result.duration_by_type["Ride"] == [2.0, 0.0, 0.0, 2.0]
    assert result.tss_by_type["Ride"] == [100.0, 0.0, 0.0, 100.0]


def test_weekly_volume_empty_df() -> None:
    """Tests handling of empty DataFrame."""
    # GIVEN an empty daily_df
    daily_df = pl.DataFrame(
        schema={
            "date": pl.Date,
            "types": pl.List(pl.String),
            "activity_durations": pl.List(pl.Float64),
            "activity_tss": pl.List(pl.Float64),
        }
    )

    provider = WeeklyVolumeProvider()

    # WHEN calculating
    result = provider.calculate(daily_df)

    # THEN it should return an empty result
    assert not result.has_data
    assert result.weeks == []
    assert result.duration_by_type == {}
    assert result.tss_by_type == {}


@pytest.mark.asyncio
async def test_weekly_volume_provide_context() -> None:
    """Tests provide_context method."""
    # GIVEN a result with multiple sports
    result = WeeklyVolumeResult(
        weeks=["2024-01-01", "2024-01-08"],
        duration_by_type={"Ride": [2.0, 3.0], "Run": [1.0, 0.0]},
        tss_by_type={"Ride": [100.0, 150.0], "Run": [60.0, 0.0]},
        has_data=True,
    )
    provider = WeeklyVolumeProvider()

    # WHEN providing context
    context = await provider.provide_context(result)

    # THEN it should contain summary for the last week
    assert "Weekly Volume Summary (Last Week: 2024-01-08):" in context
    assert "- Ride: 3.0h, 150 TSS" in context
    assert "Run" not in context  # Run is 0 in last week


def test_weekly_volume_dashboard_widget() -> None:
    """Tests get_dashboard_widget method."""
    # GIVEN a result
    result = WeeklyVolumeResult(
        weeks=["2024-01-01"],
        duration_by_type={"Ride": [2.0]},
        tss_by_type={"Ride": [100.0]},
        has_data=True,
    )
    provider = WeeklyVolumeProvider()

    # WHEN getting the widget
    widget = provider.get_dashboard_widget(result)

    # THEN it should be correctly formatted
    assert widget is not None
    assert widget.name == "weekly_volume"
    assert widget.title == "Weekly Volume"
    assert widget.custom_template == "widgets/weekly_volume_chart.html"

    # Explicitly check data to satisfy type checker
    assert widget.data is not None
    assert widget.data["weeks"] == ["2024-01-01"]
    assert widget.data["duration_by_type"] == {"Ride": [2.0]}


def test_weekly_volume_provider_name() -> None:
    """Tests provider name."""
    assert WeeklyVolumeProvider().get_name() == "weekly_volume"
