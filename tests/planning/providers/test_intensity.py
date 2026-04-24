"""Tests for the intensity provider."""

import polars as pl
import pytest

from app.planning.providers.intensity import IntensityProvider, IntensityResult


def test_intensity_provider_name() -> None:
    """Tests that the provider name is correct."""
    provider = IntensityProvider()
    assert provider.get_name() == "intensity"


def test_intensity_calculation() -> None:
    """Tests the intensity aggregation and style detection."""
    # GIVEN
    # HR Zones: Z1, Z2, Z3, Z4, Z5, Z6, Z7
    # 80/20 polarized example
    daily_df = pl.DataFrame({
        "date": ["2026-04-01", "2026-04-02"],
        "hr_zone_times": [[600, 1400, 0, 0, 0, 0, 0], [1200, 2800, 0, 500, 500, 0, 0]],
        "power_zone_times": [[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]],
        "training_stress": [50.0, 100.0],
    })

    provider = IntensityProvider()

    # WHEN
    result = provider.calculate(daily_df)

    # THEN
    # Total HR secs = 600+1400 + 1200+2800+500+500 = 2000 + 5000 = 7000
    # Z1 total = 1800 (1800/7000 = 25.7%)
    # Z2 total = 4200 (4200/7000 = 60.0%)
    # Low Intensity = 25.7 + 60.0 = 85.7%
    assert result.polarized_score > 85
    assert result.style == "Highly Polarized"
    assert result.hr_total_mins == round(7000 / 60, 1)


@pytest.mark.asyncio
async def test_intensity_context() -> None:
    """Tests context generation."""
    # GIVEN
    provider = IntensityProvider()
    result = IntensityResult(
        hr_zones_pct=[25.0, 60.0, 5.0, 10.0, 0.0, 0.0, 0.0],
        power_zones_pct=[],
        hr_total_mins=100.0,
        power_total_mins=0.0,
        polarized_score=85.0,
        style="Polarized",
    )

    # WHEN
    context = await provider.provide_context(result)

    # THEN
    assert "85.0% Low" in context
    assert "Polarized" in context
