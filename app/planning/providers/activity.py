"""Activity metric provider."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast, override

from app.intervals.analysis import TrainingLoad
from app.intervals.parser.activity import parse_activities
from app.planning.providers.base import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.analysis import AnalysisResult
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
    def calculate(self, daily_df: pl.DataFrame, **kwargs: object) -> object:
        """Perform calculations on raw data and return a structured result.

        Returns:
            object: The structured calculation result.
        """
        analysis = cast("AnalysisResult", kwargs.get("analysis"))
        client = cast("IntervalsClient", kwargs.get("client"))

        # 1. Pull pre-computed load from shared analysis
        last_day = analysis.daily_series[-1] if analysis.daily_series else {"ctl": 0.0, "atl": 0.0}
        load = TrainingLoad(chronic=last_day.get("ctl", 0.0), acute=last_day.get("atl", 0.0))

        # 2. Pull specific 7d metrics (tss, hours)
        # We still need to re-parse or filter activities for the specific "Last 7 Days" summary part.
        # Since we use cached session, this is efficient.
        # TODO(mr): Move this fetching logic out of calculate in Phase 3 #noqa: TD003
        raw_activities = client.activities(days=7)
        activities = parse_activities(raw_activities)

        if not activities:
            return {"load": load, "tss_7d": 0.0, "hours_7d": 0.0, "has_activities": False}

        tss_7d = sum(a.training_stress for a in activities)
        hours_7d = round(sum(a.duration_h for a in activities), 1)

        return {
            "load": load,
            "tss_7d": tss_7d,
            "hours_7d": hours_7d,
            "has_activities": True,
        }

    @override
    async def provide_context(self, result: object) -> str:
        """Provides activity context for the last days.

        Returns:
            str: The formatted activity summary.
        """
        res = cast("dict[str, Any]", result)
        if not res.get("has_activities") and res.get("load") is None:
            return "No recent activities found."

        load = res["load"]
        tss_7d = res["tss_7d"]
        hours_7d = res["hours_7d"]

        return (
            "Recent Training (Last 7 Days):\n"
            f"- Total TSS: {tss_7d:.1f}\n"
            f"- Total Hours: {hours_7d}\n\n"
            "Training Load:\n"
            f"- Chronic (CTL): {load.chronic:.1f}\n"
            f"- Acute (ATL): {load.acute:.1f}\n"
            f"- Balance (TSB): {load.training_stress_balance:.1f}"
        )

    @override
    def get_dashboard_widget(self, result: object) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Returns:
            DashboardWidget | None: The dashboard widget or None.
        """
        return None
