"""Power curve metric provider."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from app.intervals.parser.power_curve import parse_power_curves
from app.planning.providers.interfaces import DashboardWidget, MetricProvider

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient


@dataclass(frozen=True)
class PowerCurveResult:
    """Result of the power curve calculation."""

    peak_1s: int | None
    peak_15s: int | None
    peak_1m: int | None
    peak_5m: int | None
    peak_20m: int | None
    peak_60m: int | None
    # New fields for the heatmap
    recent_90d: list[dict[str, int]] | None = None
    season: list[dict[str, int]] | None = None
    all_time: list[dict[str, int]] | None = None


class PowerCurveProvider(MetricProvider[PowerCurveResult | None]):
    """Provides power curve context."""

    is_specialist = True

    @override
    def get_name(self) -> str:
        """Returns the provider name.

        Returns:
            The provider name.
        """
        return "power_curve"

    @override
    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
        display_days: int | None = None,
    ) -> PowerCurveResult | None:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.
            display_days: Optional number of days to display.

        Returns:
            The structured calculation result or None if no data available.
        """
        # Fetch power curves directly using client in a single call
        if client is None:
            return None

        # Fetch all requested curves in one go
        raw_curves = client.power_curves(curves="90d,s0,all")
        parsed_curves = parse_power_curves(raw_curves)

        if not parsed_curves:
            return None

        # Map curves by their ID for easy access
        curve_map = {c.id: c for c in parsed_curves}

        c_90d = curve_map.get("90d")
        c_season = curve_map.get("s0")
        c_all = curve_map.get("all")

        if not c_90d:
            return None

        return PowerCurveResult(
            peak_1s=c_90d.get_watts(1),
            peak_15s=c_90d.get_watts(15),
            peak_1m=c_90d.get_watts(60),
            peak_5m=c_90d.get_watts(300),
            peak_20m=c_90d.get_watts(1200),
            peak_60m=c_90d.get_watts(3600),
            recent_90d=c_90d.to_list(),
            season=c_season.to_list() if c_season else None,
            all_time=c_all.to_list() if c_all else None,
        )

    @override
    async def provide_context(self, result: PowerCurveResult | None) -> str:
        """Provides power curve context.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the power curve context.
        """
        if result is None:
            return "No power curve data available."

        return (
            "Season Peak Power:\n"
            f"- 1s: {result.peak_1s or '-'}W\n"
            f"- 15s: {result.peak_15s or '-'}W\n"
            f"- 1m: {result.peak_1m or '-'}W\n"
            f"- 5m: {result.peak_5m or '-'}W\n"
            f"- 20m: {result.peak_20m or '-'}W\n"
            f"- 60m: {result.peak_60m or '-'}W"
        )

    async def provide_coach_context(self, result: PowerCurveResult | None) -> str:
        """Provides power curve context for the coach prompt.

        Returns:
            The power curve prompt context.
        """
        return await self.provide_context(result)

    @override
    def get_dashboard_widget(
        self, result: PowerCurveResult | None, display_days: int | None = None
    ) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The dashboard widget.
        """
        if result is None:
            return None

        return DashboardWidget(
            name="power_curve",
            title="Critical Power Heatmap",
            custom_template="widgets/power_curve_chart.html",
            data={
                "recent_90d": result.recent_90d,
                "season": result.season,
                "all_time": result.all_time,
                "peak_20m": result.peak_20m,
            },
        )
