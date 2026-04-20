"""Unit tests for the planner service."""

from unittest.mock import MagicMock, patch

from app.models.user import User
from app.planning.llm import LLMResponse
from app.planning.summary import PlanningConstraints
from app.services.planner import generate_weekly_plan


@patch("app.services.planner.IntervalsClient")
@patch("app.services.planner.parse_activities")
@patch("app.services.planner.parse_wellness_list")
@patch("app.services.planner.compute_analysis")
@patch("app.services.planner.build_weekly_summary")
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.llm_json_to_icu_txt")
def test_generate_weekly_plan(  # noqa: PLR0913, PLR0917
    mock_llm_json_to_icu_txt: MagicMock,
    mock_generate_plan: MagicMock,
    mock_build_weekly_summary: MagicMock,
    mock_compute_analysis: MagicMock,
    mock_parse_wellness_list: MagicMock,
    mock_parse_activities: MagicMock,
    mock_intervals_client: MagicMock,
) -> None:
    """Test the generate_weekly_plan function."""
    # GIVEN a mock user and mocked settings
    mock_user = User(
        id=MagicMock(),
        email="test@example.com",
        password_hash="hashed_password",  # noqa: S106
    )
    mock_settings = MagicMock()
    mock_settings.INTERVALS_API_KEY = "test_api_key"
    mock_settings.INTERVALS_ATHLETE_ID = "test_athlete_id"
    mock_settings.CACHE_INTERVALS_HOURS = 1
    mock_settings.ANALYSIS_DAYS = 120
    mock_settings.weekly_sessions = 5
    mock_settings.weekly_hours = 10
    mock_settings.LANGUAGE_MODEL = "test_model"

    # GIVEN mocked raw data and parsed data
    mock_raw_activities = [{"id": "activity1"}]
    mock_intervals_client.return_value.activities.return_value = mock_raw_activities
    mock_raw_wellness = [{"id": "wellness1"}]
    mock_intervals_client.return_value.wellness.return_value = mock_raw_wellness

    mock_parsed_activities = [MagicMock()]
    mock_parse_activities.return_value = mock_parsed_activities
    mock_parsed_wellness = [MagicMock()]
    mock_parse_wellness_list.return_value = mock_parsed_wellness

    # GIVEN mocked analysis result
    mock_analysis = MagicMock()
    mock_analysis.daily_series = [{"ctl": 50, "atl": 60}]
    mock_analysis.wellness_summary = {"hrv_7d": 70}
    mock_compute_analysis.return_value = mock_analysis

    mock_summary = "Weekly summary"
    mock_build_weekly_summary.return_value = mock_summary

    mock_plan_json = '{"plan": "test plan"}'
    mock_generate_plan.return_value = LLMResponse(
        plan=mock_plan_json, prompt=[{"role": "user", "content": "test prompt"}]
    )

    mock_plan_txt = "icu workout"
    mock_llm_json_to_icu_txt.return_value = mock_plan_txt

    # WHEN generating the weekly plan with wellness
    result = generate_weekly_plan(mock_user, mock_settings, use_wellness=True)

    # THEN the IntervalsClient and all functions are called with correct parameters
    mock_intervals_client.assert_called_once_with("test_api_key", "test_athlete_id", 1)
    mock_intervals_client.return_value.activities.assert_called_once_with(days=120)
    mock_intervals_client.return_value.wellness.assert_called_once_with(days=120)
    mock_parse_activities.assert_called_once_with(mock_raw_activities)
    mock_parse_wellness_list.assert_called_once_with(mock_raw_wellness)
    mock_compute_analysis.assert_called_once_with(mock_parsed_activities, wellness_data=mock_parsed_wellness)

    # Verify build_weekly_summary call (especially the load and constraints)
    mock_build_weekly_summary.assert_called_once()
    args, kwargs = mock_build_weekly_summary.call_args
    assert args[0] == mock_parsed_activities
    # load should be a TrainingLoad object with ctl=50, atl=60
    assert args[1].chronic == 50
    assert args[1].acute == 60
    assert kwargs["constraints"] == PlanningConstraints(weekly_hours=10, weekly_sessions=5)
    assert kwargs["wellness_summary"] == {"hrv_7d": 70}

    mock_generate_plan.assert_called_once_with(summary=mock_summary, language_model="test_model", user=mock_user)
    mock_llm_json_to_icu_txt.assert_called_once_with(mock_plan_json)

    # THEN the result contains the expected plan and summary
    assert result["summary"] == mock_summary


@patch("app.services.planner.IntervalsClient")
@patch("app.services.planner.parse_activities")
@patch("app.services.planner.compute_analysis")
@patch("app.services.planner.build_weekly_summary")
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.llm_json_to_icu_txt")
def test_generate_weekly_plan_no_wellness(  # noqa: PLR0913, PLR0917
    mock_icu_txt: MagicMock,
    mock_generate_plan: MagicMock,
    mock_build_weekly_summary: MagicMock,
    mock_compute_analysis: MagicMock,
    mock_parse_activities: MagicMock,
    mock_intervals_client: MagicMock,
) -> None:
    """Test the generate_weekly_plan function without wellness data."""
    # GIVEN a mock user and mocked settings
    mock_user = User(
        id=MagicMock(),
        email="test2@example.com",
        password_hash="hashed_password",  # noqa: S106
    )
    mock_settings = MagicMock()
    mock_settings.INTERVALS_API_KEY = "test_api_key"
    mock_settings.INTERVALS_ATHLETE_ID = "test_athlete_id"
    mock_settings.CACHE_INTERVALS_HOURS = 1
    mock_settings.ANALYSIS_DAYS = 120
    mock_settings.weekly_sessions = 5
    mock_settings.weekly_hours = 10
    mock_settings.LANGUAGE_MODEL = "test_model"

    # GIVEN mocked raw data and parsed data
    mock_intervals_client.return_value.activities.return_value = []
    mock_parse_activities.return_value = []

    # GIVEN mocked analysis result without wellness
    mock_analysis = MagicMock()
    mock_analysis.daily_series = []
    mock_analysis.wellness_summary = None
    mock_compute_analysis.return_value = mock_analysis

    mock_generate_plan.return_value = LLMResponse(plan="{}", prompt=[])
    mock_icu_txt.return_value = ""

    # WHEN generating the weekly plan without wellness
    generate_weekly_plan(mock_user, mock_settings, use_wellness=False)

    # THEN wellness client method is NOT called
    mock_intervals_client.return_value.wellness.assert_not_called()
    # AND compute_analysis is called with wellness_data=None
    mock_compute_analysis.assert_called_once_with([], wellness_data=None)
    # AND build_weekly_summary is called with wellness_summary=None
    assert mock_build_weekly_summary.call_args.kwargs["wellness_summary"] is None
