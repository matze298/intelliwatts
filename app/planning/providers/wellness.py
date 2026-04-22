"""Wellness metric provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class WellnessResult:
    """Result of the wellness calculation."""

    hrv_7d: float
    hrv_42d: float
    rhr_7d: float
    rhr_42d: float


class WellnessProvider(MetricProvider[WellnessResult | None]):
    """Provides wellness-related context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "wellness"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        wellness_summary: dict[str, Any] | None = None,
        ftp_trajectory: dict[str, Any] | None = None,
        power_curve: dict[str, Any] | None = None,
    ) -> WellnessResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            wellness_summary: Legacy wellness summary from analysis.py.
            ftp_trajectory: Legacy FTP trajectory from analysis.py.
            power_curve: Legacy power curve summary from analysis.py.

        Returns:
            WellnessResult | None: The structured calculation result.
        """
        if not wellness_summary:
            return None

        return WellnessResult(
            hrv_7d=wellness_summary.get("hrv_7d", 0.0),
            hrv_42d=wellness_summary.get("hrv_42d", 0.0),
            rhr_7d=wellness_summary.get("resting_hr_7d", 0.0),
            rhr_42d=wellness_summary.get("resting_hr_42d", 0.0),
        )

    @override
    async def provide_context(self, result: WellnessResult | None) -> str:
        """Provides wellness context based on the analysis.

        Args:
            result: The result from the calculate method.

        Returns:
            str: A formatted string containing the wellness context.
        """
        if result is None:
            return "No wellness data available."

        return (
            "Wellness Trends:\n"
            f"- HRV (7d avg): {result.hrv_7d:.1f}\n"
            f"- HRV (42d avg): {result.hrv_42d:.1f}\n"
            f"- Resting HR (7d avg): {result.rhr_7d:.1f}\n"
            f"- Resting HR (42d avg): {result.rhr_42d:.1f}"
        )

    @override
    def get_dashboard_widget(self, result: WellnessResult | None) -> None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
        """
        return
