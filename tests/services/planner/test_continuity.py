"""Synthetic coverage for saved prior-week prescriptions in planner context."""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session

from app.models.plan import TrainingPhase, TrainingPlan
from app.models.user import User
from app.services.planner.continuity import (
    MAX_PLAN_NARRATIVE_CHARS,
    format_previous_week_plan,
    load_previous_week_plan_context,
)
from app.services.planner.orchestrator import generate_weekly_plan, update_training_plan


def _previous_week_plan(phase_id: uuid.UUID, *, week_start: date = date(2026, 11, 9)) -> TrainingPlan:
    """Create a synthetic saved week with endurance and other-sport intentions.

    Returns:
        A plan with one structured prescription and a full-week narrative.
    """
    return TrainingPlan(
        phase_id=phase_id,
        week_start=week_start,
        raw_content="Wednesday cycling intervals; Thursday strength; Friday football; Sunday rest.",
        workout_data=[
            {
                "day": "Wednesday",
                "workout_name": "Threshold build",
                "description": "Controlled interval session",
                "segments": [
                    {
                        "title": "Work",
                        "repeats": 4,
                        "steps": [{"duration_m": 3, "power_pct": "105-110"}],
                    }
                ],
            }
        ],
    )


def test_prior_week_plan_is_explicitly_planned_even_when_not_finished(session: Session) -> None:
    """Saved prescriptions must never be represented as performed training."""
    # GIVEN week one saved before selecting week two, and an unrelated athlete/phase
    phase_id = uuid.uuid4()
    session.add(_previous_week_plan(phase_id))
    session.add(_previous_week_plan(uuid.uuid4()))
    session.commit()

    # WHEN constructing week two's continuity context
    context = load_previous_week_plan_context(
        session=session, phase_id=phase_id, week_start=date(2026, 11, 16)
    )

    # THEN both structure and narrative are included, with unambiguous planned-only labels
    assert "PLANNED ONLY (2026-11-09 to 2026-11-15)" in context
    assert "[PLANNED] 2026-11-11: Threshold build" in context
    assert "4x Work (3min at 105-110% FTP)" in context
    assert "Thursday strength; Friday football" in context
    assert "NOT completed activities" in context
    assert "never count a planned session as completed" in context


def test_no_adjacent_plan_does_not_invent_history(session: Session) -> None:
    """An absent week-one prescription is not the same as a rest week."""
    # GIVEN a saved older week, but no plan for the immediately preceding week
    phase_id = uuid.uuid4()
    session.add(_previous_week_plan(phase_id, week_start=date(2026, 11, 2)))
    session.commit()

    # WHEN requesting week three (2026-11-23), whose immediate predecessor is missing
    result = load_previous_week_plan_context(
        session=session, phase_id=phase_id, week_start=date(2026, 11, 23)
    )

    # THEN no historic planned work is invented
    assert result == ""


def test_plan_context_is_bounded_and_keeps_invalid_dates_uncertain() -> None:
    """Malformed dates and long narrative should not overrun the coach context."""
    # GIVEN a large saved narrative and a workout with an invalid weekday
    plan = _previous_week_plan(uuid.uuid4())
    plan.raw_content = "Example training narrative. " * 1000
    plan.workout_data[0]["day"] = "Unknown day"

    # WHEN preparing the context
    result = format_previous_week_plan(plan)

    # THEN the date is not fabricated and the full narrative is not copied
    assert "[PLANNED] date unresolved" in result
    assert "[Saved plan narrative truncated.]" in result
    assert len(result) < MAX_PLAN_NARRATIVE_CHARS + 1000


