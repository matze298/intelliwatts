"""Wellness metric provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.base import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.analysis import AnalysisResult


class WellnessProvider(MetricProvider):
    """Provides wellness-related context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "wellness"

    @override
    def calculate(self, daily_df: pl.DataFrame, **kwargs: object) -> object:
        """Perform calculations on raw data and return a structured result.

        Returns:
            object: The structured calculation result.
        """
        analysis = cast("AnalysisResult", kwargs.get("analysis"))
        return analysis.wellness_summary

    @override
    async def provide_context(self, result: object) -> str:
        """Provides wellness context for the last days.

        Returns:
            str: The formatted wellness summary.
        """
        summary = cast("dict[str, Any]", result)

        if not summary:
            return "No wellness data available."

        hrv_7d = summary.get("hrv_7d", 0.0)
        hrv_42d = summary.get("hrv_42d", 0.0)
        rhr_7d = summary.get("resting_hr_7d", 0.0)
        rhr_42d = summary.get("resting_hr_42d", 0.0)

        return (
            "Wellness Trends:\n"
            f"- HRV (7d avg): {hrv_7d:.1f}\n"
            f"- HRV (42d avg): {hrv_42d:.1f}\n"
            f"- Resting HR (7d avg): {rhr_7d:.1f}\n"
            f"- Resting HR (42d avg): {rhr_42d:.1f}"
        )

    @override
    def get_dashboard_widget(self, result: object) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Returns:
            DashboardWidget | None: The dashboard widget or None.
        """
        return None
