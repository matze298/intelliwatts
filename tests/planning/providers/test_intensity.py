"""Tests for the intensity provider."""

import polars as pl
import pytest

from app.planning.providers.intensity import IntensityProvider, IntensityResult


def test_intensity_provider_name() -> None:
    """Tests that the provider name is correct."""
    # GIVEN: An IntensityProvider instance
    provider = IntensityProvider()

    # WHEN: Getting the provider name
    name = provider.get_name()

    # THEN: The name should be "intensity"
    assert name == "intensity"


def test_intensity_calculation() -> None:
    """Tests the intensity aggregation and style detection."""
    # GIVEN: A daily_df with aggregated zone data (list of lists of ints)
    # Day 1: 1 activity (2000s total)
    # Day 2: 1 activity (5000s total)
    # Combined: Z1=1800, Z2=4200, Z3=0, Z4=500, Z5=500 -> 7000s Total.
    daily_df = pl.DataFrame({
        "date": ["2026-04-01", "2026-04-02"],
        "hr_zone_times": [[[600, 1400, 0, 0, 0, 0, 0]], [[1200, 2800, 0, 500, 500, 0, 0]]],
        "power_zone_times": [[[0, 0, 0, 0, 0, 0, 0, 0]], [[0, 0, 0, 0, 0, 0, 0, 0]]],
        "training_stress": [50.0, 100.0],
    })

    provider = IntensityProvider()

    # WHEN: Calculating the intensity distribution
    result = provider.calculate(daily_df)

    # THEN: The style should be detected as Highly Polarized (>85% in Z1+Z2)
    # Low Intensity = (1800 + 4200) / 7000 = 85.7%
    assert result.polarized_score > 85
    assert result.style == "Highly Polarized"
    assert result.hr_total_mins == round(7000 / 60, 1)


@pytest.mark.asyncio
async def test_intensity_context() -> None:
    """Tests context generation for the LLM coach."""
    # GIVEN: An IntensityProvider and a mocked IntensityResult
    provider = IntensityProvider()
    result = IntensityResult(
        hr_zones_pct=[25.0, 60.0, 5.0, 10.0, 0.0, 0.0, 0.0],
        power_zones_pct=[],
        power_ss_pct=0.0,
        hr_total_mins=100.0,
        power_total_mins=0.0,
        polarized_score=85.0,
        style="Polarized",
    )

    # WHEN: Generating the context string
    context = await provider.provide_context(result)

    # THEN: The context contains the expected distribution percentages and style
    assert "85.0% Low" in context
    assert "Polarized" in context
