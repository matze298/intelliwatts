"""Calculate the sports science analysis."""

from datetime import UTC, date, datetime
from logging import getLogger
from typing import TYPE_CHECKING

import polars as pl

from app.intervals.models import AnalysisResult, PMCResult, TrainingLoad
from app.planning.providers.registry import registry

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient
    from app.intervals.parser.activity import ParsedActivity
    from app.intervals.parser.power_curve import ParsedPowerCurve
    from app.intervals.parser.wellness import ParsedWellness

_LOGGER = getLogger(__name__)


def compute_analysis(
    activities: list[ParsedActivity],
    display_days: int | None = None,
    wellness_data: list[ParsedWellness] | None = None,
    power_curve: list[ParsedPowerCurve] | None = None,
    client: IntervalsClient | None = None,
) -> AnalysisResult:
    """Compute a complete sports science analysis using registered providers.

    Args:
        activities: The activities to analyze.
        display_days: The number of days to include in the dashboard widgets.
        wellness_data: Optional wellness data to analyze trends.
        power_curve: Optional power curve data (handled by provider directly).
        client: Optional Intervals.icu client for provider-specific data fetching.

    Returns:
        The analysis result including provider results and widgets.
    """
    if not activities and not wellness_data and not power_curve:
        return AnalysisResult()

    # 1. Initialize DataFrame and daily aggregation
    _, daily = _init_activities_df(activities)

    # 2. Determine full date range and join all dates
    min_date, max_date = _get_analysis_range(daily, wellness_data)

    if min_date is None or max_date is None:
        return AnalysisResult()

    all_dates = pl.DataFrame({"date": pl.date_range(start=min_date, end=max_date, interval="1d", eager=True)})
    daily = all_dates.join(daily, on="date", how="left").with_columns(pl.col("training_stress").fill_null(0))

    # 3. Join wellness data if provided
    if wellness_data:
        df_wellness = pl.from_dicts([w.__dict__ for w in wellness_data]).with_columns(
            pl.col("date").str.to_date("%Y-%m-%d")
        )
        daily = daily.join(df_wellness, on="date", how="left")

    # 4. Trigger Provider Analysis (New Dynamic Architecture)
    provider_results, provider_widgets = registry.process_analysis(
        daily,
        client=client,
        display_days=display_days,
    )

    return AnalysisResult(
        provider_results=provider_results,
        widgets=provider_widgets,
    )


def _init_activities_df(activities: list[ParsedActivity]) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Initialize the activities DataFrame and aggregate daily stress.

    Args:
        activities: The list of parsed activities.

    Returns:
        A tuple of (full_activities_df, daily_aggregated_df).
    """
    if not activities:
        # Return empty dataframes with correct schemas if no activities
        df = pl.DataFrame(schema={"date": pl.Date, "training_stress": pl.Float64})
        return df, df

    # Normalize zone data during creation
    # Power zones come as list of dicts [{"secs": 10}, ...], convert to list of ints
    data = []
    for a in activities:
        d = {
            "date": a.date,
            "training_stress": a.training_stress,
            "duration_h": a.duration_h,
            "distance_km": a.distance_km,
            "hr_zone_times": a.hr_zone_times,
            "type": a.type,
        }
        if a.power_zone_times:
            d["power_zone_times"] = [z.get("secs", 0) for z in a.power_zone_times]
        else:
            d["power_zone_times"] = []
        data.append(d)

    df = pl.from_dicts(data).with_columns(pl.col("date").str.to_date("%Y-%m-%d"))
    daily = df.group_by("date").agg([
        pl.sum("training_stress"),
        pl.sum("duration_h"),
        pl.sum("distance_km"),
        pl.col("hr_zone_times"),
        pl.col("power_zone_times"),
        pl.col("type").alias("types"),
        pl.col("duration_h").alias("activity_durations"),
    ])
    return df, daily


def _get_analysis_range(
    daily: pl.DataFrame, wellness_data: list[ParsedWellness] | None
) -> tuple[date | None, date | None]:
    """Determine the date range for analysis.

    Args:
        daily: The daily aggregated activities.
        wellness_data: Optional wellness data.

    Returns:
        A tuple of (min_date, max_date).
    """
    dates = daily["date"].to_list()
    if wellness_data:
        dates.extend([datetime.strptime(w.date, "%Y-%m-%d").replace(tzinfo=UTC).date() for w in wellness_data])

    if not dates:
        return None, None

    return min(dates), max(dates)


def compute_load(activities: list[ParsedActivity], client: IntervalsClient | None = None) -> TrainingLoad:
    """Compute the training load.

    Args:
        activities: The activities to analyze.
        client: Optional Intervals.icu client.

    Returns:
        The training load (CTL, ATL & TSB).
    """
    analysis = compute_analysis(activities, client=client)
    pmc_res = analysis.provider_results.get("pmc")
    if not pmc_res:
        return TrainingLoad(chronic=0.0, acute=0.0)

    # Normalized result as a PMCResult instance
    if isinstance(pmc_res, dict):
        pmc_res = PMCResult.from_dict(pmc_res)

    try:
        chronic = pmc_res.ctl[-1] if pmc_res.ctl else 0.0
        acute = pmc_res.atl[-1] if pmc_res.atl else 0.0
    except AttributeError, KeyError, IndexError, TypeError:
        chronic = 0.0
        acute = 0.0

    return TrainingLoad(chronic=chronic, acute=acute)


def calculate_watts_per_kg(weight_kg: float, power_watts: float) -> float:
    """Calculate the watts per kilogram.

    Args:
        weight_kg: The weight of the athlete in kilograms.
        power_watts: The power of the athlete in watts.

    Returns:
        The watts per kilogram.
    """
    if weight_kg <= 0:
        return 0.0
    return power_watts / weight_kg
