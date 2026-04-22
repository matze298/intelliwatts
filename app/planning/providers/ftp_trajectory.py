"""FTP trajectory metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient

FTP_TRAJECTORY_LOOKBACK_DAYS = 28


@dataclass(frozen=True)
class FTPTrajectoryResult:
    """Result of the FTP trajectory calculation."""

    current_ftp: float | None
    ftp_4w_ago: float | None
    change_pct: float | None
    days_analyzed: int


class FTPTrajectoryProvider(MetricProvider[FTPTrajectoryResult | None]):
    """Provides FTP trajectory context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "ftp_trajectory"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
    ) -> FTPTrajectoryResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The structured calculation result.
        """
        # Calculate from daily_df
        if daily_df.is_empty() or "ftp" not in daily_df.columns:
            return None

        # Forward fill FTP to handle days without activities
        df_ftp = daily_df.select(["date", "ftp"]).with_columns(pl.col("ftp").forward_fill())

        if df_ftp["ftp"].null_count() == len(df_ftp):
            return None

        current_ftp = float(df_ftp["ftp"].tail(1).item())

        # Look back 4 weeks
        ftp_4w_ago = None
        if len(df_ftp) > FTP_TRAJECTORY_LOOKBACK_DAYS:
            val = df_ftp["ftp"].gather(len(df_ftp) - (FTP_TRAJECTORY_LOOKBACK_DAYS + 1)).item()
            ftp_4w_ago = float(val) if val is not None else None

        change_pct = None
        if current_ftp and ftp_4w_ago and ftp_4w_ago > 0:
            change_pct = ((current_ftp - ftp_4w_ago) / ftp_4w_ago) * 100

        return FTPTrajectoryResult(
            current_ftp=current_ftp,
            ftp_4w_ago=ftp_4w_ago,
            change_pct=change_pct,
            days_analyzed=FTP_TRAJECTORY_LOOKBACK_DAYS,
        )

    @override
    async def provide_context(self, result: FTPTrajectoryResult | None) -> str:
        """Provides FTP trajectory context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the FTP context.
        """
        if result is None or result.current_ftp is None:
            return "Current FTP data unavailable."

        return (
            f"FTP History (Last {result.days_analyzed} days):\n"
            f"- Current: {result.current_ftp:.0f}W\n"
            f"- Range: {result.ftp_4w_ago or '?'}W -> {result.current_ftp:.0f}W"
        )

    @override
    def get_dashboard_widget(self, result: FTPTrajectoryResult | None) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.

        Returns:
            The dashboard widget.
        """
        if result is None or result.current_ftp is None:
            return None

        trend_str = ""
        trend_pos = None
        if result.change_pct is not None:
            trend_str = f"{'+' if result.change_pct >= 0 else ''}{result.change_pct:.1f}% vs 4w"
            trend_pos = result.change_pct >= 0

        return DashboardWidget(
            name="ftp_trajectory",
            title="FTP Trajectory",
            value=f"{result.current_ftp:.0f} W",
            trend=trend_str,
            trend_positive=trend_pos,
        )
