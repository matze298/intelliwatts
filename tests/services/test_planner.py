"""Unit tests for the planner service."""

import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session, create_engine, select

from app.models.plan import (
    LongTermPlanArtifact,
    LongTermPlanBlock,
    LongTermPlanStructuredData,
    SQLModel,
    TrainingPhase,
    TrainingPlan,
)
from app.models.user import User
from app.planning.llm import LLMResponse
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
    # GIVEN: A user ID and a fresh session.
    user_id = uuid.uuid4()

    # WHEN: Getting or creating an active phase.
    phase = get_or_create_active_phase(session, user_id)

    # THEN: It should create a default active phase.
    assert phase.user_id == user_id
    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP (Default)"

    # WHEN: Getting it again.
    phase2 = get_or_create_active_phase(session, user_id)

    # THEN: It should return the same phase.
    assert phase2.id == phase.id


def test_save_training_plan_overwrite(session: Session) -> None:
    """Test save_training_plan overwrites existing plan for the week."""
    # GIVEN: An active phase and a week start date.
    user_id = uuid.uuid4()
    phase = get_or_create_active_phase(session, user_id)
    week_start = date(2026, 4, 20)

    # WHEN: Saving an initial plan.
    data = PlanData(raw_content="Old Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # THEN: It should be stored in the database.
    statement = select(TrainingPlan).where(TrainingPlan.phase_id == phase.id)
    plan = session.exec(statement).one()
    assert plan.raw_content == "Old Content"

    # WHEN: Saving a new plan for the same week.
    data = PlanData(raw_content="New Content", workout_data=[], prompt_history=[])
    save_training_plan(session, phase.id, week_start, data)

    # THEN: It should overwrite the existing plan.
    plan = session.exec(statement).one()
    assert plan.raw_content == "New Content"


@patch("app.services.planner.IntervalsClient")
@patch("app.services.planner.stage_workout_delivery")
@patch("app.services.planner.registry")
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.derive_weekly_brief")
@patch("app.services.planner.get_current_long_term_plan_artifact")
@patch("app.services.planner.get_or_create_active_phase")
@patch("app.services.planner.llm_json_to_icu_txt")
@patch("app.services.planner.user_prompt")
@pytest.mark.asyncio
async def test_generate_weekly_plan(  # noqa: PLR0913, PLR0917
    mock_user_prompt: MagicMock,
    mock_llm_json_to_icu_txt: MagicMock,
    mock_get_active_phase: MagicMock,
    mock_get_current_artifact: MagicMock,
    mock_derive_weekly_brief: MagicMock,
    mock_generate_plan: MagicMock,
    mock_registry: MagicMock,
    mock_stage_workout_delivery: MagicMock,
    mock_intervals_client: MagicMock,
) -> None:
    """Test the generate_weekly_plan function."""
    # GIVEN: A mock user and mocked settings.
    mock_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed_password",  # noqa: S106
        weekly_hours=10.0,
        weekly_sessions=5,
    )

    mock_settings = MagicMock()
    mock_settings.INTERVALS_API_KEY = "test_api_key"
    mock_settings.INTERVALS_ATHLETE_ID = "test_athlete_id"
    mock_settings.CACHE_INTERVALS_HOURS = 1
    mock_settings.ANALYSIS_DAYS = 120
    mock_settings.weekly_sessions = 5
    mock_settings.weekly_hours = 10
    mock_settings.LANGUAGE_MODEL = "test_model"

    mock_registry.get_combined_context = AsyncMock(return_value="Registry context")
    mock_user_prompt.return_value = "Formatted prompt"
    mock_generate_plan.return_value = LLMResponse(plan="test plan", prompt=[{"role": "user", "content": "test prompt"}])
    mock_llm_json_to_icu_txt.return_value = "icu workout"
    mock_derive_weekly_brief.return_value = "Weekly Brief:\n- Goal: Peak for hill climb\n- Current Block: Build"
    mock_phase = TrainingPhase(
        user_id=mock_user.id,
        primary_goal="Peak for hill climb",
        start_date=date(2026, 5, 5),
        end_date=date(2026, 8, 1),
        target_date=date(2026, 8, 1),
        status="active",
    )
    mock_get_active_phase.return_value = mock_phase
    blocks: list[LongTermPlanBlock] = [{"name": "Build", "focus": "Goal-specific workload", "weeks": 4}]
    structured_data: LongTermPlanStructuredData = {
        "goal": "Peak for hill climb",
        "start_date": "2026-05-05",
        "target_date": "2026-08-01",
        "duration_weeks": 4,
        "blocks": blocks,
    }
    mock_get_current_artifact.return_value = LongTermPlanArtifact(
        phase_id=mock_phase.id,
        structured_data=structured_data,
        summary_markdown="# Long-term plan",
        prompt_history=[],
    )

    # WHEN: Generating the weekly plan for a selected future week.
    target_week_start = date(2026, 6, 1)
    mock_analysis = MagicMock()
    mock_analysis.provider_results = {"activity": {}}
    with (
        patch("app.services.planner.Session"),
        patch("app.services.planner._get_analysis", return_value=mock_analysis),
    ):
        result = await generate_weekly_plan(mock_user, mock_settings, week_start=target_week_start)

    # THEN: The registry and LLM should be called with correct data.
    mock_intervals_client.assert_called_once_with("test_api_key", "test_athlete_id", session=ANY)
    mock_registry.get_combined_context.assert_called_once_with(mock_analysis.provider_results)
    mock_derive_weekly_brief.assert_called_once()
    assert mock_derive_weekly_brief.call_args.kwargs["week_start"] == target_week_start
    mock_user_prompt.assert_called_once()
    assert "Weekly Brief:" in mock_user_prompt.call_args[0][0]
    assert "Goal: Peak for hill climb" in mock_user_prompt.call_args[0][0]
    assert "Build FTP (Default)" not in mock_user_prompt.call_args[0][0]
    assert "Max Hours: 10.0" in mock_user_prompt.call_args[0][0]
    assert result["plan"] == "test plan\n\n## intervals.icu workout file (txt)\n\n```text\n\nicu workout\n```"
    assert result["summary"] == mock_user_prompt.call_args[0][0]
    mock_stage_workout_delivery.assert_called_once()


