"""Tests for the planner orchestration service."""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session, select

from app.models.plan import (
    LongTermPlanArtifact,
    LongTermPlanBlock,
    LongTermPlanStructuredData,
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


@patch("app.services.planner.orchestrator.IntervalsClient")
@patch("app.services.planner.persistence.stage_workout_delivery")
@patch("app.services.planner.orchestrator.registry")
@patch("app.services.planner.orchestrator.build_coach_context")
@patch("app.services.planner.orchestrator.generate_plan")
@patch("app.services.planner.orchestrator.derive_weekly_brief")
@patch("app.services.planner.orchestrator.get_current_long_term_plan_artifact")
@patch("app.services.planner.orchestrator.get_or_create_active_phase")
@patch("app.services.planner.prompt.user_prompt")
@pytest.mark.asyncio
async def test_generate_weekly_plan(  # noqa: PLR0913, PLR0917
    mock_user_prompt: MagicMock,
    mock_get_active_phase: MagicMock,
    mock_get_current_artifact: MagicMock,
    mock_derive_weekly_brief: MagicMock,
    mock_generate_plan: MagicMock,
    mock_build_coach_context: MagicMock,
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
    mock_settings.SYSTEM_PROMPT = "custom system prompt"
    mock_settings.USER_PROMPT = "custom user prompt"

    mock_coach_context = MagicMock()
    mock_coach_context.render.return_value = "Coach Context:\n- 42-day weekly summaries"
    mock_coach_context.brief_context = "Recent training is steady."
    mock_build_coach_context.return_value = mock_coach_context
    mock_registry.get_specialist_context = AsyncMock(return_value="FTP Trajectory:\n- Starting FTP: 250.0W")
    mock_user_prompt.return_value = "Formatted prompt"
    mock_generate_plan.return_value = LLMResponse(plan="test plan", prompt=[{"role": "user", "content": "test prompt"}])
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
    mock_analysis.daily_records = []
    with (
        patch("app.services.planner.orchestrator.Session"),
        patch("app.services.planner.orchestrator._get_analysis", return_value=mock_analysis),
    ):
        result = await generate_weekly_plan(mock_user, mock_settings, week_start=target_week_start)

    # THEN: The coach context and prompt helper should be called with the expected data.
    mock_intervals_client.assert_called_once_with("test_api_key", "test_athlete_id", session=ANY)
    mock_build_coach_context.assert_called_once_with(
        daily_records=mock_analysis.daily_records,
        phase=mock_phase,
        artifact=mock_get_current_artifact.return_value,
        week_start=target_week_start,
    )
    mock_registry.get_specialist_context.assert_awaited_once_with(mock_analysis.provider_results)
    mock_derive_weekly_brief.assert_called_once()
    assert mock_derive_weekly_brief.call_args.kwargs["week_start"] == target_week_start
    mock_user_prompt.assert_called_once_with(
        constraints="- Max Hours: 10.0\n- Max Sessions: 5\n- Primary Goal: Peak for hill climb",
        weekly_brief="Weekly Brief:\n- Goal: Peak for hill climb\n- Current Block: Build",
        coach_context="Coach Context:\n- 42-day weekly summaries",
        specialist_context="FTP Trajectory:\n- Starting FTP: 250.0W",
        task_prompt="custom user prompt",
    )
    assert mock_generate_plan.call_args.kwargs["messages"][0]["content"] == "custom system prompt"
    assert result["plan"] == "test plan"
    assert result["summary"] == "Formatted prompt"
    mock_stage_workout_delivery.assert_called_once()


@patch("app.services.planner.orchestrator.generate_plan")
@patch("app.services.planner.persistence.stage_workout_delivery")
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
        patch("app.services.planner.orchestrator.Session", return_value=session),
        patch("app.services.planner.orchestrator.get_monday", return_value=monday),
        patch("app.services.planner.orchestrator.datetime") as mock_datetime,
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


@pytest.mark.asyncio
async def test_update_training_plan_fallback_uses_selected_week(session: Session) -> None:
    """Updating a missing selected week should generate that same week."""
    # GIVEN a user, active phase, and selected week without a saved plan
    user = User(id=uuid.uuid4(), email="fallback@example.com", password_hash="hash")  # noqa: S106
    session.add(user)
    phase = get_or_create_active_phase(session, user.id)
    selected_week = date(2026, 6, 1)

    # WHEN updating the selected week without an existing plan
    with (
        patch("app.services.planner.orchestrator.Session", return_value=session),
        patch(
            "app.services.planner.orchestrator.generate_weekly_plan", new_callable=AsyncMock
        ) as mock_generate_weekly_plan,
    ):
        mock_generate_weekly_plan.return_value = {"plan": "generated", "week_start": selected_week}
        result = await update_training_plan(user, "make it easier", week_start=selected_week)

    # THEN the fallback generation preserves the selected week
    mock_generate_weekly_plan.assert_awaited_once_with(user, ANY, week_start=selected_week)
    assert result["week_start"] == selected_week
    assert phase.user_id == user.id
