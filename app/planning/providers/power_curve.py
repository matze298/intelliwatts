"""Power curve metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class PowerCurveResult:
    """Result of the power curve calculation."""

    peak_1s: int | None
    peak_15s: int | None
    peak_1m: int | None
    peak_5m: int | None
    peak_20m: int | None
    peak_60m: int | None


class PowerCurveProvider(MetricProvider[PowerCurveResult | None]):
    """Provides power curve context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "power_curve"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        wellness_summary: dict[str, Any] | None = None,
        ftp_trajectory: dict[str, Any] | None = None,
        power_curve: dict[str, Any] | None = None,
    ) -> PowerCurveResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            wellness_summary: Legacy wellness summary from analysis.py.
            ftp_trajectory: Legacy FTP trajectory from analysis.py.
            power_curve: Legacy power curve summary from analysis.py.

        Returns:
            The structured calculation result.
        """
        if not power_curve:
            return None

        return PowerCurveResult(
            peak_1s=power_curve.get("peak_1s"),
            peak_15s=power_curve.get("peak_15s"),
            peak_1m=power_curve.get("peak_1m"),
            peak_5m=power_curve.get("peak_5m"),
            peak_20m=power_curve.get("peak_20m"),
            peak_60m=power_curve.get("peak_60m"),
        )

    @override
    async def provide_context(self, result: PowerCurveResult | None) -> str:
        """Provides power curve context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the power curve context.
        """
        if result is None:
            return "No power curve data available."

        return (
            "Season Peak Power:\n"
            f"- 1s: {result.peak_1s or '-'}W\n"
            f"- 15s: {result.peak_15s or '-'}W\n"
            f"- 1m: {result.peak_1m or '-'}W\n"
            f"- 5m: {result.peak_5m or '-'}W\n"
            f"- 20m: {result.peak_20m or '-'}W\n"
            f"- 60m: {result.peak_60m or '-'}W"
        )

    @override
    def get_dashboard_widget(self, result: PowerCurveResult | None) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.

        Returns:
            The dashboard widget.
        """
        if result is None or result.peak_20m is None:
            return None

        return DashboardWidget(
            name="power_curve",
            title="Power Peaks",
            value=f"{result.peak_20m} W",
            trend="20m Peak",
            trend_positive=True,
        )
