"""FTP Trajectory metric provider."""

from typing import TYPE_CHECKING, override

from app.intervals.analysis import compute_analysis
from app.intervals.parser.activity import parse_activities
from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    from app.intervals.analysis import AnalysisResult
    from app.intervals.client import IntervalsClient


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
    async def provide_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult | None = None) -> str:
        """Provides FTP trajectory context for the last 28 days.

        Args:
            client: The Intervals.icu client.
            days: Number of past days to analyze (overridden to 30 for trend).
            analysis: Optional pre-computed analysis result.

        Returns:
            str: The formatted FTP trajectory.
        """
        if analysis and analysis.ftp_trajectory:
            traj = analysis.ftp_trajectory
        else:
            # FTP trajectory needs at least 28 days of history
            raw_activities = client.activities(days=max(days, 30))
            activities = parse_activities(raw_activities)

            if not activities:
                return "No activities found to determine FTP trajectory."

            analysis = compute_analysis(activities)
            traj = analysis.ftp_trajectory

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
