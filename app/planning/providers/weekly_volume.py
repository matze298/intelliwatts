"""Weekly volume comparison metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class WeeklyVolumeResult:
    """Result of the weekly volume calculation."""

    weeks: list[str]
    duration_by_type: dict[str, list[float]]
    tss_by_type: dict[str, list[float]]
    has_data: bool


class WeeklyVolumeProvider(MetricProvider[WeeklyVolumeResult]):
    """Provides weekly training volume comparison (Duration & TSS)."""

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "weekly_volume"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        display_days: int | None = None,
    ) -> WeeklyVolumeResult:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            display_days: Optional number of days to display.

        Returns:
            The structured calculation result.
        """
        if (
            "types" not in daily_df.columns
            or "activity_durations" not in daily_df.columns
            or "activity_tss" not in daily_df.columns
        ):
            return WeeklyVolumeResult(weeks=[], duration_by_type={}, tss_by_type={}, has_data=False)

        df = daily_df

        # 1. Filter by display days if provided
        if display_days:
            today = df["date"].max()
            if today:
                start_date = today - pl.duration(days=display_days)
                df = df.filter(pl.col("date") >= start_date)

        if df.is_empty():
            return WeeklyVolumeResult(weeks=[], duration_by_type={}, tss_by_type={}, has_data=False)

        # 2. Explode and group by week and type
        # truncate("1w") in Polars starts on Monday
        df_exploded = (
            df
            .select(["date", "types", "activity_durations", "activity_tss"])
            .explode(["types", "activity_durations", "activity_tss"])
            .drop_nulls()
        )

        if df_exploded.is_empty():
            return WeeklyVolumeResult(weeks=[], duration_by_type={}, tss_by_type={}, has_data=False)

        weekly = (
            df_exploded
            .with_columns(pl.col("date").dt.truncate("1w").alias("week"))
            .group_by(["week", "types"])
            .agg([
                pl.col("activity_durations").sum().alias("duration"),
                pl.col("activity_tss").sum().alias("tss"),
            ])
            .sort("week")
        )

        # 3. Ensure all combinations of week and type exist to avoid missing data points in chart
        all_weeks = weekly["week"].unique().sort()
        all_types = weekly["types"].unique().sort()

        # Create a cartesian product of all weeks and all types
        grid = all_weeks.to_frame().join(all_types.to_frame(), how="cross")

        # Join back with calculated totals
        full_weekly = (
            grid
            .join(weekly, on=["week", "types"], how="left")
            .with_columns([
                pl.col("duration").fill_null(0.0),
                pl.col("tss").fill_null(0.0),
            ])
            .sort(["types", "week"])
        )

        # 4. Format for result
        weeks_str = [d.strftime("%Y-%m-%d") for d in all_weeks]
        duration_by_type = {}
        tss_by_type = {}

        for t in all_types:
            type_data = full_weekly.filter(pl.col("types") == t)
            duration_by_type[t] = [round(float(v), 1) for v in type_data["duration"].to_list()]
            tss_by_type[t] = [round(float(v), 0) for v in type_data["tss"].to_list()]

        return WeeklyVolumeResult(
            weeks=weeks_str,
            duration_by_type=duration_by_type,
            tss_by_type=tss_by_type,
            has_data=True,
        )

    @override
    async def provide_context(self, result: WeeklyVolumeResult) -> str:
        """Provides weekly volume context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the weekly volume context.
        """
        if not result.has_data or not result.weeks:
            return "No weekly volume data available."

        last_week = result.weeks[-1]
        summary = [f"Weekly Volume Summary (Last Week: {last_week}):"]

        for sport in result.duration_by_type:
            dur = result.duration_by_type[sport][-1]
            tss = result.tss_by_type[sport][-1]
            if dur > 0 or tss > 0:
                summary.append(f"- {sport}: {dur}h, {tss:.0f} TSS")

        return "\n".join(summary)

    @override
    def get_dashboard_widget(
        self, result: WeeklyVolumeResult, display_days: int | None = None
    ) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if not result.has_data:
            return None

        return DashboardWidget(
            name="weekly_volume",
            title="Weekly Volume",
            custom_template="widgets/weekly_volume_chart.html",
            data={
                "weeks": result.weeks,
                "duration_by_type": result.duration_by_type,
                "tss_by_type": result.tss_by_type,
            },
        )
