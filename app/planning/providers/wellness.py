"""Wellness metric provider."""

from typing import TYPE_CHECKING, override

from app.intervals.parser.wellness import parse_wellness_list
from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
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
    async def provide_context(self, client: IntervalsClient, days: int) -> str:
        """Provides wellness context for the last days.

        Returns:
            str: The formatted wellness summary.
        """
        # Fetch a bit more than days to ensure we have enough data for 42d avg
        raw_wellness = client.wellness(days=max(days, 42))
        wellness_data = parse_wellness_list(raw_wellness)

        if not wellness_data:
            return "No wellness data available."

        # Sort by date descending
        wellness_data.sort(key=lambda w: w.date, reverse=True)

        # Get last 7 days and last 42 days
        last_7d_hrv = [w.hrv for w in wellness_data[:7] if w.hrv is not None]
        last_42d_hrv = [w.hrv for w in wellness_data[:42] if w.hrv is not None]
        last_7d_rhr = [w.resting_hr for w in wellness_data[:7] if w.resting_hr is not None]
        last_42d_rhr = [w.resting_hr for w in wellness_data[:42] if w.resting_hr is not None]

        hrv_7d = sum(last_7d_hrv) / len(last_7d_hrv) if last_7d_hrv else 0.0
        hrv_42d = sum(last_42d_hrv) / len(last_42d_hrv) if last_42d_hrv else 0.0
        rhr_7d = sum(last_7d_rhr) / len(last_7d_rhr) if last_7d_rhr else 0.0
        rhr_42d = sum(last_42d_rhr) / len(last_42d_rhr) if last_42d_rhr else 0.0

        return (
            "Wellness Trends:\n"
            f"- HRV (7d avg): {hrv_7d:.1f}\n"
            f"- HRV (42d avg): {hrv_42d:.1f}\n"
            f"- Resting HR (7d avg): {rhr_7d:.1f}\n"
            f"- Resting HR (42d avg): {rhr_42d:.1f}"
        )
