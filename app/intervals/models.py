"""Models for intervals analysis."""

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

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