@pytest.mark.asyncio
async def test_future_generation_prompt_includes_saved_previous_week(session: Session) -> None:
    """The same planned-only evidence reaches Manual and provider-backed generation."""
    # GIVEN a real saved Week 1 and selected Week 2 before Week 1 finishes
    user = User()
    session.add(user)
    session.flush()
    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Bike fitness",
        start_date=date(2026, 11, 9),
        end_date=date(2026, 12, 20),
        target_date=date(2026, 12, 20),
    )
    session.add(phase)
    session.flush()
    session.add(_previous_week_plan(phase.id))
    session.commit()
    analysis = MagicMock(daily_records=[], provider_results={})
    coach = MagicMock(brief_context="No recorded sessions")
    coach.render.return_value = "No completed activities"
    settings = MagicMock()
    settings.CACHE_INTERVALS_HOURS = 0
    settings.SYSTEM_PROMPT = "System prompt"
    settings.USER_PROMPT = "Generate a plan"
    settings.ANALYSIS_DAYS = 120

    # WHEN a prompt is generated ahead of the week-one finish
    with (
        patch("app.services.planner.orchestrator.Session", return_value=session),
        patch("app.services.planner.orchestrator.get_or_create_active_phase", return_value=phase),
        patch("app.services.planner.orchestrator.get_current_long_term_plan_artifact", return_value=None),
        patch("app.services.planner.orchestrator._make_intervals_client", return_value=MagicMock()),
        patch("app.services.planner.orchestrator._get_analysis", return_value=analysis),
        patch("app.services.planner.orchestrator.build_coach_context", return_value=coach),
        patch("app.services.planner.orchestrator.derive_weekly_brief", return_value="Brief"),
        patch(
            "app.services.planner.orchestrator.registry.get_specialist_context", new_callable=AsyncMock
        ) as specialists,
        patch("app.services.planner.orchestrator.load_week_commitments", return_value="No scheduled events"),
    ):
        specialists.return_value = "Specialist context"
        result = await generate_weekly_plan(user, settings, week_start=date(2026, 11, 16), prompt_only=True)

    # THEN the assembled model message has distinct planned and recorded sections
    prompt = result["prompt"][1]["content"]
    assert "PRECEDING WEEK SAVED PLAN — PLANNED ONLY" in prompt
    assert "Threshold build" in prompt
    assert "Thursday strength; Friday football" in prompt
    assert "No completed activities" in prompt
    assert "never count a planned session as completed" in prompt


@pytest.mark.asyncio
async def test_revision_prompt_refreshes_previous_week_plan(session: Session) -> None:
    """Revisions must not rely on old generation context when Week 1 changes."""
    # GIVEN Week 1 and an already saved Week 2
    user = User()
    session.add(user)
    session.flush()
    phase = TrainingPhase(
        user_id=user.id,
        primary_goal="Bike fitness",
        start_date=date(2026, 11, 9),
        end_date=date(2026, 12, 20),
        target_date=date(2026, 12, 20),
    )
    session.add(phase)
    session.flush()
    session.add(_previous_week_plan(phase.id))
    session.add(TrainingPlan(phase_id=phase.id, week_start=date(2026, 11, 16), raw_content="Week two draft"))
    session.commit()
    settings = MagicMock()

    # WHEN Week 2 is revised while the prior week is still underway
    with (
        patch("app.services.planner.orchestrator.Session", return_value=session),
        patch("app.services.planner.orchestrator.get_or_create_active_phase", return_value=phase),
        patch("app.services.planner.orchestrator.get_current_long_term_plan_artifact", return_value=None),
        patch("app.services.planner.orchestrator._fresh_revision_context", new_callable=AsyncMock) as fresh,
    ):
        fresh.return_value = "Latest observed activity"
        result = await update_training_plan(
            user,
            "Adjust following week",
            settings,
            week_start=date(2026, 11, 16),
            prompt_only=True,
        )

    # THEN the revision contains an up-to-date, explicitly planned earlier week
    latest = result["prompt"][-1]["content"]
    assert "Latest observed activity" in latest
    assert "PRECEDING WEEK SAVED PLAN — PLANNED ONLY" in latest
    assert "[PLANNED] 2026-11-11: Threshold build" in latest
    assert "Adjust following week" in latest
