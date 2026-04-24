"""Tests for the resting HR trend provider."""

import asyncio

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

    # THEN returns a widget with correct values
    assert widget is not None
    assert widget.name == "resting_hr"
    assert widget.value == "51 bpm"
    assert widget.trend == "Stable (Avg 52)"
    assert widget.trend_positive is True


def test_resting_hr_increasing_trend() -> None:
    """Tests the increasing trend detection."""
    # GIVEN an increasing HR calculation
    provider = RestingHRTrendProvider()
    result = RestingHRResult(current_hr=55.0, avg_hr=52.0, is_increasing=True, recent_trend=[52.0, 55.0])

    # WHEN providing context
    # THEN it should report increased status
    context = asyncio.run(provider.provide_context(result))

    assert "Resting HR is increased" in context
