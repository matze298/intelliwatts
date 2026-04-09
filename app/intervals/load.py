"""Calculate the sports science analysis."""

from dataclasses import dataclass
from logging import getLogger
from typing import Any

import pandas as pd

from app.intervals.parser.activity import ParsedActivity

_LOGGER = getLogger(__name__)
CHRONIC_TRAINING_LOAD_DAYS = 42
ACUTE_TRAINING_LOAD_DAYS = 7


@dataclass
class TrainingLoad:
    """Training load."""

    chronic: float
    acute: float

    @property
    def training_stress_balance(self) -> float:
        """Compute the training stress balance."""
        return self.chronic - self.acute


@dataclass
class ActivitySummary:
    """Summary of activities."""

    total_duration_h: float
    total_distance_km: float
    total_elevation_gain: float
    total_calories: float
    total_training_stress: float
    activity_count: int


@dataclass
class AnalysisResult:
    """Result of the sports science analysis."""

    daily_series: list[dict[str, Any]]
    weekly_series: list[dict[str, Any]]
    summary: ActivitySummary
    hr_intensity_distribution: list[float]
    power_intensity_distribution: list[float]
    activity_type_distribution: dict[str, int]


NUM_ZONES = 7


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

    # Daily aggregation for PMC
    daily = df.groupby("date")["training_stress"].sum().asfreq("D", fill_value=0)

    ctl = daily.ewm(span=CHRONIC_TRAINING_LOAD_DAYS).mean()
    atl = daily.ewm(span=ACUTE_TRAINING_LOAD_DAYS).mean()
    tsb = ctl - atl

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

    # Intensity Distributions (Normalized)
    def aggregate_zones(col_name: str) -> list[float]:
        zones = [0] * NUM_ZONES
        for z_list in df[col_name].dropna():
            for i, val in enumerate(z_list):
                if i < NUM_ZONES:
                    zones[i] += val
        total: int = sum(zones)
        return [z / total if total > 0 else 0 for z in zones]

    hr_dist = aggregate_zones("hr_zone_times")
    power_dist = aggregate_zones("power_zone_times")

    # Activity types
    type_dist = df["type"].value_counts().to_dict()

    return AnalysisResult(
        daily_series=daily_series.to_dict(orient="records"),
        weekly_series=weekly.to_dict(orient="records"),
        summary=summary,
        hr_intensity_distribution=hr_dist,
        power_intensity_distribution=power_dist,
        activity_type_distribution=type_dist,
    )


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
