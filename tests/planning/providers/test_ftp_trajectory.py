"""Tests for the FTP trajectory provider."""

from unittest.mock import MagicMock

import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.ftp_trajectory import FTPTrajectoryProvider


@pytest.mark.asyncio
async def test_ftp_trajectory_provider_context() -> None:
    """Test that FTPTrajectoryProvider returns the correct context string."""
    # GIVEN: An IntervalsClient mocked to return activities that result in a specific FTP trajectory.
    client = MagicMock(spec=IntervalsClient)
    # Mocking activities enough to trigger the 28-day logic in compute_analysis
    client.activities.return_value = [
        {
            "start_date_local": "2026-03-20T10:00:00",
            "moving_time": 3600,
            "icu_training_load": 100,
            "type": "Ride",
            "icu_ftp": 250,
            "calories": 500,
            "icu_distance": 30000,
            "total_elevation_gain": 500,
        },
        {
            "start_date_local": "2026-04-20T10:00:00",
            "moving_time": 3600,
            "icu_training_load": 100,
            "type": "Ride",
            "icu_ftp": 260,
            "calories": 500,
            "icu_distance": 30000,
            "total_elevation_gain": 500,
        },
    ]

    provider = FTPTrajectoryProvider()

    # WHEN: Generating FTP trajectory context.
    context = await provider.provide_context(client, days=7)

    # THEN: The context should include the current FTP, historical FTP, and progress.
    assert "FTP Trajectory (Last 4 Weeks):" in context
    assert "Current FTP: 260.0W" in context
    assert "4 Weeks Ago: 250.0W" in context
    assert "Progress: +4.0%" in context


@pytest.mark.asyncio
async def test_ftp_trajectory_provider_no_data() -> None:
    """Test that FTPTrajectoryProvider handles missing data gracefully."""
    # GIVEN: An IntervalsClient returning no activities.
    client = MagicMock(spec=IntervalsClient)
    client.activities.return_value = []

    provider = FTPTrajectoryProvider()

    # WHEN: Generating FTP trajectory context.
    context = await provider.provide_context(client, days=7)

    # THEN: A helpful message should be returned.
    assert "No activities found to determine FTP trajectory." in context
