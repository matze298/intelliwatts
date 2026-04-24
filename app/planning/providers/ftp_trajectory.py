"""FTP trajectory metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class FTPTrajectoryResult:
    """Result of the FTP trajectory calculation."""

    dates: list[str]
    ftp_values: list[float]


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
        # FTP trajectory depends on the 'ftp' column being present in daily_df
        if "ftp" not in daily_df.columns:
            return None

        # Filter to dates where FTP is not null
        ftp_df = daily_df.filter(daily_df["ftp"].is_not_null())
        if ftp_df.is_empty():
            return None

        return FTPTrajectoryResult(
            dates=ftp_df["date"].dt.strftime("%Y-%m-%d").to_list(),
            ftp_values=ftp_df["ftp"].to_list(),
        )

    @override
    async def provide_context(self, result: FTPTrajectoryResult | None) -> str:
        """Provides FTP trajectory context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the FTP trajectory context.
        """
        if result is None or not result.ftp_values:
            return "No FTP trajectory data available."

        initial_ftp = result.ftp_values[0]
        current_ftp = result.ftp_values[-1]
        change = current_ftp - initial_ftp
        change_pct = (change / initial_ftp) * 100 if initial_ftp > 0 else 0

        return (
            f"FTP Trajectory (Last {len(result.dates)} days):\n"
            f"- Starting FTP: {initial_ftp:.1f}W\n"
            f"- Current FTP: {current_ftp:.1f}W\n"
            f"- Total Change: {change:+.1f}W ({change_pct:+.1f}%)"
        )

    @override
    def get_dashboard_widget(
        self, result: FTPTrajectoryResult | None, display_days: int | None = None
    ) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if result is None or not result.ftp_values:
            return None

        current_ftp = result.ftp_values[-1]
        initial_ftp = result.ftp_values[0]
        change = current_ftp - initial_ftp

        return DashboardWidget(
            name="ftp_trajectory",
            title="FTP Trend",
            value=f"{current_ftp:.0f} W",
            trend=f"{change:+.1f} W",
            trend_positive=change >= 0,
            data={"dates": result.dates, "values": result.ftp_values},
        )
