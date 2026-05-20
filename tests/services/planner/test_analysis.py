"""Tests for planner analysis loading helpers."""

from unittest.mock import MagicMock, patch

from app.services.planner.analysis import get_analysis


@patch("app.services.planner.analysis.compute_analysis")
@patch("app.services.planner.analysis.parse_activities")
@patch("app.services.planner.analysis.parse_wellness_list")
def test_get_analysis_calls_interval_parsers(
    mock_parse_wellness_list: MagicMock,
    mock_parse_activities: MagicMock,
    mock_compute_analysis: MagicMock,
) -> None:
    """The analysis wrapper should load and forward all interval data."""
    # GIVEN: An intervals client and mocked parser / analysis functions.
    client = MagicMock()
    raw_activities = [{"id": "activity-1"}]
    raw_wellness = [{"id": "wellness-1"}]
    client.activities.return_value = raw_activities
    client.wellness.return_value = raw_wellness
    parsed_activities = ["parsed activities"]
    parsed_wellness = ["parsed wellness"]
    mock_parse_activities.return_value = parsed_activities
    mock_parse_wellness_list.return_value = parsed_wellness
    analysis_result = MagicMock()
    mock_compute_analysis.return_value = analysis_result

    # WHEN: Loading analysis with a shorter requested window.
    result = get_analysis(client, 30)

    # THEN: The wrapper should enforce the minimum lookback and delegate parsing.
    assert result is analysis_result
    client.activities.assert_called_once_with(days=42)
    client.wellness.assert_called_once_with(days=42)
    mock_parse_activities.assert_called_once_with(raw_activities)
    mock_parse_wellness_list.assert_called_once_with(raw_wellness)
    mock_compute_analysis.assert_called_once_with(
        parsed_activities,
        wellness_data=parsed_wellness,
        client=client,
    )
