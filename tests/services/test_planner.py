"""Unit tests for the planner service."""

from unittest.mock import MagicMock, patch

from app.models.user import User
from app.planning.llm import LLMResponse
from app.services.planner import generate_weekly_plan


@patch("app.services.planner.IntervalsClient")
@patch("app.services.planner.parse_activities")
@patch("app.services.planner.compute_load")
@patch("app.services.planner.build_weekly_summary")
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.llm_json_to_icu_txt")
def test_generate_weekly_plan(  # noqa: PLR0913, PLR0917
    mock_llm_json_to_icu_txt: MagicMock,
    mock_generate_plan: MagicMock,
    mock_build_weekly_summary: MagicMock,
    mock_compute_load: MagicMock,
    mock_parse_activities: MagicMock,
    mock_intervals_client: MagicMock,
) -> None:
    """Test the generate_weekly_plan function."""
    # GIVEN a mock user and mocked settings
    mock_user = User(
        id="1",
        email="test@example.com",
        hashed_password="hashed_password",  # noqa: S106
        iv="iv",
        salt="salt",
    )
    mock_settings = MagicMock()
    mock_settings.INTERVALS_API_KEY = "test_api_key"
    mock_settings.INTERVALS_ATHLETE_ID = "test_athlete_id"
    mock_settings.CACHE_INTERVALS_HOURS = 1
    mock_settings.weekly_sessions = 5
    mock_settings.weekly_hours = 10
    mock_settings.LANGUAGE_MODEL = "test_model"

    # GIVEN mocked raw activities, parsed activities, load, summary, plan, and plan text
    mock_raw_activities = [{"id": "activity1"}]
    mock_intervals_client.return_value.activities.return_value = mock_raw_activities

    mock_parsed_activities = [MagicMock()]
    mock_parse_activities.return_value = mock_parsed_activities

    mock_load = 100
    mock_compute_load.return_value = mock_load

    mock_summary = "Weekly summary"
    mock_build_weekly_summary.return_value = mock_summary

    mock_plan_json = '{"plan": "test plan"}'
    mock_generate_plan.return_value = LLMResponse(
        plan=mock_plan_json, prompt=[{"   role": "user", "content": "test prompt"}]
    )

    mock_plan_txt = "icu workout"
    mock_llm_json_to_icu_txt.return_value = mock_plan_txt

    # WHEN generating the weekly plan
    result = generate_weekly_plan(mock_user, mock_settings)

    # THEN the IntervalsClient and all functions are called with correct parameters
    mock_intervals_client.assert_called_once_with("test_api_key", "test_athlete_id", 1)
    mock_intervals_client.return_value.activities.assert_called_once()
    mock_parse_activities.assert_called_once_with(mock_raw_activities)
    mock_compute_load.assert_called_once_with(mock_parsed_activities)
    mock_build_weekly_summary.assert_called_once_with(
        mock_parsed_activities,
        mock_load,
        weekly_sessions=5,
        weekly_hours=10,
    )
    mock_generate_plan.assert_called_once_with(summary=mock_summary, language_model="test_model", user=mock_user)
    mock_llm_json_to_icu_txt.assert_called_once_with(mock_plan_json)

    # THEN the result contains the expected plan and summary
    expected_plan = (
        '{"plan": "test plan"}\n\n## intervals.icu workout file (txt)\n\n'
        """```text

icu workout
```"""
    )
    assert result["plan"] == expected_plan
    assert result["summary"] == mock_summary
