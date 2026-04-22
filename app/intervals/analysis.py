"""Calculate the sports science analysis."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from logging import getLogger
from typing import TYPE_CHECKING, Any, cast

import polars as pl

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient
    from app.intervals.parser.activity import ParsedActivity
    from app.intervals.parser.power_curve import ParsedPowerCurve
    from app.intervals.parser.wellness import ParsedWellness
    from app.planning.providers.base import DashboardWidget

_LOGGER = getLogger(__name__)
CHRONIC_TRAINING_LOAD_DAYS = 42
ACUTE_TRAINING_LOAD_DAYS = 7


@dataclass(frozen=True)
class TrainingLoad:
    """Training load."""

    chronic: float
    acute: float

    @property
    def training_stress_balance(self) -> float:
        """Calculate the training stress balance (TSB).

        Returns:
            The training stress balance.
        """
        return self.chronic - self.acute

    def to_dict(self) -> dict[str, Any]:
        """Convert the training load to a dictionary.

        Returns:
            The training load as a serializable dictionary.
        """
        return asdict(self)


@dataclass(frozen=True)
class ActivitySummary:
    """Summary of activities."""

    total_duration_h: float
    total_distance_km: float
    total_elevation_gain: float
    total_calories: float
    total_training_stress: float
    activity_count: int

    def to_dict(self) -> dict[str, Any]:
        """Convert the summary to a dictionary.

        Returns:
            The summary as a serializable dictionary.
        """
        return asdict(self)


@dataclass(frozen=True)
class AnalysisResult:
    """Result of the sports science analysis."""

    daily_series: list[dict[str, Any]]
    weekly_series: list[dict[str, Any]]
    summary: ActivitySummary
    hr_intensity_distribution: list[float]
    power_intensity_distribution: list[float]
    activity_type_distribution: dict[str, int]
    provider_results: dict[str, Any] = field(default_factory=dict)
    widgets: list[DashboardWidget] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the analysis result to a dictionary.

        Returns:
            The analysis result as a serializable dictionary.
        """
        return asdict(self)


@dataclass(frozen=True)
class PMCResult:
    """Performance Management Chart results."""

    ctl: pl.Series
    atl: pl.Series
    tsb: pl.Series


def compute_analysis(
    activities: list[ParsedActivity],
    display_days: int | None = None,
    wellness_data: list[ParsedWellness] | None = None,
    power_curve: list[ParsedPowerCurve] | None = None,
    client: IntervalsClient | None = None,
) -> AnalysisResult:
    """Compute a complete sports science analysis.

    Args:
        activities: The activities to analyze.
        display_days: The number of days to include in the final analysis result.
            If set, only the last `display_days` will be returned in the series and summaries.
            However, the CTL/ATL calculation will still use all available activities for initialization.
        wellness_data: Optional wellness data to analyze trends.
        power_curve: Optional power curve data.
        client: Optional Intervals.icu client for provider-specific data fetching.

    Returns:
        The analysis result including time series and summaries.
    """
    if not activities and not wellness_data and not power_curve:
        return AnalysisResult(
            daily_series=[],
            weekly_series=[],
            summary=ActivitySummary(0, 0, 0, 0, 0, 0),
            hr_intensity_distribution=[],
            power_intensity_distribution=[],
            activity_type_distribution={},
        )

    # 1. Initialize DataFrame and daily aggregation
    df_activities, daily = _init_activities_df(activities)

    # 2. Determine full date range and join all dates
    min_date, max_date = _get_analysis_range(daily, wellness_data, display_days)

    if min_date is None or max_date is None:
        return AnalysisResult(
            daily_series=[],
            weekly_series=[],
            summary=ActivitySummary(0, 0, 0, 0, 0, 0),
            hr_intensity_distribution=[],
            power_intensity_distribution=[],
            activity_type_distribution={},
        )

    all_dates = pl.DataFrame({"date": pl.date_range(start=min_date, end=max_date, interval="1d", eager=True)})
    daily = all_dates.join(daily, on="date", how="left").with_columns(pl.col("training_stress").fill_null(0))

    # 3. Join wellness data if available
    if wellness_data:
        wellness_df = pl.DataFrame([vars(w) for w in wellness_data])
        wellness_df = wellness_df.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))
        daily = daily.join(wellness_df, on="date", how="left")

    # 4. Run calculations for all providers and collect results/widgets
    # Local import to avoid circular dependency
    from app.planning.providers.registry import registry  # noqa: PLC0415

    provider_results, provider_widgets = registry.process_analysis(
        daily,
        client=client,
    )

    # 5. Compute PMC values (CTL/ATL/TSB) and build series
    pmc = compute_pmc_values(daily)
    daily_series_df = _build_daily_series_df(daily, pmc.ctl, pmc.atl, pmc.tsb, has_wellness=wellness_data is not None)

    # 6. Filter for display and compute summaries
    daily_series_df, df_activities = _filter_by_display_days(daily_series_df, df_activities, display_days)
    daily_series_df = daily_series_df.with_columns(pl.col("date").dt.strftime("%Y-%m-%d"))

    # 7. Aggregate distributions and summaries
    summary, hr_dist, power_dist, type_dist = _get_activity_metrics(df_activities)
    weekly_series = _get_weekly_series(df_activities)

    return AnalysisResult(
        daily_series=daily_series_df.to_dicts(),
        weekly_series=weekly_series,
        summary=summary,
        hr_intensity_distribution=hr_dist,
        power_intensity_distribution=power_dist,
        activity_type_distribution=type_dist,
        provider_results=provider_results,
        widgets=provider_widgets,
    )


