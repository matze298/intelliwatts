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
    result = FTPTrajectoryResult(current_ftp=260.0, ftp_4w_ago=250.0, change_pct=4.0, days_analyzed=30)

    provider = FTPTrajectoryProvider()

    # WHEN: Generating FTP trajectory context.
    context = await provider.provide_context(result)

    # THEN: The context should include the current FTP and historical FTP.
    assert "FTP History (Last 30 days):" in context
    assert "Current: 260W" in context
    assert "Range: 250.0W -> 260W" in context


def test_ftp_trajectory_provider_no_data() -> None:
    """Test that FTPTrajectoryProvider handles missing data gracefully."""
    # GIVEN: An empty daily series.
    client = MagicMock(spec=IntervalsClient)
    daily_df = pl.DataFrame([])

    provider = FTPTrajectoryProvider()

    # WHEN: Calculating FTP trajectory result with no data.
    result = provider.calculate(daily_df, client=client)

    # THEN: Result should be None.
    assert result is None
