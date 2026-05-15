"""Activity history metric provider."""

from dataclasses import dataclass
from numbers import Real
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class ActivityHistoryEntry:
    """Structured recent activity entry for dashboard drill-downs."""

    date: str
    activity_type: str
    duration_h: float
    training_stress: float
    distance_km: float | None
    avg_power: float | None
    avg_hr: float | None
    max_hr: float | None
    elevation_gain: float | None
    ftp: float | None


@dataclass(frozen=True)
class ActivityHistoryResult:
    """Result of the activity history calculation."""

    activities: list[ActivityHistoryEntry]
    has_data: bool


class ActivityHistoryProvider(MetricProvider[ActivityHistoryResult | None]):
    """Provides recent activity history with drill-down details."""

    @override
    def get_name(self) -> str:
        """Returns the provider name."""
        return "activity_history"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        display_days: int | None = None,
    ) -> ActivityHistoryResult | None:
        """Reconstruct recent individual activities from the daily aggregate.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            display_days: Optional number of days to display.

        Returns:
            Structured recent activity history, or None if the required columns are unavailable.
        """
        required_columns = {
            "date",
            "types",
            "activity_durations",
            "activity_tss",
            "activity_distances",
            "activity_avg_power",
            "activity_avg_hr",
            "activity_max_hr",
            "activity_elevation_gain",
            "activity_ftp",
        }
        if not required_columns.issubset(daily_df.columns):
            return None

        df = daily_df
        if display_days:
            today = df["date"].max()
            if today:
                start_date = today - pl.duration(days=display_days)
                df = df.filter(pl.col("date") > start_date)

        exploded = (
            df
            .select([
                "date",
                "types",
                "activity_durations",
                "activity_tss",
                "activity_distances",
                "activity_avg_power",
                "activity_avg_hr",
                "activity_max_hr",
                "activity_elevation_gain",
                "activity_ftp",
            ])
            .explode([
                "types",
                "activity_durations",
                "activity_tss",
                "activity_distances",
                "activity_avg_power",
                "activity_avg_hr",
                "activity_max_hr",
                "activity_elevation_gain",
                "activity_ftp",
            ])
            .drop_nulls(subset=["types", "activity_durations", "activity_tss"])
            .sort(["date", "activity_durations"], descending=[True, True])
        )

        if exploded.is_empty():
            return ActivityHistoryResult(activities=[], has_data=False)

        entries = [
            ActivityHistoryEntry(
                date=row["date"].strftime("%Y-%m-%d"),
                activity_type=str(row["types"]),
                duration_h=round(float(row["activity_durations"]), 1),
                training_stress=round(float(row["activity_tss"]), 1),
                distance_km=self._to_optional_float(row["activity_distances"]),
                avg_power=self._to_optional_float(row["activity_avg_power"]),
                avg_hr=self._to_optional_float(row["activity_avg_hr"]),
                max_hr=self._to_optional_float(row["activity_max_hr"]),
                elevation_gain=self._to_optional_float(row["activity_elevation_gain"]),
                ftp=self._to_optional_float(row["activity_ftp"]),
            )
            for row in exploded.to_dicts()
        ]

        return ActivityHistoryResult(activities=entries, has_data=bool(entries))

    @override
    async def provide_context(self, result: ActivityHistoryResult | None) -> str:
        """Provides a compact recent activity history summary.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing recent activity context for the planner.
        """
        if not result or not result.has_data:
            return ""

        lines = ["Recent Activities:"]
        for activity in result.activities[:5]:
            summary = f"- {activity.date}: {activity.activity_type}, {activity.duration_h:.1f}h, {activity.training_stress:.0f} TSS"
            if activity.distance_km is not None:
                summary += f", {activity.distance_km:.1f}km"
            lines.append(summary)
        return "\n".join(lines)

    @override
    def get_dashboard_widget(
        self, result: ActivityHistoryResult | None, display_days: int | None = None
    ) -> DashboardWidget | None:
        """Format the activity history for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            A custom dashboard widget, or None when no activity history is available.
        """
        if not result or not result.has_data:
            return None

        return DashboardWidget(
            name="activity_history",
            title="Recent Activity History",
            custom_template="widgets/activity_history.html",
            data={
                "activities": [
                    {
                        "date": activity.date,
                        "type": activity.activity_type,
                        "duration_h": activity.duration_h,
                        "training_stress": activity.training_stress,
                        "distance_km": activity.distance_km,
                        "avg_power": activity.avg_power,
                        "avg_hr": activity.avg_hr,
                        "max_hr": activity.max_hr,
                        "elevation_gain": activity.elevation_gain,
                        "ftp": activity.ftp,
                    }
                    for activity in result.activities
                ]
            },
        )

    @staticmethod
    def _to_optional_float(value: object) -> float | None:
        """Convert numeric widget values while preserving nulls.

        Args:
            value: Potential numeric value from the aggregated activity row.

        Returns:
            Rounded float output, or None if the value is missing.
        """
        if value is None or not isinstance(value, Real):
            return None
        return round(float(value), 1)