def _init_activities_df(activities: list[ParsedActivity]) -> tuple[pl.DataFrame | None, pl.DataFrame]:
    """Initialize activities DataFrame and perform daily aggregation.

    Args:
        activities: List of parsed activity objects.

    Returns:
        A tuple of (activities DataFrame, daily aggregated DataFrame).
    """
    if not activities:
        return None, pl.DataFrame(
            {"date": [], "training_stress": []}, schema={"date": pl.Date, "training_stress": pl.Int32}
        )

    df = pl.DataFrame([vars(a) for a in activities])
    df = df.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))

    agg_exprs = [
        pl.sum("training_stress").alias("training_stress"),
        pl.sum("duration_h").alias("duration_h"),
        pl.sum("distance_km").alias("distance_km"),
        pl.sum("elevation_gain").alias("elevation_gain"),
        pl.sum("calories").alias("calories"),
    ]
    agg_exprs.extend([pl.last(col).alias(col) for col in ["ftp", "resting_hr"] if col in df.columns])
    agg_exprs.extend([pl.col(col) for col in ["hr_zone_times", "power_zone_times"] if col in df.columns])

    daily = df.group_by("date").agg(agg_exprs).sort("date")
    return df, daily


def _get_analysis_range(
    daily: pl.DataFrame, wellness_data: list[ParsedWellness] | None, display_days: int | None = None
) -> tuple[date | None, date | None]:
    """Determine the full date range for analysis.

    Args:
        daily: Aggregated daily activity data.
        wellness_data: List of parsed wellness objects.
        display_days: Optional number of days to ensure in the range.

    Returns:
        A tuple of (min_date, max_date).
    """
    dates: list[date] = []
    if not daily.is_empty():
        dates.extend([cast("date", daily["date"].min()), cast("date", daily["date"].max())])
    if wellness_data:
        w_dates = [datetime.strptime(w.date, "%Y-%m-%d").replace(tzinfo=UTC).date() for w in wellness_data]
        dates.extend([min(w_dates), max(w_dates)])

    if not dates:
        return None, None

    min_date = min(dates)
    max_date = max(dates)

    if display_days:
        min_date = min(min_date, max_date - timedelta(days=display_days - 1))

    return min_date, max_date


def compute_pmc_values(df_daily: pl.DataFrame) -> PMCResult:
    """Compute CTL, ATL, and TSB values using exponentially weighted moving averages.

    Args:
        df_daily: Daily aggregated data with "training_stress".

    Returns:
        PMCResult containing the computed series.
    """
    alpha_ctl = 1 - math.exp(-1 / CHRONIC_TRAINING_LOAD_DAYS)
    alpha_atl = 1 - math.exp(-1 / ACUTE_TRAINING_LOAD_DAYS)

    ctl = df_daily.select(pl.col("training_stress").ewm_mean(alpha=alpha_ctl, adjust=False)).to_series()
    atl = df_daily.select(pl.col("training_stress").ewm_mean(alpha=alpha_atl, adjust=False)).to_series()
    tsb = ctl - atl
    return PMCResult(ctl=ctl, atl=atl, tsb=tsb)


def _build_daily_series_df(
    daily: pl.DataFrame,
    ctl: pl.Series,
    atl: pl.Series,
    tsb: pl.Series,
    has_wellness: bool,  # noqa: FBT001
) -> pl.DataFrame:
    """Build the final daily series DataFrame.

    Args:
        daily: The daily aggregated data.
        ctl: Computed CTL series.
        atl: Computed ATL series.
        tsb: Computed TSB series.
        has_wellness: Whether wellness data was included.

    Returns:
        The complete daily series DataFrame.
    """
    cols = [
        daily["date"],
        daily["training_stress"],
        ctl.alias("ctl"),
        atl.alias("atl"),
        tsb.alias("tsb"),
    ]
    if has_wellness:
        cols.extend([daily[col] for col in ["hrv", "resting_hr"] if col in daily.columns])

    return pl.DataFrame(cols)


