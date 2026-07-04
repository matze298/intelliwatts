"""Calculate the sports science analysis."""

from datetime import UTC, date, datetime
from logging import getLogger
from typing import TYPE_CHECKING

import polars as pl

from app.intervals.models import AnalysisResult, DailyRecordField, PMCResult, TrainingLoad
from app.planning.providers.registry import registry

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient
    from app.intervals.parser.activity import ParsedActivity
    from app.intervals.parser.wellness import ParsedWellness

_LOGGER = getLogger(__name__)
_ACTIVITY_NUMBER_FIELDS = (
    "duration_h",
    "training_stress",
    "calories",
    "avg_power",
    "avg_hr",
    "max_hr",
    "distance_km",
    "elevation_gain",
    "ftp",
)
_WELLNESS_NUMBER_FIELDS = (
    "hrv",
    "resting_hr",
    "sleep_score",
    "sleep_quality",
    "fatigue",
    "soreness",
    "stress",
    "readiness",
)


def compute_analysis(
    activities: list[ParsedActivity],
    display_days: int | None = None,
    wellness_data: list[ParsedWellness] | None = None,
    client: IntervalsClient | None = None,
) -> AnalysisResult:
    """Compute a complete sports science analysis using registered providers.

    Args:
        activities: The activities to analyze.
        display_days: The number of days to include in the dashboard widgets.
        wellness_data: Optional wellness data to analyze trends.
        client: Optional Intervals.icu client for provider-specific data fetching.

    Returns:
        The analysis result including provider results and widgets.
    """
    activities = _filter_valid_activities(activities)
    wellness_data = _filter_valid_wellness(wellness_data or [])

    if not activities and not wellness_data:
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

    record_columns = [field.value for field in DailyRecordField]
    record_exprs: list[pl.Expr] = [pl.col("date").dt.to_string("%Y-%m-%d").alias("date")]
    for column in record_columns:
        if column in daily.columns:
            record_exprs.append(pl.col(column))
        else:
            record_exprs.append(pl.lit(None).alias(column))

    daily_records = daily.select(record_exprs).to_dicts()

    # 4. Trigger Provider Analysis (New Dynamic Architecture)
    provider_results, provider_widgets = registry.process_analysis(
        daily,
        client=client,
        display_days=display_days,
    )

    return AnalysisResult(
        provider_results=provider_results,
        widgets=provider_widgets,
        daily_records=daily_records,
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
            "avg_power": a.avg_power,
            "avg_hr": a.avg_hr,
            "max_hr": a.max_hr,
            "elevation_gain": a.elevation_gain,
            "ftp": a.ftp,
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
        pl.col("training_stress").alias("activity_tss"),
        pl.col("distance_km").alias("activity_distances"),
        pl.col("avg_power").alias("activity_avg_power"),
        pl.col("avg_hr").alias("activity_avg_hr"),
        pl.col("max_hr").alias("activity_max_hr"),
        pl.col("elevation_gain").alias("activity_elevation_gain"),
        pl.col("ftp").alias("activity_ftp"),
    ])
    return df, daily


def _filter_valid_activities(activities: list[ParsedActivity]) -> list[ParsedActivity]:
    """Return activities that can safely enter DataFrame analysis."""
    valid_activities: list[ParsedActivity] = []
    for index, activity in enumerate(activities):
        reason = _get_activity_validation_error(activity)
        if reason is not None:
            _LOGGER.warning(
                "Skipping malformed activity record: index=%s date=%s reason=%s",
                index,
                _safe_record_date(activity),
                reason,
            )
            continue
        valid_activities.append(activity)
    return valid_activities


def _filter_valid_wellness(wellness_data: list[ParsedWellness]) -> list[ParsedWellness]:
    """Return wellness records that can safely enter date-window analysis."""
    valid_wellness: list[ParsedWellness] = []
    for index, record in enumerate(wellness_data):
        reason = _get_wellness_validation_error(record)
        if reason is not None:
            _LOGGER.warning(
                "Skipping malformed wellness record: index=%s date=%s reason=%s",
                index,
                _safe_record_date(record),
                reason,
            )
            continue
        valid_wellness.append(record)
    return valid_wellness


def _get_activity_validation_error(activity: ParsedActivity) -> str | None:
    if not _is_iso_date(activity.date):
        return "invalid_date"
    if not isinstance(activity.type, str):
        return "invalid_type"
    for field_name in _ACTIVITY_NUMBER_FIELDS:
        if not _is_optional_number(getattr(activity, field_name)):
            return f"invalid_{field_name}"
    if activity.hr_zone_times is not None and not _is_number_list(activity.hr_zone_times):
        return "invalid_hr_zone_times"
    if activity.power_zone_times is not None and not _is_power_zone_times(activity.power_zone_times):
        return "invalid_power_zone_times"
    return None


def _get_wellness_validation_error(record: ParsedWellness) -> str | None:
    if not _is_iso_date(record.date):
        return "invalid_date"
    for field_name in _WELLNESS_NUMBER_FIELDS:
        if not _is_optional_number(getattr(record, field_name)):
            return f"invalid_{field_name}"
    if record.comments is not None and not isinstance(record.comments, str):
        return "invalid_comments"
    return None


def _is_iso_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_optional_number(value: object) -> bool:
    return value is None or (isinstance(value, int | float) and not isinstance(value, bool))


def _is_number_list(value: object) -> bool:
    return isinstance(value, list) and all(_is_optional_number(item) and item is not None for item in value)


def _is_power_zone_times(value: object) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) and _is_optional_number(item.get("secs")) and item.get("secs") is not None
        for item in value
    )


def _safe_record_date(record: object) -> str:
    record_date = getattr(record, "date", None)
    return record_date if isinstance(record_date, str) else "<missing>"


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
