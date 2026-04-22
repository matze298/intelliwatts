"""PMC (Performance Management Chart) metric provider."""

import math
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient

CHRONIC_TRAINING_LOAD_DAYS = 42
ACUTE_TRAINING_LOAD_DAYS = 7


@dataclass(frozen=True)
class PMCResult:
    """Result of the PMC calculation."""

    ctl: list[float]
    atl: list[float]
    tsb: list[float]
    dates: list[str]


class PMCProvider(MetricProvider[PMCResult]):
    """Provides PMC-related metrics (CTL, ATL, TSB)."""

    @override
    def get_name(self) -> str:
        """Returns the unique name of the provider.

        Returns:
            The provider name.
        """
        return "pmc"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        wellness_summary: dict[str, Any] | None = None,
        ftp_trajectory: dict[str, Any] | None = None,
        power_curve: dict[str, Any] | None = None,
    ) -> PMCResult:
        """Computes the PMC values (CTL, ATL, TSB).

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            wellness_summary: Legacy wellness summary from analysis.py.
            ftp_trajectory: Legacy FTP trajectory from analysis.py.
            power_curve: Legacy power curve summary from analysis.py.

        Returns:
            Dictionary containing lists of CTL, ATL, TSB values and dates.
        """
        if daily_df.is_empty():
            return PMCResult(ctl=[], atl=[], tsb=[], dates=[])

        alpha_ctl = 1 - math.exp(-1 / CHRONIC_TRAINING_LOAD_DAYS)
        alpha_atl = 1 - math.exp(-1 / ACUTE_TRAINING_LOAD_DAYS)

        # Use EWM from Polars
        ctl = daily_df.select(pl.col("training_stress").ewm_mean(alpha=alpha_ctl, adjust=False)).to_series().to_list()
        atl = daily_df.select(pl.col("training_stress").ewm_mean(alpha=alpha_atl, adjust=False)).to_series().to_list()

        # Calculate TSB
        tsb = [c - a for c, a in zip(ctl, atl, strict=True)]
        dates = daily_df["date"].dt.strftime("%Y-%m-%d").to_list()

        return PMCResult(
            ctl=ctl,
            atl=atl,
            tsb=tsb,
            dates=dates,
        )

    @override
    async def provide_context(self, result: PMCResult) -> str:
        """Provides PMC-specific context for the LLM.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the PMC context (currently empty).
        """
        return ""

    @override
    def get_dashboard_widget(self, result: PMCResult) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.

        Returns:
            The dashboard widget.
        """
        return DashboardWidget(
            name="pmc",
            title="Fitness Trend",
            custom_template="widgets/pmc_chart.html",
            data=asdict(result),
        )
