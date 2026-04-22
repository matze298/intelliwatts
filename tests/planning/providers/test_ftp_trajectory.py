"""Tests for the FTP trajectory provider."""

from unittest.mock import MagicMock

import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.ftp_trajectory import FTPTrajectoryProvider


@pytest.mark.asyncio
async def test_ftp_trajectory_provider_context() -> None:
    """Test that FTPTrajectoryProvider returns the correct context string."""
    # GIVEN: A mocked analysis result with an FTP trajectory.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.ftp_trajectory = {
        "current_ftp": 260.0,
        "ftp_4w_ago": 250.0,
        "change_pct": 4.0,
    }

    provider = FTPTrajectoryProvider()

    # WHEN: Generating FTP trajectory context.
    context = await provider.provide_context(client, days=7, analysis=analysis)

    # THEN: The context should include the current FTP, historical FTP, and progress from analysis.
    assert "FTP Trajectory (Last 4 Weeks):" in context
    assert "Current FTP: 260.0W" in context
    assert "4 Weeks Ago: 250.0W" in context
    assert "Progress: +4.0%" in context


@pytest.mark.asyncio
async def test_ftp_trajectory_provider_no_data() -> None:
    """Test that FTPTrajectoryProvider handles missing data gracefully."""
    # GIVEN: An analysis result with no FTP trajectory.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.ftp_trajectory = None

    provider = FTPTrajectoryProvider()

    # WHEN: Generating FTP trajectory context.
    context = await provider.provide_context(client, days=7, analysis=analysis)

    # THEN: A helpful message should be returned.
    assert "Current FTP data unavailable." in context
