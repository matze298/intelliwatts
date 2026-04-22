"""FTP Trajectory metric provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, override

from app.planning.providers.base import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.analysis import AnalysisResult


class FTPTrajectoryProvider(MetricProvider):
    """Provides FTP trajectory context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "ftp_trajectory"

    @override
    def calculate(self, daily_df: pl.DataFrame, **kwargs: object) -> object:
        """Perform calculations on raw data and return a structured result.

        Returns:
            object: The structured calculation result.
        """
        analysis = cast("AnalysisResult", kwargs.get("analysis"))
        return analysis.ftp_trajectory

    @override
    async def provide_context(self, result: object) -> str:
        """Provides FTP trajectory context for the last 28 days.

        Returns:
            str: The formatted FTP trajectory.
        """
        traj = cast("dict[str, Any]", result)

        if not traj or traj.get("current_ftp") is None:
            return "Current FTP data unavailable."

        current = traj["current_ftp"]
        prev = traj.get("ftp_4w_ago")
        change = traj.get("change_pct")

        if prev is None:
            return f"Current FTP: {current}W (Historical trend unavailable)"

        trend_sign = "+" if (change or 0) >= 0 else ""
        return (
            "FTP Trajectory (Last 4 Weeks):\n"
            f"- Current FTP: {current}W\n"
            f"- 4 Weeks Ago: {prev}W\n"
            f"- Progress: {trend_sign}{change}%"
        )

    @override
    def get_dashboard_widget(self, result: object) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Returns:
            DashboardWidget | None: The dashboard widget or None.
        """
        return None
