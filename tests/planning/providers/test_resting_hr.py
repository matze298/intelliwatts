"""Tests for the resting HR trend provider."""

from app.planning.providers.resting_hr import RestingHRResult, RestingHRTrendProvider


def test_resting_hr_provider_name() -> None:
    """Tests that the provider name is correct."""
    provider = RestingHRTrendProvider()
    assert provider.get_name() == "resting_hr"


def test_resting_hr_widget() -> None:
    """Tests the dashboard widget formatting."""
    # GIVEN a resting HR calculation
    provider = RestingHRTrendProvider()
    result = RestingHRResult(current_hr=51.0, avg_hr=52.0, is_increasing=False, recent_trend=[52.0, 51.0])

    # WHEN formatting for dashboard
    widget = provider.get_dashboard_widget(result)

    # THEN returns None (no widget for resting_hr currently)
    assert widget is None
