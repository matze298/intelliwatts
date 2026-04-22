"""Resting HR trend provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class RestingHRResult:
    """Result of the resting HR calculation."""

    rhr_7d: float
    rhr_42d: float


class RestingHRTrendProvider(MetricProvider[RestingHRResult | None]):
    """Provides resting HR trend context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "resting_hr"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        wellness_summary: dict[str, Any] | None = None,
        ftp_trajectory: dict[str, Any] | None = None,
        power_curve: dict[str, Any] | None = None,
    ) -> RestingHRResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            wellness_summary: Legacy wellness summary from analysis.py.
            ftp_trajectory: Legacy FTP trajectory from analysis.py.
            power_curve: Legacy power curve summary from analysis.py.

        Returns:
            RestingHRResult | None: The structured calculation result.
        """
        if daily_df is None or daily_df.is_empty() or "resting_hr" not in daily_df.columns:
            return None

        # Simple calculation if not already provided in wellness_summary
        rhr_7d = daily_df["resting_hr"].tail(7).mean()
        rhr_42d = daily_df["resting_hr"].tail(42).mean()

        return RestingHRResult(
            rhr_7d=float(cast("float", rhr_7d)) if rhr_7d is not None else 0.0,
            rhr_42d=float(cast("float", rhr_42d)) if rhr_42d is not None else 0.0,
        )

    @override
    async def provide_context(self, result: RestingHRResult | None) -> str:
        """Provides resting HR context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the resting HR context.
        """
        if result is None:
            return "No resting HR data available."

        return f"Resting HR Trend:\n- 7d Average: {result.rhr_7d:.1f} bpm\n- 42d Average: {result.rhr_42d:.1f} bpm"

    @override
    def get_dashboard_widget(self, result: RestingHRResult | None) -> None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
        """
        return
