"""Tests for the FTP trajectory provider."""

from app.planning.providers.ftp_trajectory import FTPTrajectoryProvider, FTPTrajectoryResult


def test_ftp_trajectory_provider_name() -> None:
    """Tests that the provider name is correct."""
    provider = FTPTrajectoryProvider()
    assert provider.get_name() == "ftp_trajectory"


def test_ftp_trajectory_widget() -> None:
    """Tests the dashboard widget formatting."""
    # GIVEN a successful FTP calculation
    provider = FTPTrajectoryProvider()
    result = FTPTrajectoryResult(dates=["2026-04-01", "2026-04-20"], ftp_values=[250.0, 260.0])

    # WHEN formatting for dashboard
    widget = provider.get_dashboard_widget(result)

    # THEN returns a widget with correct values
    assert widget is not None
    assert widget.name == "ftp_trajectory"
    assert widget.value == "260 W"
    assert widget.trend == "+10.0 W"
    assert widget.trend_positive is True
