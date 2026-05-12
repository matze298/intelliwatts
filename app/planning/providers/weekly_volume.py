"""Weekly volume comparison metric provider."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, cast, override

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

        # 1. Prepare and filter data
        today = cast("date | None", daily_df["date"].max())
        df = daily_df
        if display_days and today:
            num_weeks = (display_days + 6) // 7
            end_week = pl.Series([today], dtype=pl.Date).dt.truncate("1w")[0]
            start_week = end_week - timedelta(weeks=num_weeks - 1)
            df = df.filter(pl.col("date") >= start_week)

        if df.is_empty():
            return WeeklyVolumeResult(weeks=[], duration_by_type={}, tss_by_type={}, has_data=False)

        # 2. Explode and group by week and type
        weekly = self._aggregate_weekly(df)
        if weekly.is_empty():
            return WeeklyVolumeResult(weeks=[], duration_by_type={}, tss_by_type={}, has_data=False)

        # 3. Ensure all combinations of week and type exist
        all_weeks = self._get_all_weeks(weekly, display_days, today)
        all_types = weekly["types"].unique().sort()
        full_weekly = self._align_to_grid(weekly, all_weeks, all_types)

        # 4. Format for result
        return self._format_result(full_weekly, all_weeks, all_types)

    @staticmethod
    def _aggregate_weekly(df: pl.DataFrame) -> pl.DataFrame:
        """Aggregate data by week and activity type.

        Args:
            df: The exploded activity DataFrame.

        Returns:
            A DataFrame aggregated by week and sport type.
        """
        df_exploded = (
            df
            .select(["date", "types", "activity_durations", "activity_tss"])
            .explode(["types", "activity_durations", "activity_tss"])
            .drop_nulls()
        )
        if df_exploded.is_empty():
            return pl.DataFrame()

        return (
            df_exploded
            .with_columns(pl.col("date").dt.truncate("1w").alias("week"))
            .group_by(["week", "types"])
            .agg([
                pl.col("activity_durations").sum().alias("duration"),
                pl.col("activity_tss").sum().alias("tss"),
            ])
            .sort("week")
        )

    @staticmethod
    def _get_all_weeks(weekly: pl.DataFrame, display_days: int | None, today: date | None) -> pl.Series:
        """Generate a continuous sequence of weeks.

        Args:
            weekly: The aggregated weekly DataFrame.
            display_days: Optional lookback in days.
            today: The latest date in the data.

        Returns:
            A Series of week start dates.
        """
        if display_days and today:
            num_weeks = (display_days + 6) // 7
            end_week_val = pl.Series([today], dtype=pl.Date).dt.truncate("1w")[0]
            start_week_val = end_week_val - timedelta(weeks=num_weeks - 1)
            return pl.date_range(
                cast("date", start_week_val),
                cast("date", end_week_val),
                interval="1w",
                eager=True,
            ).alias("week")

        min_week = weekly["week"].min()
        max_week = weekly["week"].max()
        return pl.date_range(
            cast("date", min_week),
            cast("date", max_week),
            interval="1w",
            eager=True,
        ).alias("week")

    @staticmethod
    def _align_to_grid(weekly: pl.DataFrame, all_weeks: pl.Series, all_types: pl.Series) -> pl.DataFrame:
        """Align weekly data to a full grid of weeks and types.

        Args:
            weekly: The aggregated weekly DataFrame.
            all_weeks: A Series of all weeks in the range.
            all_types: A Series of all unique activity types.

        Returns:
            A DataFrame with all combinations of week and sport type.
        """
        grid = all_weeks.to_frame().join(all_types.to_frame(), how="cross")
        return (
            grid
            .join(weekly, on=["week", "types"], how="left")
            .with_columns([
                pl.col("duration").fill_null(0.0),
                pl.col("tss").fill_null(0.0),
            ])
            .sort(["types", "week"])
        )

    @staticmethod
    def _format_result(full_weekly: pl.DataFrame, all_weeks: pl.Series, all_types: pl.Series) -> WeeklyVolumeResult:
        """Format the aligned data into a WeeklyVolumeResult.

        Args:
            full_weekly: The aligned DataFrame.
            all_weeks: A Series of all weeks.
            all_types: A Series of all unique activity types.

        Returns:
            A structured WeeklyVolumeResult object.
        """
        weeks_str = [d.strftime("%d.%m") for d in all_weeks]
        duration_by_type = {}

        tss_by_type = {}

        for t in all_types:
            type_data = full_weekly.filter(pl.col("types") == t)
            duration_by_type[t] = type_data["duration"].round(1).to_list()
            tss_by_type[t] = type_data["tss"].round(0).to_list()

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
