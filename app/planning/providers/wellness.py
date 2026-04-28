"""Wellness metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient

RECENT_DAYS = 7


@dataclass(frozen=True)
class WellnessResult:
    """Result of the wellness calculation."""

    dates: list[str]
    hrv: list[float | None]
    hrv_7d: list[float | None]
    resting_hr: list[float | None]
    resting_hr_7d: list[float | None]
    avg_hrv: float
    avg_resting_hr: float
    hrv_trend: str  # "improving", "declining", "stable"
    recent_hrv_trend: list[float]


class WellnessProvider(MetricProvider[WellnessResult | None]):
    """Provides wellness context for the last days."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "wellness"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
    ) -> WellnessResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The structured calculation result.
        """
        if "hrv" not in daily_df.columns and "resting_hr" not in daily_df.columns:
            return None

        # Work with a subset for trends
        # We need enough data for the rolling average
        df = daily_df.select(["date", "hrv", "resting_hr"])

        # Calculate 7-day rolling averages
        # min_samples=1 ensures we get values even at the start of the series
        df = df.with_columns([
            pl.col("hrv").rolling_mean(window_size=7, min_samples=1).alias("hrv_7d"),
            pl.col("resting_hr").rolling_mean(window_size=7, min_samples=1).alias("resting_hr_7d"),
        ])

        # Overall averages for the entire period
        avg_hrv = cast("float", df["hrv"].mean()) if "hrv" in df.columns else 0.0
        avg_resting_hr = cast("float", df["resting_hr"].mean()) if "resting_hr" in df.columns else 0.0

        # Trend analysis based on last 7 days vs baseline
        if not df.is_empty() and len(df) >= RECENT_DAYS:
            recent_hrv_series = df["hrv"][-RECENT_DAYS:]
            recent_hrv = cast("float", recent_hrv_series.mean())
            if recent_hrv > (avg_hrv or 1) * 1.05:
                trend = "improving"
            elif recent_hrv < (avg_hrv or 1) * 0.95:
                trend = "declining"
            else:
                trend = "stable"
            recent_hrv_trend = recent_hrv_series.drop_nulls().to_list()
        else:
            trend = "stable"
            recent_hrv_trend = df["hrv"].drop_nulls().to_list() if "hrv" in df.columns else []

        return WellnessResult(
            dates=df["date"].dt.to_string("%Y-%m-%d").to_list(),
            hrv=df["hrv"].to_list(),
            hrv_7d=df["hrv_7d"].to_list(),
            resting_hr=df["resting_hr"].to_list(),
            resting_hr_7d=df["resting_hr_7d"].to_list(),
            avg_hrv=avg_hrv or 0.0,
            avg_resting_hr=avg_resting_hr or 0.0,
            hrv_trend=trend,
            recent_hrv_trend=recent_hrv_trend,
        )

    @override
    async def provide_context(self, result: WellnessResult | None) -> str:
        """Provides wellness context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the wellness context.
        """
        if result is None:
            return "No wellness data available."

        trend_str = ", ".join([f"{v:.0f}" for v in result.recent_hrv_trend])
        return (
            "Wellness Metrics:\n"
            f"- Average HRV: {result.avg_hrv:.1f}\n"
            f"- Average Resting HR: {result.avg_resting_hr:.1f} bpm\n"
            f"- HRV Trend Status: {result.hrv_trend.capitalize()}\n"
            f"- Recent HRV Trend (Last days): [{trend_str}]"
        )

    @override
    def get_dashboard_widget(
        self, result: WellnessResult | None, display_days: int | None = None
    ) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if result is None:
            return None

        # We return a custom template widget that will render the dual-axis chart
        return DashboardWidget(
            name="wellness",
            title="Wellness Trends",
            custom_template="widgets/wellness_chart.html",
            data={
                "dates": result.dates,
                "hrv": result.hrv,
                "hrv_7d": result.hrv_7d,
                "resting_hr": result.resting_hr,
                "resting_hr_7d": result.resting_hr_7d,
                "avg_hrv": result.avg_hrv,
                "avg_resting_hr": result.avg_resting_hr,
                "hrv_trend": result.hrv_trend,
            },
        )
