"""Resting HR trend metric provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.base import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl


class RestingHRTrendProvider(MetricProvider):
    """Provides resting heart rate trend context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "resting_hr_trend"

    @override
    def calculate(self, daily_df: pl.DataFrame, **kwargs: object) -> object:
        """Perform calculations on raw data and return a structured result.

        Returns:
            object: The structured calculation result.
        """
        if daily_df.is_empty() or "resting_hr" not in daily_df.columns:
            return []

        # Extract last 7 days of resting HR
        return daily_df["resting_hr"].drop_nulls().tail(7).to_list()

    @override
    async def provide_context(self, result: object) -> str:
        """Provides resting HR trend context for the last 7 days.

        Returns:
            str: The formatted resting HR trend.
        """
        rhrs = cast("list[Any]", result)

        if not rhrs:
            return "No resting HR data available."

        trend_str = " -> ".join(str(r) for r in rhrs)
        return f"Resting HR Trend (Last 7 days): {trend_str}"

    @override
    def get_dashboard_widget(self, result: object) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Returns:
            DashboardWidget | None: The dashboard widget or None.
        """
        return None
