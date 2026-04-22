"""Calculate the sports science analysis."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from logging import getLogger
from typing import TYPE_CHECKING, Any, cast

import polars as pl

if TYPE_CHECKING:
    from datetime import date

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
        """Compute the training stress balance."""
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
class WellnessSummary:
    """Summary of wellness metrics."""

    hrv_7d: float | None
    hrv_42d: float | None
    resting_hr_7d: float | None
    resting_hr_42d: float | None

    def to_dict(self) -> dict[str, Any]:
        """Convert the wellness summary to a dictionary.

        Returns:
            The wellness summary as a serializable dictionary.
        """
        return asdict(self)


FTP_TRAJECTORY_LOOKBACK_DAYS = 28


@dataclass(frozen=True)
class FtpTrajectory:
    """FTP trajectory over time."""

    current_ftp: float | None
    ftp_4w_ago: float | None
    change_pct: float | None

    def to_dict(self) -> dict[str, Any]:
        """Convert the FTP trajectory to a dictionary.

        Returns:
            The FTP trajectory as a dictionary.
        """
        return asdict(self)


@dataclass(frozen=True)
class PowerCurveSummary:
    """Summary of peak power values."""

    peak_5s: int | None
    peak_1m: int | None
    peak_5m: int | None
    peak_20m: int | None

    def to_dict(self) -> dict[str, Any]:
        """Convert the power curve summary to a dictionary.

        Returns:
            The power curve summary as a dictionary.
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
    wellness_summary: dict[str, Any] | None = None
    ftp_trajectory: dict[str, Any] | None = None
    power_curve: dict[str, Any] | None = None
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


def compute_analysis(  # noqa: PLR0914
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
    min_date, max_date = _get_analysis_range(daily, wellness_data)

    if min_date is None or max_date is None:
        # If no time-series data, we can still compute power curve summary
        power_curve_dict = None
        if power_curve:
            power_curve_dict = _compute_power_curve_summary(power_curve)

        return AnalysisResult(
            daily_series=[],
            weekly_series=[],
            summary=ActivitySummary(0, 0, 0, 0, 0, 0),
            hr_intensity_distribution=[],
            power_intensity_distribution=[],
            activity_type_distribution={},
            wellness_summary=None,
            ftp_trajectory=None,
            power_curve=power_curve_dict,
        )

    all_dates = pl.DataFrame({
        "date": pl.date_range(start=cast("date", min_date), end=cast("date", max_date), interval="1d", eager=True)
    })
    daily = all_dates.join(daily, on="date", how="left").with_columns(pl.col("training_stress").fill_null(0))

    # 3. Process wellness trends
    wellness_summary_dict = None
    if wellness_data:
        daily, wellness_summary_dict = _compute_wellness_trends(daily, wellness_data)

    # 4. Process FTP trajectory
    ftp_trajectory_dict = None
    if not daily.is_empty() and "ftp" in daily.columns:
        ftp_trajectory_dict = _compute_ftp_trajectory(daily)

    # 5. Process Power Curve
    power_curve_dict = None
    if power_curve:
        power_curve_dict = _compute_power_curve_summary(power_curve)

    # 6. Run calculations for all providers and collect results/widgets
    # Local import to avoid circular dependency
    from app.planning.providers.registry import registry  # noqa: PLC0415

    provider_results, provider_widgets = registry.process_analysis(
        daily,
        client=client,
        wellness_summary=wellness_summary_dict,
        ftp_trajectory=ftp_trajectory_dict,
        power_curve=power_curve_dict,
    )

    # 7. Compute PMC values (CTL/ATL/TSB) and build series
    pmc = compute_pmc_values(daily)
    daily_series_df = _build_daily_series_df(daily, pmc.ctl, pmc.atl, pmc.tsb, has_wellness=wellness_data is not None)

    # 8. Filter for display and compute summaries
    daily_series_df, df_activities = _filter_by_display_days(daily_series_df, df_activities, display_days)
    daily_series_df = daily_series_df.with_columns(pl.col("date").dt.strftime("%Y-%m-%d"))

    # 9. Aggregate distributions and summaries
    summary, hr_dist, power_dist, type_dist = _get_activity_metrics(df_activities)
    weekly_series = _get_weekly_series(df_activities)

    return AnalysisResult(
        daily_series=daily_series_df.to_dicts(),
        weekly_series=weekly_series,
        summary=summary,
        hr_intensity_distribution=hr_dist,
        power_intensity_distribution=power_dist,
        activity_type_distribution=type_dist,
        wellness_summary=wellness_summary_dict,
        ftp_trajectory=ftp_trajectory_dict,
        power_curve=power_curve_dict,
        provider_results=provider_results,
        widgets=provider_widgets,
    )


def _init_activities_df(activities: list[ParsedActivity]) -> tuple[pl.DataFrame | None, pl.DataFrame]:
    """Initialize activities DataFrame and perform daily aggregation.

    Returns:
        A tuple of (full activities DataFrame, daily aggregated DataFrame).
    """
    if not activities:
        return None, pl.DataFrame(
            {"date": [], "training_stress": [], "ftp": []},
            schema={"date": pl.Date, "training_stress": pl.Float64, "ftp": pl.Float64},
        )

    df = pl.DataFrame([vars(a) for a in activities])
    df = df.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))
    daily = df.group_by("date").agg([pl.sum("training_stress"), pl.max("ftp")]).sort("date")
    return df, daily


