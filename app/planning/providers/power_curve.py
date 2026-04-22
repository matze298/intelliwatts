"""Power curve metric provider."""

from typing import TYPE_CHECKING, override

from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    from app.intervals.analysis import AnalysisResult
    from app.intervals.client import IntervalsClient


class PowerCurveProvider(MetricProvider):
    """Provides power curve context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "power_curve"

    @override
    async def provide_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult) -> str:
        """Provides power curve context.

        Returns:
            str: The formatted power curve summary.
        """
        summary = analysis.power_curve

        if not summary:
            return "No power curve data available."

        peak_5s = summary.get("peak_5s")
        peak_1m = summary.get("peak_1m")
        peak_5m = summary.get("peak_5m")
        peak_20m = summary.get("peak_20m")

        return (
            "Power Curve (Last 90 Days):\n"
            f"- 5s Peak: {peak_5s}W\n"
            f"- 1m Peak: {peak_1m}W\n"
            f"- 5m Peak: {peak_5m}W\n"
            f"- 20m Peak: {peak_20m}W"
        )
