"""Power curve metric provider."""

from typing import TYPE_CHECKING, override

from app.intervals.parser.power_curve import parse_power_curves
from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
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
    async def provide_context(self, client: IntervalsClient, days: int) -> str:
        """Provides power curve context.

        Returns:
            str: The formatted power curve summary.
        """
        raw_power_curves = client.power_curves(curves="90d")
        power_curves = parse_power_curves(raw_power_curves)

        if not power_curves:
            return "No power curve data available."

        curve = power_curves[0]

        peak_5s = curve.get_watts(5)
        peak_1m = curve.get_watts(60)
        peak_5m = curve.get_watts(300)
        peak_20m = curve.get_watts(1200)

        return (
            "Power Curve (Last 90 Days):\n"
            f"- 5s Peak: {peak_5s}W\n"
            f"- 1m Peak: {peak_1m}W\n"
            f"- 5m Peak: {peak_5m}W\n"
            f"- 20m Peak: {peak_20m}W"
        )