@patch("app.services.planner.generate_plan")
@patch("app.services.planner.stage_workout_delivery")
@pytest.mark.asyncio
async def test_update_training_plan_uses_history(
    mock_stage_workout_delivery: MagicMock,
    mock_generate_plan: MagicMock,
    session: Session,
) -> None:
    """Test update_training_plan retrieves history and calls LLM with it."""
    # GIVEN: A user and an existing training plan with prompt history.
    user = User(id=uuid.uuid4(), email="test@example.com", password_hash="hash")  # noqa: S106
    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Test",
        start_date=date(2026, 4, 20),
        end_date=date(2026, 5, 17),
    )
    session.add(phase)
    session.commit()
    phase_id = phase.id

    monday = date(2026, 4, 20)
    initial_history = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    data = PlanData(raw_content="Initial Plan", workout_data=[], prompt_history=initial_history)
    save_training_plan(session, phase_id, monday, data)
    blocks: list[LongTermPlanBlock] = [{"name": "Build", "focus": "Goal-specific workload", "weeks": 4}]
    structured_data: LongTermPlanStructuredData = {
        "goal": "Test",
        "start_date": "2026-04-20",
        "target_date": "2026-05-17",
        "duration_weeks": 4,
        "blocks": blocks,
    }
    artifact = LongTermPlanArtifact(
        phase_id=phase_id,
        structured_data=structured_data,
        summary_markdown="# Long-term plan",
        prompt_history=[],
    )
    session.add(artifact)
    session.commit()
    artifact_id = artifact.id

    # GIVEN: A mocked LLM response for the update.
    mock_llm_response = MagicMock()
    mock_llm_response.plan = "Updated Plan ###JSON_START### [] ###JSON_END###"
    mock_llm_response.prompt = [
        *initial_history,
        {"role": "user", "content": "make it harder"},
        {"role": "assistant", "content": "ok"},
    ]
    mock_generate_plan.return_value = mock_llm_response

    # WHEN: Updating the training plan with feedback.
    with (
        patch("app.services.planner.Session", return_value=session),
        patch("app.services.planner.get_monday", return_value=monday),
        patch("app.services.planner.datetime") as mock_datetime,
    ):
        mock_datetime.now.return_value = datetime(2026, 4, 21, tzinfo=UTC)
        await update_training_plan(user, "make it harder")

    # THEN: Generate_plan should be called with the extended message history.
    mock_generate_plan.assert_called_once()
    passed_messages = mock_generate_plan.call_args.kwargs["messages"]
    assert len(passed_messages) == 3
    assert passed_messages[2]["content"] == "make it harder"

    # THEN: The plan and its history should be updated in the database.
    plan = session.exec(select(TrainingPlan)).one()
    assert "Updated Plan" in plan.raw_content
    assert len(plan.prompt_history) == 4
    # AND the current long-term artifact should remain unchanged
    artifacts = session.exec(select(LongTermPlanArtifact).where(LongTermPlanArtifact.phase_id == phase_id)).all()
    assert len(artifacts) == 1
    assert artifacts[0].id == artifact_id
    mock_stage_workout_delivery.assert_called_once()
