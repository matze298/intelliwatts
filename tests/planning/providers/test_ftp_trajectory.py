"""Tests for the FTP trajectory provider."""

from unittest.mock import MagicMock

import polars as pl
import pytest

from app.intervals.client import IntervalsClient
from app.planning.providers.ftp_trajectory import FTPTrajectoryProvider, FTPTrajectoryResult


@pytest.mark.asyncio
async def test_ftp_trajectory_provider_context() -> None:
    """Test that FTPTrajectoryProvider returns the correct context string."""
    # GIVEN: A result object for testing provide_context
    result = FTPTrajectoryResult(current_ftp=260.0, lowest_ftp=250.0, highest_ftp=265.0, days_analyzed=30)

    provider = FTPTrajectoryProvider()

    # WHEN: Generating FTP trajectory context.
    context = await provider.provide_context(result)

    # THEN: The context should include the current FTP, historical FTP, and progress.
    assert "FTP History (Last 30 days):" in context
    assert "Current: 260.0W" in context
    assert "Range: 250.0W - 265.0W" in context


def test_ftp_trajectory_provider_no_data() -> None:
    """Test that FTPTrajectoryProvider handles missing data gracefully."""
    # GIVEN: An analysis result with no FTP trajectory.
    client = MagicMock(spec=IntervalsClient)
    analysis = MagicMock()
    analysis.ftp_trajectory = None
    analysis.daily_series = []

    provider = FTPTrajectoryProvider()

    # WHEN: Calculating FTP trajectory result with no data.
    daily_df = pl.DataFrame(analysis.daily_series)
    result = provider.calculate(daily_df, client=client, ftp_trajectory=None)

    # THEN: Result should be None.
    assert result is None
