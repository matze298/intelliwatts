"""Wellness metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient

RECENT_DAYS = 7


@dataclass(frozen=True)
class WellnessResult:
    """Result of the wellness calculation."""

    avg_hrv: float
    avg_resting_hr: float
    hrv_trend: str  # "improving", "declining", "stable"


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
        if "hrv" not in daily_df.columns:
            return None

        # Filter out nulls
        df = daily_df.filter(daily_df["hrv"].is_not_null())
        if df.is_empty():
            return None

        avg_hrv = cast("float", df["hrv"].mean())
        avg_resting_hr = cast("float", df["resting_hr"].mean()) if "resting_hr" in df.columns else 0.0

        # Simple trend analysis
        if len(df) >= RECENT_DAYS:
            recent_hrv = cast("float", df["hrv"][-RECENT_DAYS:].mean())
            if recent_hrv > avg_hrv * 1.05:
                trend = "improving"
            elif recent_hrv < avg_hrv * 0.95:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return WellnessResult(
            avg_hrv=avg_hrv,
            avg_resting_hr=avg_resting_hr,
            hrv_trend=trend,
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

        return (
            "Wellness Metrics:\n"
            f"- Average HRV: {result.avg_hrv:.1f}\n"
            f"- Average Resting HR: {result.avg_resting_hr:.1f} bpm\n"
            f"- HRV Trend: {result.hrv_trend.capitalize()}"
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

        return DashboardWidget(
            name="wellness",
            title="Readiness",
            value=f"{result.avg_hrv:.0f} ms",
            trend=result.hrv_trend.capitalize(),
            trend_positive=result.hrv_trend == "improving",
        )
