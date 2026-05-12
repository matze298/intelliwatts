"""Tests for the activity history provider."""

import polars as pl
import pytest

from app.planning.providers.activity_history import (
    ActivityHistoryEntry,
    ActivityHistoryProvider,
    ActivityHistoryResult,
)


def test_activity_history_calculation() -> None:
    """Tests that recent activity history is reconstructed from daily aggregates."""
    # GIVEN a daily aggregate with multiple activities across two days
    daily_df = pl.DataFrame({
        "date": ["2026-04-01", "2026-04-02"],
        "types": [["Ride", "Run"], ["Ride"]],
        "activity_durations": [[2.0, 0.8], [1.5]],
        "activity_tss": [[120.0, 45.0], [90.0]],
        "activity_distances": [[65.2, 8.1], [42.0]],
        "activity_avg_power": [[210.0, None], [195.0]],
        "activity_avg_hr": [[145.0, 152.0], [140.0]],
        "activity_max_hr": [[172.0, 170.0], [168.0]],
        "activity_elevation_gain": [[620.0, 35.0], [410.0]],
        "activity_ftp": [[260.0, None], [260.0]],
    }).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    provider = ActivityHistoryProvider()

    # WHEN calculating activity history
    result = provider.calculate(daily_df)

    # THEN the latest activities are reconstructed in reverse-chronological order
    assert result is not None
    assert result.has_data
    assert len(result.activities) == 3
    assert result.activities[0].date == "2026-04-02"
    assert result.activities[0].activity_type == "Ride"
    assert result.activities[0].duration_h == 1.5
    assert result.activities[1].activity_type == "Ride"
    assert result.activities[2].activity_type == "Run"
    assert result.activities[2].avg_power is None


def test_activity_history_respects_display_days() -> None:
    """Tests that display_days filters the reconstructed history."""
    # GIVEN activities that span beyond the requested display range
    daily_df = pl.DataFrame({
        "date": ["2026-04-01", "2026-04-10"],
        "types": [["Ride"], ["Run"]],
        "activity_durations": [[2.0], [1.0]],
        "activity_tss": [[120.0], [50.0]],
        "activity_distances": [[60.0], [10.0]],
        "activity_avg_power": [[210.0], [None]],
        "activity_avg_hr": [[145.0], [150.0]],
        "activity_max_hr": [[172.0], [168.0]],
        "activity_elevation_gain": [[620.0], [40.0]],
        "activity_ftp": [[260.0], [None]],
    }).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))

    provider = ActivityHistoryProvider()

    # WHEN requesting only the last 7 days
    result = provider.calculate(daily_df, display_days=7)

    # THEN only the recent entry remains
    assert result is not None
    assert [activity.date for activity in result.activities] == ["2026-04-10"]


@pytest.mark.asyncio
async def test_activity_history_context() -> None:
    """Tests that the provider emits a compact recent activity summary."""
    # GIVEN a small history result
    result = ActivityHistoryResult(
        activities=[
            ActivityHistoryEntry(
                date="2026-04-10",
                activity_type="Ride",
                duration_h=1.5,
                training_stress=90.0,
                distance_km=42.0,
                avg_power=195.0,
                avg_hr=140.0,
                max_hr=168.0,
                elevation_gain=410.0,
                ftp=260.0,
            )
        ],
        has_data=True,
    )
    provider = ActivityHistoryProvider()

    # WHEN generating the planning context
    context = await provider.provide_context(result)

    # THEN it contains the recent activity summary
    assert "Recent Activities:" in context
    assert "2026-04-10: Ride, 1.5h, 90 TSS, 42.0km" in context


def test_activity_history_widget() -> None:
    """Tests that the dashboard widget is populated for the custom template."""
    # GIVEN a recent activity history result
    result = ActivityHistoryResult(
        activities=[
            ActivityHistoryEntry(
                date="2026-04-10",
                activity_type="Ride",
                duration_h=1.5,
                training_stress=90.0,
                distance_km=42.0,
                avg_power=195.0,
                avg_hr=140.0,
                max_hr=168.0,
                elevation_gain=410.0,
                ftp=260.0,
            )
        ],
        has_data=True,
    )
    provider = ActivityHistoryProvider()

    # WHEN building the dashboard widget
    widget = provider.get_dashboard_widget(result)

    # THEN the custom template and activity payload are present
    assert widget is not None
    assert widget.name == "activity_history"
    assert widget.title == "Recent Activity History"
    assert widget.custom_template == "widgets/activity_history.html"
    assert widget.data is not None
    assert widget.data["activities"][0]["type"] == "Ride"
    assert widget.data["activities"][0]["avg_power"] == 195.0
