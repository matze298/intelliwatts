"""Tests for the metric registry."""

from unittest.mock import ANY, AsyncMock, MagicMock

import pytest

from app.planning.providers.interfaces import MetricProvider
from app.planning.providers.registry import MetricRegistry


def test_metric_registry_registration() -> None:
    """Tests that providers can be registered with the MetricRegistry."""
    # GIVEN: A fresh MetricRegistry and a mocked MetricProvider.
    registry = MetricRegistry()
    mock_provider = MagicMock(spec=MetricProvider)

    # WHEN: The provider is registered with the registry instance.
    registry.register(mock_provider)

    # THEN: The provider should be present in the registry's internal list and count should be 1.
    assert mock_provider in registry.providers
    assert len(registry.providers) == 1


def test_metric_registry_process_analysis() -> None:
    """Tests that the registry correctly processes analysis across all providers."""
    # GIVEN: A registry with two providers.
    registry = MetricRegistry()
    daily_df = MagicMock()

    provider1 = MagicMock(spec=MetricProvider)
    provider1.get_name.return_value = "p1"
    provider1.calculate.return_value = {"val": 1}
    provider1.get_dashboard_widget.return_value = MagicMock()

    provider2 = MagicMock(spec=MetricProvider)
    provider2.get_name.return_value = "p2"
    provider2.calculate.return_value = {"val": 2}
    provider2.get_dashboard_widget.return_value = None

    registry.register(provider1)
    registry.register(provider2)

    # WHEN: Running the analysis.
    results, widgets = registry.process_analysis(daily_df, client=None)

    # THEN: The results and widgets should be collected correctly.
    assert results == {"p1": {"val": 1}, "p2": {"val": 2}}
    assert len(widgets) == 1
    # provider_results is passed and accumulates
    provider1.calculate.assert_called_once_with(
        daily_df,
        client=None,
        provider_results=ANY,
        display_days=None,
    )
    provider2.calculate.assert_called_once_with(
        daily_df,
        client=None,
        provider_results=ANY,
        display_days=None,
    )


@pytest.mark.asyncio
async def test_metric_registry_combined_context() -> None:
    """Tests that the registry correctly combines context from multiple providers."""
    # GIVEN: A registry with three providers (two returning text, one returning an empty string).
    registry = MetricRegistry()
    results = {
        "p1": {"data": 1},
        "p2": {"data": 2},
        "p3": {"data": 3},
    }

    provider1 = MagicMock(spec=MetricProvider)
    provider1.get_name.return_value = "p1"
    provider1.provide_context = AsyncMock(return_value="Context 1")

    provider2 = MagicMock(spec=MetricProvider)
    provider2.get_name.return_value = "p2"
    provider2.provide_context = AsyncMock(return_value="Context 2")

    provider3 = MagicMock(spec=MetricProvider)
    provider3.get_name.return_value = "p3"
    provider3.provide_context = AsyncMock(return_value="")  # Should be ignored by the registry

    registry.register(provider1)
    registry.register(provider2)
    registry.register(provider3)

    # WHEN: Requesting combined context from all registered providers via the registry.
    combined_context = await registry.get_combined_context(results)

    # THEN: Only the non-empty contexts should be joined with double newlines.
    assert combined_context == "Context 1\n\nContext 2"
    provider1.provide_context.assert_called_once_with({"data": 1})
    provider2.provide_context.assert_called_once_with({"data": 2})
    provider3.provide_context.assert_called_once_with({"data": 3})


@pytest.mark.asyncio
async def test_metric_registry_specialist_context() -> None:
    """Tests that only specialist providers contribute to coach context."""
    # GIVEN a registry with one specialist and one regular provider.
    registry = MetricRegistry()
    results = {"specialist": {"data": 1}, "regular": {"data": 2}}
    specialist = MagicMock(spec=MetricProvider)
    specialist.get_name.return_value = "specialist"
    specialist.provide_coach_context = AsyncMock(return_value="Specialist Context")

    regular = MagicMock(spec=MetricProvider)
    regular.get_name.return_value = "regular"

    registry.register(specialist)
    registry.register(regular)

    # WHEN requesting the specialist context from the registry.
    context = await registry.get_specialist_context(results)

    # THEN only the specialist provider should contribute text.
    assert context == "Specialist Context"
    specialist.provide_coach_context.assert_awaited_once_with({"data": 1})
