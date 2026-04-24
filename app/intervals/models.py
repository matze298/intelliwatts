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
class AnalysisResult:
    """Result of the sports science analysis."""

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
