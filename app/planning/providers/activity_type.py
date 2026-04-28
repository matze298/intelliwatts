"""Activity type distribution metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class ActivityTypeResult:
    """Result of the activity type calculation."""

    type_durations: dict[str, float]
    total_hours: float
    primary_sport: str


class ActivityTypeProvider(MetricProvider[ActivityTypeResult | None]):
    """Provides activity type distribution context."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "activity_type"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
    ) -> ActivityTypeResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The structured calculation result.
        """
        if "types" not in daily_df.columns or "activity_durations" not in daily_df.columns:
            return None

        # Reconstruct individual activities by exploding types and durations
        # Each row in daily_df has a list of types and a list of durations
        df = daily_df.select(["types", "activity_durations"]).explode(["types", "activity_durations"]).drop_nulls()

        if df.is_empty():
            return None

        # Group by type and sum durations
        summary = (
            df.group_by("types").agg(pl.col("activity_durations").sum()).sort("activity_durations", descending=True)
        )

        type_durations = {row["types"]: round(float(row["activity_durations"]), 1) for row in summary.to_dicts()}
        total_hours = round(sum(type_durations.values()), 1)
        primary_sport = summary["types"][0] if not summary.is_empty() else "N/A"

        return ActivityTypeResult(
            type_durations=type_durations,
            total_hours=total_hours,
            primary_sport=primary_sport,
        )

    @override
    async def provide_context(self, result: ActivityTypeResult | None) -> str:
        """Provides activity type context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the activity type context.
        """
        if not result:
            return ""

        dist = ", ".join([f"{k}: {v}h" for k, v in result.type_durations.items()])
        return f"Activity Type Distribution: {dist} (Primary: {result.primary_sport})"

    @override
    def get_dashboard_widget(
        self, result: ActivityTypeResult | None, display_days: int | None = None
    ) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if not result:
            return None

        return DashboardWidget(
            name="activity_type",
            title="Sport Distribution",
            custom_template="widgets/activity_type_chart.html",
            data={
                "labels": list(result.type_durations.keys()),
                "values": list(result.type_durations.values()),
                "primary_sport": result.primary_sport,
                "total_hours": result.total_hours,
            },
        )
