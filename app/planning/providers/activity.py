"""Activity metric provider."""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, override

from app.intervals.analysis import compute_load
from app.intervals.parser.activity import parse_activities
from app.planning.providers.base import MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient


class ActivityProvider(MetricProvider):
    """Provides activity-related context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "activity"

    @override
    async def provide_context(self, client: IntervalsClient, days: int) -> str:
        """Provides activity context for the last days.

        Returns:
            str: The formatted activity summary.
        """
        raw_activities = client.activities(days=days)
        activities = parse_activities(raw_activities)

        if not activities:
            return "No recent activities found."

        # Logic from app/planning/summary.py
        today = datetime.now(tz=UTC).date()
        seven_days_ago = str(today - timedelta(days=7))
        last_7d = [a for a in activities if a.date >= seven_days_ago]

        tss_7d = sum(a.training_stress for a in last_7d)
        hours_7d = round(sum(a.duration_h for a in last_7d), 1)

        load = compute_load(activities)

        return (
            "Recent Training (Last 7 Days):\n"
            f"- Total TSS: {tss_7d}\n"
            f"- Total Hours: {hours_7d}\n\n"
            "Training Load:\n"
            f"- Chronic (CTL): {load.chronic:.1f}\n"
            f"- Acute (ATL): {load.acute:.1f}\n"
            f"- Balance (TSB): {load.training_stress_balance:.1f}"
        )
