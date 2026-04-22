"""Base classes for metric providers."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import polars as pl


@dataclass(frozen=True)
class DashboardWidget:
    """Represents a widget on the athlete dashboard."""

    name: str
    title: str
    value: str | None = None
    trend: str | None = None
    trend_positive: bool | None = None
    custom_template: str | None = None
    data: dict[str, object] | None = None


class MetricProvider(Protocol):
    """Protocol for metric providers that contribute to the planning context."""

    def get_name(self) -> str:
        """Returns the unique name of the provider.

        Returns:
            str: The provider name.
        """
        ...

    def calculate(self, daily_df: pl.DataFrame, **kwargs: object) -> object:
        """Perform calculations on raw data and return a structured result.

        Args:
            daily_df: Polars DataFrame containing daily wellness/activity data.
            **kwargs: Additional provider-specific arguments.

        Returns:
            object: The calculation result.
        """
        ...

    async def provide_context(self, result: object) -> str:
        """Provides metric-specific context for the LLM.

        Args:
            result: The result from the calculate method.

        Returns:
            str: A formatted string containing the metric context.
        """
        ...

    def get_dashboard_widget(self, result: object) -> DashboardWidget | None:
        """Format the calculation result for the dashboard.

        Args:
            result: The result from the calculate method.

        Returns:
            DashboardWidget | None: The widget data or None if not applicable.
        """
        ...
