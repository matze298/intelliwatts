"""Performance Management Chart (PMC) metric provider."""

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

import polars as pl

from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class PMCResult:
    """Result of the PMC calculation."""

    dates: list[str]
    ctl: list[float]
    atl: list[float]
    tsb: list[float]


class PMCProvider(MetricProvider[PMCResult]):
    """Provides PMC (Fitness, Fatigue, Form) context."""

    _chronic_days = 42
    _acute_days = 7

    @override
    def get_name(self) -> str:
        """Returns the provider name.

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
    ) -> PMCResult:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The structured calculation result.
        """
        # Compute CTL, ATL using exponentially weighted moving averages
        alpha_ctl = 1 - math.exp(-1 / self._chronic_days)
        alpha_atl = 1 - math.exp(-1 / self._acute_days)

        pmc_df = daily_df.select([
            pl.col("date"),
            pl.col("training_stress").ewm_mean(alpha=alpha_ctl, adjust=False).alias("ctl"),
            pl.col("training_stress").ewm_mean(alpha=alpha_atl, adjust=False).alias("atl"),
        ]).with_columns((pl.col("ctl") - pl.col("atl")).alias("tsb"))

        return PMCResult(
            dates=pmc_df["date"].dt.strftime("%Y-%m-%d").to_list(),
            ctl=pmc_df["ctl"].to_list(),
            atl=pmc_df["atl"].to_list(),
            tsb=pmc_df["tsb"].to_list(),
        )

    @override
    async def provide_context(self, result: PMCResult) -> str:
        """Provides PMC context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the PMC context.
        """
        if not result.ctl:
            return "No fitness data available."

        last_ctl = result.ctl[-1]
        last_atl = result.atl[-1]
        last_tsb = result.tsb[-1]

        return (
            "Current Fitness (PMC):\n"
            f"- Fitness (CTL): {last_ctl:.1f}\n"
            f"- Fatigue (ATL): {last_atl:.1f}\n"
            f"- Form (TSB): {last_tsb:.1f}"
        )

    @override
    def get_dashboard_widget(self, result: PMCResult, display_days: int | None = None) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if not result.ctl:
            return None

        # Filter series for display if display_days is set
        dates = result.dates
        ctl = result.ctl
        atl = result.atl
        tsb = result.tsb

        if display_days:
            dates = dates[-display_days:]
            ctl = ctl[-display_days:]
            atl = atl[-display_days:]
            tsb = tsb[-display_days:]

        return DashboardWidget(
            name="pmc",
            title="Fitness Trend",
            custom_template="widgets/pmc_chart.html",
            data={
                "dates": dates,
                "ctl": ctl,
                "atl": atl,
                "tsb": tsb,
            },
        )
