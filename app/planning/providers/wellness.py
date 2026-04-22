"""Wellness metric provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class WellnessResult:
    """Result of the wellness calculation."""

    hrv_7d: float | None
    hrv_42d: float | None
    rhr_7d: float | None
    rhr_42d: float | None


class WellnessProvider(MetricProvider[WellnessResult | None]):
    """Provides wellness-related context."""

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
            The structured calculation result.
        """
        # If legacy summary is provided, use it
        if wellness_summary:
            return WellnessResult(
                hrv_7d=wellness_summary.get("hrv_7d"),
                hrv_42d=wellness_summary.get("hrv_42d"),
                rhr_7d=wellness_summary.get("resting_hr_7d"),
                rhr_42d=wellness_summary.get("resting_hr_42d"),
            )

        # Otherwise calculate from daily_df if columns exist
        if "hrv" not in daily_df.columns or "resting_hr" not in daily_df.columns:
            return None

        hrv_7d = daily_df["hrv"].tail(7).mean()
        hrv_42d = daily_df["hrv"].tail(42).mean()
        rhr_7d = daily_df["resting_hr"].tail(7).mean()
        rhr_42d = daily_df["resting_hr"].tail(42).mean()

        return WellnessResult(
            hrv_7d=float(cast("float", hrv_7d)) if hrv_7d is not None else None,
            hrv_42d=float(cast("float", hrv_42d)) if hrv_42d is not None else None,
            rhr_7d=float(cast("float", rhr_7d)) if rhr_7d is not None else None,
            rhr_42d=float(cast("float", rhr_42d)) if rhr_42d is not None else None,
        )

    @override
    async def provide_context(self, result: WellnessResult | None) -> str:
        """Provides wellness context based on the analysis.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the wellness context.
        """
        if result is None:
            return "No wellness data available."

        hrv_7d = result.hrv_7d or 0.0
        hrv_42d = result.hrv_42d or 0.0
        rhr_7d = result.rhr_7d or 0.0
        rhr_42d = result.rhr_42d or 0.0

        return (
            "Wellness Trends:\n"
            f"- HRV (7d avg): {hrv_7d:.1f}\n"
            f"- HRV (42d avg): {hrv_42d:.1f}\n"
            f"- Resting HR (7d avg): {rhr_7d:.1f}\n"
            f"- Resting HR (42d avg): {rhr_42d:.1f}"
        )

    @override
    def get_dashboard_widget(self, result: WellnessResult | None) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.

        Returns:
            The dashboard widget or None.
        """
        if result is None or result.hrv_7d is None:
            return None

        hrv_trend = ""
        trend_pos = None
        if result.hrv_7d and result.hrv_42d:
            diff = result.hrv_7d - result.hrv_42d
            hrv_trend = f"{'+' if diff >= 0 else ''}{diff:.1f} vs 42d"
            trend_pos = diff >= 0

        return DashboardWidget(
            name="wellness",
            title="Readiness (HRV)",
            value=f"{result.hrv_7d:.0f} ms",
            trend=hrv_trend,
            trend_positive=trend_pos,
        )