def _get_analysis_range(daily: pl.DataFrame, wellness_data: list[ParsedWellness] | None) -> tuple[Any, Any]:
    """Calculate the min and max date for the analysis.

    Returns:
        A tuple of (min_date, max_date).
    """
    min_date = daily["date"].min() if not daily.is_empty() else None
    max_date = daily["date"].max() if not daily.is_empty() else None

    if wellness_data:
        wellness_dates = [datetime.strptime(w.date, "%Y-%m-%d").replace(tzinfo=UTC).date() for w in wellness_data]
        min_date = min(min_date, *wellness_dates) if min_date else min(wellness_dates)
        max_date = max(max_date, *wellness_dates) if max_date else max(wellness_dates)

    return min_date, max_date


def _compute_wellness_trends(
    daily: pl.DataFrame, wellness_data: list[ParsedWellness]
) -> tuple[pl.DataFrame, dict[str, Any]]:
    """Compute rolling averages for wellness metrics.

    Returns:
        A tuple of (updated daily DataFrame, wellness summary dictionary).
    """
    wellness_df = pl.DataFrame([vars(w) for w in wellness_data])
    wellness_df = wellness_df.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))
    daily = daily.join(wellness_df, on="date", how="left")

    daily = daily.with_columns([
        pl.col("hrv").rolling_mean(window_size=7, min_samples=1).alias("hrv_7d"),
        pl.col("hrv").rolling_mean(window_size=42, min_samples=1).alias("hrv_42d"),
        pl.col("resting_hr").rolling_mean(window_size=7, min_samples=1).alias("resting_hr_7d"),
        pl.col("resting_hr").rolling_mean(window_size=42, min_samples=1).alias("resting_hr_42d"),
    ])

    last_wellness = daily.tail(1).to_dicts()[0]
    summary = WellnessSummary(
        hrv_7d=last_wellness.get("hrv_7d"),
        hrv_42d=last_wellness.get("hrv_42d"),
        resting_hr_7d=last_wellness.get("resting_hr_7d"),
        resting_hr_42d=last_wellness.get("resting_hr_42d"),
    ).to_dict()

    return daily, summary


def _compute_ftp_trajectory(daily: pl.DataFrame) -> dict[str, Any]:
    """Compute the FTP trajectory from the daily series.

    Returns:
        The FTP trajectory as a dictionary.
    """
    # Forward fill FTP to handle days without activities
    df_ftp = daily.select(["date", "ftp"]).with_columns(pl.col("ftp").forward_fill())

    if df_ftp["ftp"].null_count() == len(df_ftp):
        return FtpTrajectory(None, None, None).to_dict()

    current_ftp = df_ftp["ftp"].tail(1).item()

    # Look back 4 weeks
    ftp_4w_ago = None
    if len(df_ftp) > FTP_TRAJECTORY_LOOKBACK_DAYS:
        ftp_4w_ago = df_ftp["ftp"].gather(len(df_ftp) - (FTP_TRAJECTORY_LOOKBACK_DAYS + 1)).item()

    change_pct = None
    if current_ftp and ftp_4w_ago and ftp_4w_ago > 0:
        change_pct = round(((current_ftp - ftp_4w_ago) / ftp_4w_ago) * 100, 2)

    return FtpTrajectory(
        current_ftp=float(current_ftp) if current_ftp else None,
        ftp_4w_ago=float(ftp_4w_ago) if ftp_4w_ago else None,
        change_pct=change_pct,
    ).to_dict()


def _compute_power_curve_summary(power_curves: list[ParsedPowerCurve]) -> dict[str, Any]:
    """Compute a summary of the power curve.

    Args:
        power_curves: The list of parsed power curves.

    Returns:
        The power curve summary as a dictionary.
    """
    # For now, we just take the first curve (usually the 90d one)
    if not power_curves:
        return PowerCurveSummary(None, None, None, None).to_dict()

    curve = power_curves[0]
    return PowerCurveSummary(
        peak_5s=curve.get_watts(5),
        peak_1m=curve.get_watts(60),
        peak_5m=curve.get_watts(300),
        peak_20m=curve.get_watts(1200),
    ).to_dict()


def _build_daily_series_df(
    daily: pl.DataFrame, ctl: pl.Series, atl: pl.Series, tsb: pl.Series, *, has_wellness: bool
) -> pl.DataFrame:
    """Build the daily series DataFrame.

    Returns:
        A DataFrame containing the daily metrics.
    """
    cols = {
        "date": daily["date"],
        "ctl": ctl,
        "atl": atl,
        "tsb": tsb,
    }
    if has_wellness:
        cols.update({
            "hrv": daily["hrv"],
            "resting_hr": daily["resting_hr"],
        })
    return pl.DataFrame(cols)


