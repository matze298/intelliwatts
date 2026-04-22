"""Tests for the PMC provider."""

from datetime import date

import polars as pl

from app.planning.providers.pmc import PMCProvider, PMCResult


def test_pmc_provider_calculate_empty() -> None:
    """Test PMCProvider.calculate with empty data."""
    # GIVEN
    provider = PMCProvider()
    daily_df = pl.DataFrame(
        {"date": [], "training_stress": []}, schema={"date": pl.Date, "training_stress": pl.Float64}
    )

    # WHEN
    result = provider.calculate(daily_df)

    # THEN
    assert result.ctl == []
    assert result.atl == []
    assert result.tsb == []
    assert result.dates == []


def test_pmc_provider_calculate_with_data() -> None:
    """Test PMCProvider.calculate with sample data."""
    # GIVEN
    provider = PMCProvider()
    dates = [date(2024, 1, i + 1) for i in range(10)]
    training_stress = [10.0 * (i + 1) for i in range(10)]
    daily_df = pl.DataFrame({"date": dates, "training_stress": training_stress})

    # WHEN
    result = provider.calculate(daily_df)

    # THEN
    assert len(result.ctl) == 10
    assert len(result.atl) == 10
    assert len(result.tsb) == 10
    assert len(result.dates) == 10
    assert result.dates[0] == "2024-01-01"

    # Verify values are increasing
    assert result.ctl[0] < result.ctl[-1]
    assert result.atl[0] < result.atl[-1]


def test_pmc_provider_get_dashboard_widget() -> None:
    """Test PMCProvider.get_dashboard_widget."""
    # GIVEN
    provider = PMCProvider()
    result = PMCResult(ctl=[1.0], atl=[2.0], tsb=[-1.0], dates=["2024-01-01"])

    # WHEN
    widget = provider.get_dashboard_widget(result)

    # THEN
    assert widget is not None
    assert widget.name == "pmc"
    assert widget.title == "Fitness Trend"
    assert widget.custom_template == "widgets/pmc_chart.html"
    # For widget data, it's serialized to dict/JSON
    assert isinstance(widget.data, dict)
    assert widget.data["ctl"] == [1.0]
