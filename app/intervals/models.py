"""Models for intervals analysis."""

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    import polars as pl

    from app.planning.providers.interfaces import DashboardWidget


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


class DailyRecordField(StrEnum):
    """Columns preserved in the joined daily analysis records."""

    TRAINING_STRESS = "training_stress"
    DURATION_H = "duration_h"
    DISTANCE_KM = "distance_km"
    TYPES = "types"
    ACTIVITY_DURATIONS = "activity_durations"
    ACTIVITY_TSS = "activity_tss"
    ACTIVITY_DISTANCES = "activity_distances"
    ACTIVITY_AVG_POWER = "activity_avg_power"
    ACTIVITY_AVG_HR = "activity_avg_hr"
    ACTIVITY_MAX_HR = "activity_max_hr"
    ACTIVITY_ELEVATION_GAIN = "activity_elevation_gain"
    ACTIVITY_FTP = "activity_ftp"
    HRV = "hrv"
    RESTING_HR = "resting_hr"
    SLEEP_SCORE = "sleep_score"
    SLEEP_QUALITY = "sleep_quality"
    FATIGUE = "fatigue"
    SORENESS = "soreness"
    STRESS = "stress"
    READINESS = "readiness"
    COMMENTS = "comments"


@dataclass(frozen=True)
class AnalysisResult:
    """Result of the sports science analysis."""

    provider_results: dict[str, Any] = field(default_factory=dict)
    widgets: list[DashboardWidget] = field(default_factory=list)
    daily_records: list[dict[str, Any]] = field(default_factory=list)

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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create a PMCResult from a dictionary.

        Args:
            data: The dictionary containing PMC data.

        Returns:
            A PMCResult instance.
        """
        return cls(
            ctl=data["ctl"],
            atl=data["atl"],
            tsb=data["tsb"],
        )
