"""Intensity distribution metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient

# Constants for training styles
HIGHLY_POLARIZED_THRESHOLD = 85
THRESHOLD_PYRAMIDAL_THRESHOLD = 70
MIN_ZONES_FOR_POLARIZED = 2


@dataclass(frozen=True)
class IntensityResult:
    """Result of the intensity calculation."""

    hr_zones_pct: list[float]
    power_zones_pct: list[float]
    hr_total_mins: float
    power_total_mins: float
    polarized_score: float  # % of low intensity (Z1-Z2)
    style: str


class IntensityProvider(MetricProvider[IntensityResult]):
    """Provides intensity distribution context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "intensity"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
    ) -> IntensityResult:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The structured calculation result.
        """
        hr_totals = _sum_zones(daily_df, "hr_zone_times")
        power_totals = _sum_zones(daily_df, "power_zone_times")

        hr_sum_secs = sum(hr_totals)
        power_sum_secs = sum(power_totals)

        hr_zones_pct = [round((z / hr_sum_secs) * 100, 1) if hr_sum_secs > 0 else 0.0 for z in hr_totals]
        power_zones_pct = [round((z / power_sum_secs) * 100, 1) if power_sum_secs > 0 else 0.0 for z in power_totals]

        # Calculate polarized score (Z1 + Z2)
        polarized_score = 0.0
        if len(hr_zones_pct) >= MIN_ZONES_FOR_POLARIZED:
            polarized_score = hr_zones_pct[0] + hr_zones_pct[1]
        elif len(power_zones_pct) >= MIN_ZONES_FOR_POLARIZED:
            polarized_score = power_zones_pct[0] + power_zones_pct[1]

        style = _detect_style(polarized_score)

        return IntensityResult(
            hr_zones_pct=hr_zones_pct,
            power_zones_pct=power_zones_pct,
            hr_total_mins=round(hr_sum_secs / 60, 1),
            power_total_mins=round(power_sum_secs / 60, 1),
            polarized_score=polarized_score,
            style=style,
        )

    @override
    async def provide_context(self, result: IntensityResult) -> str:
        """Provides intensity context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the intensity context.
        """
        if not result.hr_zones_pct and not result.power_zones_pct:
            return "No intensity distribution data available."

        context = "Intensity Distribution (Last Lookback Period):\n"
        if result.hr_zones_pct:
            low = sum(result.hr_zones_pct[:MIN_ZONES_FOR_POLARIZED])
            # Z3 is index 2, Z4 is index 3
            mid_idx = 2
            high_start_idx = 3
            mid = result.hr_zones_pct[mid_idx] if len(result.hr_zones_pct) > mid_idx else 0
            high = sum(result.hr_zones_pct[high_start_idx:]) if len(result.hr_zones_pct) > high_start_idx else 0
            context += f"- Heart Rate: {low:.1f}% Low / {mid:.1f}% Mid / {high:.1f}% High\n"

        context += f"Overall Style: {result.style}"
        return context

    @override
    def get_dashboard_widget(self, result: IntensityResult, display_days: int | None = None) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if not result.hr_zones_pct and not result.power_zones_pct:
            return None

        return DashboardWidget(
            name="intensity",
            title="Intensity Distribution",
            custom_template="widgets/intensity_chart.html",
            data={
                "hr_zones": result.hr_zones_pct,
                "power_zones": result.power_zones_pct,
                "style": result.style,
                "polarized_score": result.polarized_score,
            },
        )


def _sum_zones(daily_df: pl.DataFrame, col_name: str) -> list[int]:
    """Sum zone times across all days.

    Args:
        daily_df: The daily dataframe.
        col_name: The column name to sum.

    Returns:
        The list of summed zone times.
    """
    if col_name not in daily_df.columns:
        return []

    raw_data = daily_df[col_name].to_list()
    flattened = _flatten_zone_data(raw_data)

    if not flattened:
        return []

    max_len = max(len(row) for row in flattened)
    totals = [0] * max_len
    for row in flattened:
        for i, val in enumerate(row):
            if val is not None:
                totals[i] += val.get("secs", 0) if isinstance(val, dict) else val
    return totals


def _flatten_zone_data(raw_data: list[Any]) -> list[list[Any]]:
    """Flatten nested zone data from aggregation.

    Args:
        raw_data: List of potentially nested zone time data.

    Returns:
        Flattened list of lists.
    """
    flattened = []
    for item in raw_data:
        if item is None:
            continue
        if isinstance(item, list) and len(item) > 0 and isinstance(item[0], list):
            flattened.extend([sub for sub in item if sub])
        elif isinstance(item, list):
            flattened.append(item)
    return flattened


def _detect_style(polarized_score: float) -> str:
    """Detect the training style based on the polarized score.

    Args:
        polarized_score: The percentage of time in Z1 and Z2.

    Returns:
        The detected training style name.
    """
    if polarized_score > HIGHLY_POLARIZED_THRESHOLD:
        return "Highly Polarized"
    if polarized_score < THRESHOLD_PYRAMIDAL_THRESHOLD:
        return "Threshold/Pyramidal"
    return "Base Building"
