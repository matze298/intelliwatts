"""Power curve metric provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.base import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.analysis import AnalysisResult


class PowerCurveProvider(MetricProvider):
    """Provides power curve context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "power_curve"

    @override
    def calculate(self, daily_df: pl.DataFrame, **kwargs: object) -> object:
        """Perform calculations on raw data and return a structured result.

        Returns:
            object: The structured calculation result.
        """
        analysis = cast("AnalysisResult", kwargs.get("analysis"))
        return analysis.power_curve

    @override
    async def provide_context(self, result: object) -> str:
        """Provides power curve context.

        Returns:
            str: The formatted power curve summary.
        """
        summary = cast("dict[str, Any]", result)

        if not summary:
            return "No power curve data available."

        peak_5s = summary.get("peak_5s")
        peak_1m = summary.get("peak_1m")
        peak_5m = summary.get("peak_5m")
        peak_20m = summary.get("peak_20m")

        return (
            "Power Curve (Last 90 Days):\n"
            f"- 5s Peak: {peak_5s}W\n"
            f"- 1m Peak: {peak_1m}W\n"
            f"- 5m Peak: {peak_5m}W\n"
            f"- 20m Peak: {peak_20m}W"
        )

    @override
    def get_dashboard_widget(self, result: object) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Returns:
            DashboardWidget | None: The dashboard widget or None.
        """
        return None
