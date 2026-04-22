"""Wellness metric provider."""

from typing import TYPE_CHECKING, override

from app.intervals.analysis import compute_analysis
from app.intervals.parser.wellness import parse_wellness_list
from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    from app.intervals.analysis import AnalysisResult
    from app.intervals.client import IntervalsClient


class WellnessProvider(MetricProvider):
    """Provides wellness-related context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "wellness"

    @override
    async def provide_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult | None = None) -> str:
        """Provides wellness context for the last days.

        Returns:
            str: The formatted wellness summary.
        """
        if analysis and analysis.wellness_summary:
            summary = analysis.wellness_summary
            hrv_7d = summary.get("hrv_7d", 0.0)
            hrv_42d = summary.get("hrv_42d", 0.0)
            rhr_7d = summary.get("resting_hr_7d", 0.0)
            rhr_42d = summary.get("resting_hr_42d", 0.0)
        else:
            # Fetch a bit more than days to ensure we have enough data for 42d avg
            raw_wellness = client.wellness(days=max(days, 42))
            wellness_data = parse_wellness_list(raw_wellness)

            if not wellness_data:
                return "No wellness data available."

            # Fallback to computing once if not provided
            # Optimization: compute_analysis handles wellness trends
            analysis = compute_analysis([], wellness_data=wellness_data)
            if not analysis.wellness_summary:
                return "Wellness data parsing failed."

            summary = analysis.wellness_summary
            hrv_7d = summary.get("hrv_7d", 0.0)
            hrv_42d = summary.get("hrv_42d", 0.0)
            rhr_7d = summary.get("resting_hr_7d", 0.0)
            rhr_42d = summary.get("resting_hr_42d", 0.0)

        return (
            "Wellness Trends:\n"
            f"- HRV (7d avg): {hrv_7d:.1f}\n"
            f"- HRV (42d avg): {hrv_42d:.1f}\n"
            f"- Resting HR (7d avg): {rhr_7d:.1f}\n"
            f"- Resting HR (42d avg): {rhr_42d:.1f}"
        )