def _filter_by_display_days(
    daily_series_df: pl.DataFrame, df_activities: pl.DataFrame | None, display_days: int | None
) -> tuple[pl.DataFrame, pl.DataFrame | None]:
    """Filter DataFrames based on display days constraint.

    Returns:
        A tuple of (filtered daily series, filtered activities).
    """
    if display_days is not None:
        daily_series_df = daily_series_df.tail(display_days)
        display_start_date = daily_series_df["date"].min()
        if display_start_date and df_activities is not None:
            df_activities = df_activities.filter(pl.col("date") >= display_start_date)
    return daily_series_df, df_activities


def _get_weekly_series(df: pl.DataFrame | None) -> list[dict[str, Any]]:
    """Aggregate activities into a weekly series.

    Returns:
        A list of weekly aggregation dictionaries.
    """
    if df is None or df.is_empty():
        return []

    df_weekly = df.with_columns(pl.col("date").dt.truncate("1w").alias("week"))
    weekly = (
        df_weekly
        .group_by("week")
        .agg([
            pl.sum("duration_h").alias("duration_h"),
            pl.sum("training_stress").alias("training_stress"),
            pl.sum("distance_km").alias("distance_km"),
            pl.sum("elevation_gain").alias("elevation_gain"),
        ])
        .sort("week")
    )
    return weekly.with_columns(pl.col("week").dt.strftime("%Y-%m-%d")).to_dicts()


def _get_activity_metrics(df: pl.DataFrame | None) -> tuple[ActivitySummary, list[float], list[float], dict[str, int]]:
    """Compute summary metrics and distributions for activities.

    Returns:
        A tuple of (summary, hr distribution, power distribution, type distribution).
    """
    if df is None or df.is_empty():
        return ActivitySummary(0, 0, 0, 0, 0, 0), [], [], {}

    summary = ActivitySummary(
        total_duration_h=float(df["duration_h"].sum()),
        total_distance_km=float(df["distance_km"].sum()),
        total_elevation_gain=float(df["elevation_gain"].sum()),
        total_calories=float(df["calories"].sum()),
        total_training_stress=float(df["training_stress"].sum()),
        activity_count=len(df),
    )
    hr_dist = _aggregate_hr_zones(df)
    power_dist = _aggregate_power_zones(df)
    type_dist = {str(k): int(v) for k, v in df["type"].value_counts().rows()}

    return summary, hr_dist, power_dist, type_dist


def _aggregate_power_zones(df: pl.DataFrame) -> list[float]:
    """Aggregate the power zones.

    Returns:
        The time in seconds spent in each power zone.
    """
    valid_zones = df["power_zone_times"].drop_nulls()
    if not valid_zones.is_empty():
        num_zones = len(valid_zones[0])
    else:
        return []
    zones = [0.0] * num_zones
    for z_list in valid_zones:
        for i, val in enumerate(z_list):
            zones[i] += float(val["secs"])
    total = sum(zones)
    return [z / total if total > 0 else 0 for z in zones]


def _aggregate_hr_zones(df: pl.DataFrame, num_hr_zones: int = 7) -> list[float]:
    """Aggregate the HR zones.

    Returns:
        The time in seconds spent in each HR zone.
    """
    zones = [0] * num_hr_zones
    for z_list in df["hr_zone_times"].drop_nulls():
        for i, val in enumerate(z_list):
            if i < num_hr_zones:
                zones[i] += val
    total: int = sum(zones)
    return [z / total if total > 0 else 0 for z in zones]


def compute_pmc_values(df_daily: pl.DataFrame) -> PMCResult:
    """Computes the Performance Management Chart values using an exponentially weighted moving average (EWMA).

    Follows the definition from https://www.sciencetosport.com/monitoring-training-load/.

    Returns:
        PMCResult containing CTL, ATL and TSB.
    """
    alpha_ctl = 1 - math.exp(-1 / CHRONIC_TRAINING_LOAD_DAYS)
    alpha_atl = 1 - math.exp(-1 / ACUTE_TRAINING_LOAD_DAYS)
    ctl = df_daily.select(pl.col("training_stress").ewm_mean(alpha=alpha_ctl, adjust=False)).to_series()
    atl = df_daily.select(pl.col("training_stress").ewm_mean(alpha=alpha_atl, adjust=False)).to_series()
    tsb = ctl - atl
    return PMCResult(ctl=ctl, atl=atl, tsb=tsb)


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


def calculate_power_to_weight(power_watts: float, weight_kg: float) -> float:
    """Calculate the power-to-weight ratio (W/kg).

    Args:
        power_watts: The power output in Watts.
        weight_kg: The weight in kilograms.

    Returns:
        The power-to-weight ratio rounded to 2 decimal places.

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
