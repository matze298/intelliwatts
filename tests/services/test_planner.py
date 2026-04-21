"""Unit tests for the planner service."""

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from unittest.mock import ANY, MagicMock, patch

import pytest
from sqlmodel import Session, create_engine, select

from app.models.plan import SQLModel, TrainingPhase, TrainingPlan
from app.models.user import User
from app.planning.llm import LLMResponse, LLMRole
from app.planning.summary import PlanningConstraints
from app.services.planner import (
    PlanData,
    generate_weekly_plan,
    get_or_create_active_phase,
    save_training_plan,
    update_training_plan,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture
def session() -> Generator[Session]:
    """Provides a clean in-memory database session.

    Yields:
        The database session.
    """
    engine: Engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_get_or_create_active_phase(session: Session) -> None:
    """Test get_or_create_active_phase creates default if none exists."""
    # GIVEN a user ID
    user_id = uuid.uuid4()

    # WHEN getting or creating an active phase
    phase = get_or_create_active_phase(session, user_id)

    # THEN it should create a default active phase
    assert phase.user_id == user_id
    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP (Default)"

    # WHEN getting it again
    phase2 = get_or_create_active_phase(session, user_id)

    # THEN it should return the same phase
    assert phase2.id == phase.id


def test_save_training_plan_overwrite(session: Session) -> None:
    """Test save_training_plan overwrites existing plan for the week."""
    # GIVEN an active phase and a week start date
    user_id = uuid.uuid4()
    phase = get_or_create_active_phase(session, user_id)
    week_start = date(2026, 4, 20)

    # WHEN saving an initial plan
    data = PlanData(raw_content="Old Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # THEN it should be stored in the database
    statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase.id)
    plan = session.exec(statement).one()
    assert plan.raw_content == "Old Content"

    # WHEN saving a new plan for the same week
    data = PlanData(raw_content="New Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # THEN it should overwrite the existing plan
    plan = session.exec(statement).one()
    assert plan.raw_content == "New Content"


@patch("app.services.planner.IntervalsClient")
@patch("app.services.planner.parse_activities")
@patch("app.services.planner.parse_wellness_list")
@patch("app.services.planner.parse_power_curves")
@patch("app.services.planner.compute_athlete_status")
@patch("app.services.planner.build_weekly_summary")
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.llm_json_to_icu_txt")
def test_generate_weekly_plan(  # noqa: PLR0913, PLR0917, PLR0915, PLR0914
    mock_llm_json_to_icu_txt: MagicMock,
    mock_generate_plan: MagicMock,
    mock_build_weekly_summary: MagicMock,
    mock_compute_athlete_status: MagicMock,
    mock_parse_power_curves: MagicMock,
    mock_parse_wellness_list: MagicMock,
    mock_parse_activities: MagicMock,
    mock_intervals_client: MagicMock,
) -> None:
    """Test the generate_weekly_plan function."""
    # GIVEN a mock user and mocked settings
    mock_user = User(
        id=uuid.uuid4(),
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
    mock_raw_power_curves = {"list": [{"id": "90d"}]}
    mock_intervals_client.return_value.power_curves.return_value = mock_raw_power_curves

    mock_parsed_activities = [MagicMock()]
    mock_parse_activities.return_value = mock_parsed_activities
    mock_parsed_wellness = [MagicMock()]
    mock_parse_wellness_list.return_value = mock_parsed_wellness
    mock_parsed_power_curves = [MagicMock()]
    mock_parse_power_curves.return_value = mock_parsed_power_curves

    # GIVEN mocked athlete status
    mock_status = MagicMock()
    mock_status.load.chronic = 50
    mock_status.load.acute = 60
    mock_status.wellness = {"hrv_7d": 70}
    mock_status.ftp_trajectory = {"change_pct": 2.5}
    mock_status.power_curve = {"peak_5m": 350}
    mock_compute_athlete_status.return_value = mock_status

    mock_summary = "Weekly summary"
    mock_build_weekly_summary.return_value = mock_summary

    mock_plan_json = '{"plan": "test plan"}'
    mock_generate_plan.return_value = LLMResponse(
        plan=mock_plan_json, prompt=[{"role": "user", "content": "test prompt"}]
    )

    mock_plan_txt = "icu workout"
    mock_llm_json_to_icu_txt.return_value = mock_plan_txt

    # WHEN generating the weekly plan with wellness
    with patch("app.services.planner.Session"):
        result = generate_weekly_plan(mock_user, mock_settings, use_wellness=True)

    # THEN the IntervalsClient and all functions are called with correct parameters
    mock_intervals_client.assert_called_once_with("test_api_key", "test_athlete_id", session=ANY)
    mock_intervals_client.return_value.activities.assert_called_once_with(days=120)
    mock_intervals_client.return_value.wellness.assert_called_once_with(days=120)
    mock_intervals_client.return_value.power_curves.assert_called_once_with(curves="90d")
    mock_parse_activities.assert_called_once_with(mock_raw_activities)
    mock_parse_wellness_list.assert_called_once_with(mock_raw_wellness)
    mock_parse_power_curves.assert_called_once_with(mock_raw_power_curves)
    mock_compute_athlete_status.assert_called_once_with(
        mock_parsed_activities, wellness_data=mock_parsed_wellness, power_curve=mock_parsed_power_curves
    )

    # THEN build_weekly_summary is called with correct parameters
    mock_build_weekly_summary.assert_called_once()
    args, kwargs = mock_build_weekly_summary.call_args
    assert args[0] == mock_parsed_activities
    assert args[1].chronic == 50
    assert args[1].acute == 60
    assert kwargs["constraints"] == PlanningConstraints(weekly_hours=10, weekly_sessions=5)
    assert kwargs["wellness_summary"] == {"hrv_7d": 70}
    assert kwargs["ftp_trajectory"] == {"change_pct": 2.5}
    assert kwargs["power_curve"] == {"peak_5m": 350}

    # THEN generate_plan is called with the messages
    mock_generate_plan.assert_called_once()
    passed_messages = mock_generate_plan.call_args.kwargs["messages"]
    assert len(passed_messages) == 2
    assert passed_messages[0]["role"] == LLMRole.SYSTEM
    assert "Weekly summary" in passed_messages[1]["content"]
    assert mock_generate_plan.call_args.kwargs["language_model"] == "test_model"
    assert mock_generate_plan.call_args.kwargs["user"] == mock_user

    # THEN the result contains the expected plan and summary
    assert result["summary"] == mock_summary


@patch("app.services.planner.IntervalsClient")
@patch("app.services.planner.parse_activities")
@patch("app.services.planner.parse_power_curves")
@patch("app.services.planner.compute_athlete_status")
@patch("app.services.planner.build_weekly_summary")
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.llm_json_to_icu_txt")
def test_generate_weekly_plan_no_wellness(  # noqa: PLR0913, PLR0917
    mock_icu_txt: MagicMock,
    mock_generate_plan: MagicMock,
    mock_build_weekly_summary: MagicMock,
    mock_compute_athlete_status: MagicMock,
    mock_parse_power_curves: MagicMock,
    mock_parse_activities: MagicMock,
    mock_intervals_client: MagicMock,
) -> None:
    """Test the generate_weekly_plan function without wellness data."""
    # GIVEN a mock user and mocked settings
    mock_user = User(
        id=uuid.uuid4(),
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
    mock_intervals_client.return_value.power_curves.return_value = {"list": []}
    mock_parse_activities.return_value = []
    mock_parse_power_curves.return_value = []

    # GIVEN mocked status result without wellness
    mock_status = MagicMock()
    mock_status.load.chronic = 0
    mock_status.load.acute = 0
    mock_status.wellness = None
    mock_status.ftp_trajectory = None
    mock_status.power_curve = None
    mock_compute_athlete_status.return_value = mock_status

    mock_generate_plan.return_value = LLMResponse(plan="{}", prompt=[])
    mock_icu_txt.return_value = ""

    # WHEN generating the weekly plan without wellness
    with patch("app.services.planner.Session"):
        generate_weekly_plan(mock_user, mock_settings, use_wellness=False)

    # THEN wellness client method is NOT called
    mock_intervals_client.return_value.wellness.assert_not_called()

    # THEN compute_athlete_status is called with wellness_data=None
    mock_compute_athlete_status.assert_called_once_with([], wellness_data=None, power_curve=[])

    # THEN build_weekly_summary is called with wellness_summary=None
    assert mock_build_weekly_summary.call_args.kwargs["wellness_summary"] is None


@patch("app.services.planner.generate_plan")
def test_update_training_plan_uses_history(mock_generate_plan: MagicMock, session: Session) -> None:
    """Test update_training_plan retrieves history and calls LLM with it."""
    # GIVEN a user and an existing training plan with prompt history
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106
    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Test",
        start_date=date(2026, 4, 20),
        end_date=date(2026, 5, 17),
    )
    session.add(phase)
    session.commit()

    monday = date(2026, 4, 20)
    initial_history = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    data = PlanData(raw_content="Initial Plan", workout_data=[], prompt_history=initial_history)
    save_training_plan(session, phase.id, monday, data)

    # GIVEN a mocked LLM response for the update
    mock_llm_response = MagicMock()
    mock_llm_response.plan = "Updated Plan ###JSON_START### [] ###JSON_END###"
    mock_llm_response.prompt = [
        *initial_history,
        {"role": "user", "content": "make it harder"},
        {"role": "assistant", "content": "ok"},
    ]
    mock_generate_plan.return_value = mock_llm_response

    # WHEN updating the training plan with feedback
    with (
        patch("app.services.planner.Session", return_value=session),
        patch("app.services.planner.get_monday", return_value=monday),
        patch("app.services.planner.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = datetime(2026, 4, 21, tzinfo=UTC)
        update_training_plan(user, "make it harder")

    # THEN generate_plan should be called with the extended message history
    mock_generate_plan.assert_called_once()
    passed_messages = mock_generate_plan.call_args.kwargs["messages"]
    assert len(passed_messages) == 3
    assert passed_messages[2]["content"] == "make it harder"

    # THEN the plan and its history should be updated in the database
    plan = session.exec(select(TrainingPlan)).one()
    assert "Updated Plan" in plan.raw_content
    assert len(plan.prompt_history) == 4
