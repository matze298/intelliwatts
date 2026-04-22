"""Tests for the PMC provider."""

import math
from datetime import date

import polars as pl

from app.planning.providers.pmc import PMCProvider, PMCResult


def test_pmc_provider_calculate_empty() -> None:
    """Test PMCProvider.calculate with empty data."""
    # GIVEN: an empty DataFrame representing no activities
    provider = PMCProvider()
    daily_df = pl.DataFrame(
        {"date": [], "training_stress": []}, schema={"date": pl.Date, "training_stress": pl.Float64}
    )

    # WHEN: computing the PMC result
    result = provider.calculate(daily_df)

    # THEN: the result should be empty lists for all metrics
    assert result.ctl == []
    assert result.atl == []
    assert result.tsb == []
    assert result.dates == []


def test_pmc_provider_calculate_with_data() -> None:
    """Test PMCProvider.calculate with sample data."""
    # GIVEN: a provider and 10 days of synthetic training stress data
    provider = PMCProvider()
    dates = [date(2024, 1, i + 1) for i in range(10)]
    training_stress = [10.0 * (i + 1) for i in range(10)]
    daily_df = pl.DataFrame({"date": dates, "training_stress": training_stress})

    # WHEN: calculating the PMC values
    result = provider.calculate(daily_df)

    # THEN: the result should contain exactly 10 data points
    assert len(result.ctl) == 10
    assert len(result.atl) == 10
    assert len(result.tsb) == 10
    assert len(result.dates) == 10
    assert result.dates[0] == "2024-01-01"

    # THEN: the EWMA computation should output specific initial values
    # For day 1 (stress=10.0), EWMA initializes at 10.0
    assert math.isclose(result.ctl[0], 10.0)
    assert math.isclose(result.atl[0], 10.0)
    assert math.isclose(result.tsb[0], 0.0)

    # Verify values are increasing
    assert result.ctl[0] < result.ctl[-1]
    assert result.atl[0] < result.atl[-1]


def test_pmc_provider_get_dashboard_widget() -> None:
    """Test PMCProvider.get_dashboard_widget."""
    # GIVEN: a provider and a dummy PMC result
    provider = PMCProvider()
    result = PMCResult(ctl=[1.0], atl=[2.0], tsb=[-1.0], dates=["2024-01-01"])

    # WHEN: retrieving the dashboard widget
    widget = provider.get_dashboard_widget(result)

    # THEN: a valid custom template widget is returned with serialized data
    assert widget is not None
    assert widget.name == "pmc"
    assert widget.title == "Fitness Trend"
    assert widget.custom_template == "widgets/pmc_chart.html"
    # For widget data, it's serialized to dict/JSON
    assert isinstance(widget.data, dict)
    assert widget.data["ctl"] == [1.0]
