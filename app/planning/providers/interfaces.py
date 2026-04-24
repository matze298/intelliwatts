"""Base classes for metric providers."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    import polars as pl

    from app.intervals.client import IntervalsClient

T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True)
class DashboardWidget:
    """Represents a widget on the athlete dashboard."""

    name: str
    title: str
    value: str | None = None
    trend: str | None = None
    trend_positive: bool | None = None
    custom_template: str | None = None
    data: dict[str, Any] | None = None


class MetricProvider(Protocol[T_co]):
    """Protocol for metric providers that contribute to the planning context."""

    def get_name(self) -> str:
        """Returns the unique name of the provider.

        Returns:
            The provider name.
        """
        ...

    def calculate(
        self,
        daily_df: pl.DataFrame,
        client: IntervalsClient | None = None,
        provider_results: dict[str, Any] | None = None,
    ) -> T_co:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            client: The Intervals.icu client.
            provider_results: Mapping of previous provider results.

        Returns:
            The calculation result.
        """
        ...

    async def provide_context(self, result: T_co) -> str:
        """Provides metric-specific context for the LLM.

        Args:
            result: The result from the calculate method.

        Returns:
            A formatted string containing the metric context.
        """
        ...

    def get_dashboard_widget(self, result: T_co, display_days: int | None = None) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.
            display_days: Optional number of days to display.

        Returns:
            The widget data or None if not applicable.
        """
        ...
