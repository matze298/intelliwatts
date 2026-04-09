"""Calculate the sports science analysis."""

import math
from dataclasses import asdict, dataclass
from logging import getLogger
from typing import Any

import pandas as pd

from app.intervals.parser.activity import ParsedActivity

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

    df = pd.DataFrame([vars(a) for a in activities])
    df["date"] = pd.to_datetime(df["date"])

    # Daily aggregation for Performance Management Chart (PMC)
    daily = df.groupby("date")["training_stress"].sum().asfreq("D", fill_value=0)

    ctl, atl, tsb = compute_pmc_values(daily)

    daily_series = pd.DataFrame({"ctl": ctl, "atl": atl, "tsb": tsb}).reset_index()
    daily_series["date"] = daily_series["date"].dt.strftime("%Y-%m-%d")

    # Weekly aggregation
    df["week"] = df["date"].dt.to_period("W").dt.start_time
    weekly = (
        df
        .groupby("week")
        .agg({
            "duration_h": "sum",
            "training_stress": "sum",
            "distance_km": "sum",
            "elevation_gain": "sum",
        })
        .reset_index()
    )
    weekly["week"] = weekly["week"].dt.strftime("%Y-%m-%d")

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
        daily_series=daily_series.to_dict(orient="records"),
        weekly_series=weekly.to_dict(orient="records"),
        summary=summary,
        hr_intensity_distribution=_aggregate_hr_zones(df),
        power_intensity_distribution=_aggregate_power_zones(df),
        activity_type_distribution={str(k): int(v) for k, v in df["type"].value_counts().items()},
    )


def _aggregate_power_zones(df: pd.DataFrame) -> list[float]:
    """Aggregate the power zones.

    Returns:
        The time in seconds spent in each power zone.
    """
    valid_zones = df["power_zone_times"].dropna()
    num_zones = len(valid_zones.iloc[0])
    zones = [0.0] * num_zones
    for z_list in valid_zones:
        for i, val in enumerate(z_list):
            zones[i] += float(val["secs"])
    total = sum(zones)
    return [z / total if total > 0 else 0 for z in zones]


def _aggregate_hr_zones(df: pd.DataFrame, num_hr_zones: int = 7) -> list[float]:
    """Aggregate the HR zones.

    Returns:
        The time in seconds spent in each HR zone.
    """
    zones = [0] * num_hr_zones
    for z_list in df["hr_zone_times"].dropna():
        for i, val in enumerate(z_list):
            if i < num_hr_zones:
                zones[i] += val
    total: int = sum(zones)
    return [z / total if total > 0 else 0 for z in zones]


def compute_pmc_values(df_daily: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Computes the Performance Management Chart values using an exponentially weighted moving average (EWMA).

    Follows the definition from https://www.sciencetosport.com/monitoring-training-load/.

    Returns:
        Chronic Training Load (CTL), Acute Training Load (ATL) and Training Stress Balance (TSB).
    """
    alpha_ctl = 1 - math.exp(-1 / CHRONIC_TRAINING_LOAD_DAYS)
    alpha_atl = 1 - math.exp(-1 / ACUTE_TRAINING_LOAD_DAYS)
    ctl: pd.DataFrame = df_daily.ewm(alpha=alpha_ctl, adjust=False).mean()
    atl: pd.DataFrame = df_daily.ewm(alpha=alpha_atl, adjust=False).mean()
    tsb: pd.DataFrame = ctl - atl
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
