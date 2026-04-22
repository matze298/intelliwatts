"""Activity metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from app.intervals.models import TrainingLoad
from app.intervals.parser.activity import parse_activities
from app.planning.providers.interfaces import MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class ActivityResult:
    """Result of the activity calculation."""

    load: TrainingLoad
    tss_7d: float
    hours_7d: float
    has_activities: bool


class ActivityProvider(MetricProvider[ActivityResult]):
    """Provides activity-related context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            str: The provider name.
        """
        return "activity"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
    ) -> ActivityResult:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The structured calculation result.
        """
        # 1. Pull pre-computed load from PMC provider results if available
        chronic = 0.0
        acute = 0.0

        if provider_results and "pmc" in provider_results:
            pmc_res = provider_results["pmc"]
            if isinstance(pmc_res, dict):
                ctl = pmc_res.get("ctl", [])
                atl = pmc_res.get("atl", [])
                if ctl and atl:
                    chronic = ctl[-1]
                    acute = atl[-1]

        load = TrainingLoad(chronic=chronic, acute=acute)

        # 2. Pull specific 7d metrics (tss, hours)
        if client is None:
            return ActivityResult(load=load, tss_7d=0.0, hours_7d=0.0, has_activities=False)

        # TODO(mr): Move this fetching logic out of calculate in Phase 3 #noqa: TD003
        raw_activities = client.activities(days=7)
        activities = parse_activities(raw_activities)

        if not activities:
            return ActivityResult(load=load, tss_7d=0.0, hours_7d=0.0, has_activities=False)

        tss_7d = sum(a.training_stress for a in activities)
        hours_7d = round(sum(a.duration_h for a in activities), 1)

        return ActivityResult(
            load=load,
            tss_7d=tss_7d,
            hours_7d=hours_7d,
            has_activities=True,
        )

    @override
    async def provide_context(self, result: ActivityResult) -> str:
        """Provides activity context for the last days.

        Args:
            result: The result from the calculate method.

        Returns:
            str: The formatted activity summary.
        """
        load = result.load
        tss_7d = result.tss_7d
        hours_7d = result.hours_7d

        if not result.has_activities and load.chronic == 0 and load.acute == 0:
            return "No recent activities found."

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
    def get_dashboard_widget(self, result: ActivityResult) -> None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
        """
        return