def _filter_by_display_days(
    daily_series: pl.DataFrame, activities: pl.DataFrame | None, display_days: int | None
) -> tuple[pl.DataFrame, pl.DataFrame | None]:
    """Filter the results based on the requested display days.

    Args:
        daily_series: The full daily series DataFrame.
        activities: The full activities DataFrame.
        display_days: Number of days to keep.

    Returns:
        A tuple of (filtered daily_series, filtered activities).
    """
    if not display_days:
        return daily_series, activities

    daily_series = daily_series.tail(display_days)
    if activities is not None:
        min_date = daily_series["date"].min()
        activities = activities.filter(pl.col("date") >= min_date)

    return daily_series, activities


def _extract_zone_distributions(df: pl.DataFrame) -> tuple[list[float], list[float]]:
    """Extract intensity distributions from zone time columns.

    Args:
        df: The activities DataFrame.

    Returns:
        A tuple of (hr_dist, power_dist).
    """
    hr_dist = [0.0] * 7
    power_dist = [0.0] * 7

    for col, dist in [("hr_zone_times", hr_dist), ("power_zone_times", power_dist)]:
        if col not in df.columns:
            continue
        for entry in df[col]:
            if not isinstance(entry, list):
                continue
            # Handle both list of ints and list of lists (from daily agg)
            if entry and isinstance(entry[0], list):
                for sub_list in entry:
                    for i, val in enumerate(sub_list[:7]):
                        dist[i] += float(val)
            else:
                for i, val in enumerate(entry[:7]):
                    dist[i] += float(val)
    return hr_dist, power_dist


def _get_activity_metrics(df: pl.DataFrame | None) -> tuple[ActivitySummary, list[float], list[float], dict[str, int]]:
    """Aggregate metrics from the activities DataFrame.

    Args:
        df: The activities DataFrame.

    Returns:
        A tuple of (ActivitySummary, hr_dist, power_dist, type_dist).
    """
    if df is None or df.is_empty():
        return ActivitySummary(0, 0, 0, 0, 0, 0), [], [], {}

    summary = ActivitySummary(
        total_duration_h=round(df["duration_h"].sum(), 1),
        total_distance_km=round(df["distance_km"].sum(), 1),
        total_elevation_gain=round(df["elevation_gain"].sum(), 0),
        total_calories=round(df["calories"].sum(), 0),
        total_training_stress=round(df["training_stress"].sum(), 0),
        activity_count=len(df),
    )

    hr_dist, power_dist = _extract_zone_distributions(df)

    type_counts = df["type"].value_counts().sort("count", descending=True).to_dicts()
    type_dict = {d["type"]: d["count"] for d in type_counts}

    return summary, hr_dist, power_dist, type_dict


def _get_weekly_series(df: pl.DataFrame | None) -> list[dict[str, Any]]:
    """Aggregate daily data into weekly summaries.

    Args:
        df: The activities DataFrame.

    Returns:
        A list of weekly summary dictionaries.
    """
    if df is None or df.is_empty():
        return []

    weekly = (
        df
        .with_columns(pl.col("date").dt.truncate("1w").alias("week"))
        .group_by("week")
        .agg([
            pl.sum("duration_h").alias("duration_h"),
            pl.sum("training_stress").alias("training_stress"),
            pl.sum("distance_km").alias("distance_km"),
            pl.sum("elevation_gain").alias("elevation_gain"),
        ])
        .select([
            "week",
            "duration_h",
            "training_stress",
            "distance_km",
            "elevation_gain",
        ])
        .sort("week")
    )
    return weekly.with_columns(pl.col("week").dt.strftime("%Y-%m-%d")).to_dicts()


def compute_load(activities: list[ParsedActivity], client: IntervalsClient | None = None) -> TrainingLoad:
    """Compute the training load.

    Args:
        activities: The activities to analyze.
        client: Optional Intervals.icu client.

    Returns:
        The training load (CTL, ATL & TSB).
    """
    analysis = compute_analysis(activities, client=client)
    if not analysis.daily_series:
        return TrainingLoad(chronic=0, acute=0)
    last_day = analysis.daily_series[-1]
    return TrainingLoad(chronic=last_day["ctl"], acute=last_day["atl"])


def calculate_watts_per_kg(weight_kg: float, power_watts: float) -> float:
    """Calculate the power to weight ratio (W/kg).

    Args:
        weight_kg: The weight in kilograms.
        power_watts: The power in watts.

    Returns:
        The power to weight ratio.

    Raises:
        ValueError: If weight is <= 0 or power is < 0.
    """
    if weight_kg <= 0:
        msg = "Weight must be greater than zero"
        raise ValueError(msg)
    if power_watts < 0:
        msg = "Power cannot be negative"
        raise ValueError(msg)

    return round(power_watts / weight_kg, 2)
