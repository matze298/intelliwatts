"""Calculate the sports science analysis."""

import math
from dataclasses import asdict, dataclass
from logging import getLogger
from typing import TYPE_CHECKING, Any, cast

import polars as pl

from app.intervals.parser.activity import ParsedActivity

if TYPE_CHECKING:
    from datetime import date


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
class AnalysisResult:
    """Result of the sports science analysis."""

    daily_series: list[dict[str, Any]]
    weekly_series: list[dict[str, Any]]
    summary: ActivitySummary
    hr_intensity_distribution: list[float]
    power_intensity_distribution: list[float]
    activity_type_distribution: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert the analysis result to a dictionary.

        Returns:
            The analysis result as a serializable dictionary.
        """
        return asdict(self)


def compute_analysis(activities: list[ParsedActivity]) -> AnalysisResult:
    """Compute a complete sports science analysis.

    Returns:
        The analysis result including time series and summaries.
    """
    if not activities:
        return AnalysisResult(
            daily_series=[],
            weekly_series=[],
            summary=ActivitySummary(0, 0, 0, 0, 0, 0),
            hr_intensity_distribution=[],
            power_intensity_distribution=[],
            activity_type_distribution={},
        )

    df = pl.DataFrame([vars(a) for a in activities])
    df = df.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))

    # Daily aggregation for Performance Management Chart (PMC)
    daily = df.group_by("date").agg(pl.sum("training_stress")).sort("date")
    # Generate a complete date range
    min_date = cast("date", daily["date"].min())
    max_date = cast("date", daily["date"].max())
    all_dates = pl.DataFrame({"date": pl.date_range(start=min_date, end=max_date, interval="1d", eager=True)})

    # Join with all_dates to fill missing dates and then fill nulls
    daily = all_dates.join(daily, on="date", how="left").with_columns(pl.col("training_stress").fill_null(0))

    ctl, atl, tsb = compute_pmc_values(daily)

    daily_series = pl.DataFrame({"date": daily["date"], "ctl": ctl, "atl": atl, "tsb": tsb})
    daily_series = daily_series.with_columns(pl.col("date").dt.strftime("%Y-%m-%d"))

    # Weekly aggregation
    df = df.with_columns(pl.col("date").dt.truncate("1w").alias("week"))
    weekly = (
        df
        .group_by("week")
        .agg([
            pl.sum("duration_h").alias("duration_h"),
            pl.sum("training_stress").alias("training_stress"),
            pl.sum("distance_km").alias("distance_km"),
            pl.sum("elevation_gain").alias("elevation_gain"),
        ])
        .sort("week")
    )
    weekly = weekly.with_columns(pl.col("week").dt.strftime("%Y-%m-%d"))

    # Summary
    summary = ActivitySummary(
        total_duration_h=float(df["duration_h"].sum()),
        total_distance_km=float(df["distance_km"].sum()),
        total_elevation_gain=float(df["elevation_gain"].sum()),
        total_calories=float(df["calories"].sum()),
        total_training_stress=float(df["training_stress"].sum()),
        activity_count=len(df),
    )

    return AnalysisResult(
        daily_series=daily_series.to_dicts(),
        weekly_series=weekly.to_dicts(),
        summary=summary,
        hr_intensity_distribution=_aggregate_hr_zones(df),
        power_intensity_distribution=_aggregate_power_zones(df),
        activity_type_distribution={str(k): int(v) for k, v in df["type"].value_counts().rows()},
    )


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


def compute_pmc_values(df_daily: pl.DataFrame) -> tuple[pl.Series, pl.Series, pl.Series]:
    """Computes the Performance Management Chart values using an exponentially weighted moving average (EWMA).

    Follows the definition from https://www.sciencetosport.com/monitoring-training-load/.

    Returns:
        Chronic Training Load (CTL), Acute Training Load (ATL) and Training Stress Balance (TSB).
    """
    alpha_ctl = 1 - math.exp(-1 / CHRONIC_TRAINING_LOAD_DAYS)
    alpha_atl = 1 - math.exp(-1 / ACUTE_TRAINING_LOAD_DAYS)
    ctl: pl.Series = df_daily.select(pl.col("training_stress").ewm_mean(alpha=alpha_ctl, adjust=False)).to_series()
    atl: pl.Series = df_daily.select(pl.col("training_stress").ewm_mean(alpha=alpha_atl, adjust=False)).to_series()
    tsb: pl.Series = ctl - atl
    return ctl, atl, tsb


def compute_load(activities: list[ParsedActivity]) -> TrainingLoad:
    """Compute the training load.

    Returns:
        The training load (CTL, ATL & TSB).
    """
    analysis = compute_analysis(activities)
    if not analysis.daily_series:
        return TrainingLoad(chronic=0, acute=0)
    last_day = analysis.daily_series[-1]
    return TrainingLoad(chronic=last_day["ctl"], acute=last_day["atl"])
