"""Wellness metric provider."""

from typing import TYPE_CHECKING, override

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
    async def provide_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult) -> str:
        """Provides wellness context for the last days.

        Returns:
            str: The formatted wellness summary.
        """
        summary = analysis.wellness_summary

        if not summary:
            return "No wellness data available."

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
