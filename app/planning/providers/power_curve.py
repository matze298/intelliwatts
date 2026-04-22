"""Power curve metric provider."""

from typing import TYPE_CHECKING, override

from app.intervals.analysis import compute_analysis
from app.intervals.parser.power_curve import parse_power_curves
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
    async def provide_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult | None = None) -> str:
        """Provides power curve context.

        Returns:
            str: The formatted power curve summary.
        """
        if analysis and analysis.power_curve:
            summary = analysis.power_curve
            peak_5s = summary.get("peak_5s")
            peak_1m = summary.get("peak_1m")
            peak_5m = summary.get("peak_5m")
            peak_20m = summary.get("peak_20m")
        else:
            raw_power_curves = client.power_curves(curves="90d")
            power_curves = parse_power_curves(raw_power_curves)

            if not power_curves:
                return "No power curve data available."

            # Optimization: compute_analysis handles power curve summary
            analysis = compute_analysis([], power_curve=power_curves)
            if not analysis.power_curve:
                return "Power curve parsing failed."

            summary = analysis.power_curve
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
