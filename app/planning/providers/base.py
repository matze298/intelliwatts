"""Base classes for metric providers."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.intervals.analysis import AnalysisResult
    from app.intervals.client import IntervalsClient


class MetricProvider(Protocol):
    """Protocol for metric providers that contribute to the planning context."""

    def get_name(self) -> str:
        """Returns the unique name of the provider.

        Returns:
            str: The provider name.
        """
        ...

    async def provide_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult) -> str:
        """Provides metric-specific context for the LLM.

        Args:
            client: The Intervals.icu client.
            days: Number of past days to analyze.
            analysis: The pre-computed analysis result.

        Returns:
            str: A formatted string containing the metric context.
        """
        ...
