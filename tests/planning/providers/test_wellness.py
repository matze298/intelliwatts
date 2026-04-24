"""Tests for the wellness provider."""

from app.planning.providers.wellness import WellnessProvider, WellnessResult


def test_wellness_provider_name() -> None:
    """Tests that the provider name is correct."""
    provider = WellnessProvider()
    assert provider.get_name() == "wellness"


def test_wellness_widget() -> None:
    """Tests the dashboard widget formatting."""
    # GIVEN a successful wellness calculation
    provider = WellnessProvider()
    result = WellnessResult(
        avg_hrv=60.0,
        avg_resting_hr=50.0,
        hrv_trend="improving",
    )

    # WHEN formatting for dashboard
    widget = provider.get_dashboard_widget(result)

    # THEN returns a widget with correct values
    assert widget is not None
    assert widget.name == "wellness"
    assert widget.value == "60 ms"
    assert widget.trend == "Improving"
    assert widget.trend_positive is True
