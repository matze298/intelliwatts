"""Resting heart rate trend metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.interfaces import MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class RestingHRResult:
    """Result of the resting heart rate trend calculation."""

    current_hr: float
    avg_hr: float
    is_increasing: bool
    recent_trend: list[float]


class RestingHRTrendProvider(MetricProvider[RestingHRResult | None]):
    """Provides resting heart rate trend context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "resting_hr"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
    ) -> RestingHRResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The structured calculation result.
        """
        if "resting_hr" not in daily_df.columns:
            return None

        # Filter out nulls
        hr_df = daily_df.filter(daily_df["resting_hr"].is_not_null())
        if hr_df.is_empty():
            return None

        current_hr = cast("float", hr_df["resting_hr"][-1])
        avg_hr = cast("float", hr_df["resting_hr"].mean())

        # Get last 7 days for trend context
        recent_trend = hr_df["resting_hr"][-7:].to_list()

        return RestingHRResult(
            current_hr=current_hr,
            avg_hr=avg_hr,
            is_increasing=current_hr > avg_hr,
            recent_trend=recent_trend,
        )

    @override
    async def provide_context(self, result: RestingHRResult | None) -> str:
        """Provides resting heart rate context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the resting heart rate context.
        """
        if result is None:
            return "No resting heart rate data available."

        status = "increased" if result.is_increasing else "decreased/stable"
        trend_str = ", ".join([f"{v:.0f}" for v in result.recent_trend])
        return (
            "Physiological Trends:\n"
            f"- Current Resting HR: {result.current_hr:.0f} bpm\n"
            f"- Baseline (Avg): {result.avg_hr:.1f} bpm\n"
            f"- Status: Resting HR is {status} compared to baseline.\n"
            f"- Recent Trend (Last 7 days): [{trend_str}]"
        )

    @override
    def get_dashboard_widget(self, result: RestingHRResult | None, display_days: int | None = None) -> None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.
        """
        return
