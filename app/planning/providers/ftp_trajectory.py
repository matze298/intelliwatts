"""FTP trajectory metric provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class FTPTrajectoryResult:
    """Result of the FTP trajectory calculation."""

    current_ftp: float
    lowest_ftp: float
    highest_ftp: float
    days_analyzed: int


class FTPTrajectoryProvider(MetricProvider[FTPTrajectoryResult | None]):
    """Provides FTP trajectory context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "ftp_trajectory"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        wellness_summary: dict[str, Any] | None = None,
        ftp_trajectory: dict[str, Any] | None = None,
        power_curve: dict[str, Any] | None = None,
    ) -> FTPTrajectoryResult | None:
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
        if not ftp_trajectory:
            return None

        return FTPTrajectoryResult(
            current_ftp=ftp_trajectory.get("current_ftp", 0.0),
            lowest_ftp=ftp_trajectory.get("lowest_ftp", 0.0),
            highest_ftp=ftp_trajectory.get("highest_ftp", 0.0),
            days_analyzed=ftp_trajectory.get("days_analyzed", 0),
        )

    @override
    async def provide_context(self, result: FTPTrajectoryResult | None) -> str:
        """Provides FTP trajectory context.

        Args:
            result: The result from the calculate method.

        Returns:
            str: A formatted string containing the FTP context.
        """
        if result is None:
            return "Current FTP data unavailable."

        return (
            f"FTP History (Last {result.days_analyzed} days):\n"
            f"- Current: {result.current_ftp}W\n"
            f"- Range: {result.lowest_ftp}W - {result.highest_ftp}W"
        )

    @override
    def get_dashboard_widget(self, result: FTPTrajectoryResult | None) -> None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
        """
        return
