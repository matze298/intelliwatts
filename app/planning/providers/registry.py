"""Registry for managing and executing metric providers."""

from typing import TYPE_CHECKING

from app.planning.providers.activity import ActivityProvider
from app.planning.providers.ftp_trajectory import FTPTrajectoryProvider
from app.planning.providers.power_curve import PowerCurveProvider
from app.planning.providers.resting_hr import RestingHRTrendProvider
from app.planning.providers.wellness import WellnessProvider

if TYPE_CHECKING:
    from app.intervals.analysis import AnalysisResult
    from app.intervals.client import IntervalsClient
    from app.planning.providers.base import MetricProvider


class MetricRegistry:
    """Registry that holds all active metric providers."""

    def __init__(self) -> None:
        """Initializes an empty registry."""
        self.providers: list[MetricProvider] = []

    def register(self, provider: MetricProvider) -> None:
        """Registers a new provider.

        Args:
            provider: The provider instance to register.
        """
        self.providers.append(provider)

    async def get_combined_context(self, client: IntervalsClient, days: int, analysis: AnalysisResult) -> str:
        """Collects and combines context from all registered providers.

        Args:
            client: The Intervals.icu client.
            days: Number of past days to analyze.
            analysis: The pre-computed analysis result.

        Returns:
            str: Combined context string from all providers.
        """
        contexts = []
        for provider in self.providers:
            context = await provider.provide_context(client, days, analysis=analysis)
            if context:
                contexts.append(context)
        return "\n\n".join(contexts)


# Global registry instance
registry = MetricRegistry()
registry.register(ActivityProvider())
registry.register(WellnessProvider())
registry.register(PowerCurveProvider())
registry.register(RestingHRTrendProvider())
registry.register(FTPTrajectoryProvider())
