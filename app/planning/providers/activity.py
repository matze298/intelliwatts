"""Activity metric provider."""

import contextlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.intervals.models import TrainingLoad
from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class ActivityResult:
    """Result of the activity calculation."""

    load: TrainingLoad
    tss_7d: float
    hours_7d: float
    distance_7d: float
    has_activities: bool


class ActivityProvider(MetricProvider[ActivityResult]):
    """Provides activity context for the last days."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "activity"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        display_days: int | None = None,
    ) -> ActivityResult:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            display_days: Optional number of days to display.

        Returns:
            The structured calculation result.
        """
        # Filter to last 7 days for summary metrics
        today = daily_df["date"].max()
        if today is None:
            return ActivityResult(
                load=TrainingLoad(0, 0),
                tss_7d=0,
                hours_7d=0,
                distance_7d=0,
                has_activities=False,
            )

        seven_days_ago = today - pl.duration(days=7)
        recent_df = daily_df.filter(pl.col("date") > seven_days_ago)

        tss_7d = round(float(recent_df["training_stress"].sum()), 1)
        hours_7d = round(float(recent_df["duration_h"].sum()), 1)
        distance_7d = round(float(recent_df["distance_km"].sum()), 1)

        # Get latest load (from PMC provider if available)
        load = TrainingLoad(0, 0)
        if provider_results and "pmc" in provider_results:
            pmc_res = provider_results["pmc"]
            with contextlib.suppress(AttributeError, IndexError):
                load = TrainingLoad(chronic=pmc_res.ctl[-1], acute=pmc_res.atl[-1])

        return ActivityResult(
            load=load,
            tss_7d=tss_7d,
            hours_7d=hours_7d,
            distance_7d=distance_7d,
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
        distance_7d = result.distance_7d

        return (
            "Recent Training (Last 7 Days):\n"
            f"- Total TSS: {tss_7d:.1f}\n"
            f"- Total Hours: {hours_7d}h\n"
            f"- Total Distance: {distance_7d}km\n\n"
            "Training Load:\n"
            f"- Chronic (CTL): {load.chronic:.1f}\n"
            f"- Acute (ATL): {load.acute:.1f}\n"
            f"- Balance (TSB): {load.training_stress_balance:.1f}"
        )

    @override
    def get_dashboard_widget(self, result: ActivityResult, display_days: int | None = None) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if not result.has_activities:
            return None

        return DashboardWidget(
            name="activity",
            title="Recent Training",
            value=f"{result.tss_7d:.0f} TSS",
            trend=f"{result.hours_7d:.1f} hours",
            trend_positive=True,
        )
