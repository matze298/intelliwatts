"""Intensity distribution metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
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
        hr_totals = self._sum_zones_polars(daily_df, "hr_zone_times")
        power_totals = self._sum_zones_polars(daily_df, "power_zone_times")

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

        style = self._detect_style(polarized_score)

        return IntensityResult(
            hr_zones_pct=hr_zones_pct,
            power_zones_pct=power_zones_pct,
            hr_total_mins=round(hr_sum_secs / 60, 1),
            power_total_mins=round(power_sum_secs / 60, 1),
            polarized_score=polarized_score,
            style=style,
        )

    @staticmethod
    def _sum_zones_polars(daily_df: pl.DataFrame, col_name: str) -> list[int]:
        """Sum zone times across all days using Polars for better performance.

        Args:
            daily_df: The daily dataframe.
            col_name: The column name to sum.

        Returns:
            The list of summed zone times.
        """
        if col_name not in daily_df.columns:
            return []

        # Robust extraction and flattening using Polars
        try:
            # Keep track of which activity each zone belongs to for index-wise summing
            # We convert to a dedicated dataframe to maintain structure
            df_zones = daily_df.select(col_name).filter(pl.col(col_name).is_not_null())
            if df_zones.is_empty():
                return []

            # Explode once to handle the aggregation (one row per activity)
            df_zones = df_zones.explode(col_name)

            # Now we have one row per activity, where col_name is list[int] or list[dict]
            # Add a unique ID per activity
            df_zones = df_zones.with_row_index("activity_id").explode(col_name)

            # Now we have one row per zone per activity.
            # col_name is now scalar (int or dict)

            # Extract 'secs' if it's a dict
            if df_zones[col_name].dtype == pl.Struct:
                # Handle struct/dict from Power zones
                df_zones = df_zones.with_columns(val=pl.col(col_name).struct.field("secs").fill_null(0))
            else:
                df_zones = df_zones.with_columns(val=pl.col(col_name).fill_null(0).cast(pl.Int64))

            # Add zone index within each activity to sum corresponding zones
            df_zones = df_zones.with_columns(zone_idx=pl.int_range(0, pl.len()).over("activity_id"))

            # Sum by zone index
            res = df_zones.group_by("zone_idx").agg(pl.col("val").sum()).sort("zone_idx")
            return res["val"].to_list()
        except pl.exceptions.ColumnNotFoundError, pl.exceptions.ComputeError, pl.exceptions.SchemaError:
            return []

    @staticmethod
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
