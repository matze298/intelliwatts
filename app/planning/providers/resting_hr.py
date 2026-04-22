"""Resting HR trend metric provider."""

from typing import TYPE_CHECKING, override

from app.intervals.parser.wellness import parse_wellness_list
from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    from app.intervals.analysis import AnalysisResult
    from app.intervals.client import IntervalsClient


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
    async def provide_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult | None = None) -> str:
        """Provides resting HR trend context for the last 7 days.

        Returns:
            str: The formatted resting HR trend.
        """
        if analysis and analysis.daily_series:
            # Use pre-computed daily series
            rhrs = [d["resting_hr"] for d in analysis.daily_series if d.get("resting_hr") is not None]
        else:
            raw_wellness = client.wellness(days=days)
            wellness_data = parse_wellness_list(raw_wellness)

            if not wellness_data:
                return "No wellness data available for RHR trend."

            # Sort by date ascending to show trend
            wellness_data.sort(key=lambda w: w.date)
            rhrs = [w.resting_hr for w in wellness_data if w.resting_hr is not None]

        if not rhrs:
            return "No resting HR data available."

        trend_str = " -> ".join(str(r) for r in rhrs[-7:])
        return f"Resting HR Trend (Last 7 days): {trend_str}"
