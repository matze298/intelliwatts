"""Tests for coach context building and prompt formatting."""

import uuid
from datetime import date, timedelta

import pytest

from app.models.plan import LongTermPlanArtifact, TrainingPhase
from app.planning.coach_prompt import user_prompt
from app.services import coach_context


@pytest.fixture
def coach_phase() -> TrainingPhase:
    """Provide a synthetic active phase for coach-context tests.

    Returns:
        A synthetic active phase.
    """
    return TrainingPhase(
        user_id=uuid.uuid4(),
        primary_goal="Peak for gravel race",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 6, 30),
        target_date=date(2026, 6, 30),
        status="active",
    )


@pytest.fixture
def coach_artifact(coach_phase: TrainingPhase) -> LongTermPlanArtifact:
    """Provide a deterministic long-term plan artifact.

    Returns:
        A deterministic long-term plan artifact.
    """
    return LongTermPlanArtifact(
        phase_id=coach_phase.id,
        structured_data={
            "goal": "Peak for gravel race",
            "start_date": "2026-04-01",
            "target_date": "2026-06-30",
            "duration_weeks": 12,
            "blocks": [{"name": "Build", "focus": "Goal-specific workload", "weeks": 4}],
        },
        summary_markdown="# Long-term plan",
        prompt_history=[],
    )


@pytest.fixture
def coach_daily_records() -> list[dict[str, object]]:
    """Provide 42 days of mixed training and recovery records.

    Returns:
        42 days of mixed training and recovery records.
    """
    records: list[dict[str, object]] = []
    for offset in range(42):
        record_date = date(2026, 4, 1) + timedelta(days=offset)
        is_hard_day = offset % 7 in {1, 3}
        records.append({
            "date": record_date.isoformat(),
            "training_stress": 80.0 if is_hard_day else 35.0,
            "duration_h": 1.5 if is_hard_day else 0.75,
            "distance_km": 42.0 if is_hard_day else 20.0,
            "types": ["Ride"],
            "activity_durations": [1.5 if is_hard_day else 0.75],
            "activity_tss": [80.0 if is_hard_day else 35.0],
            "hrv": 56.0 if offset < 28 else 46.0,
            "resting_hr": 48 if offset < 28 else 53,
            "sleep_score": 84 if offset < 28 else 61,
            "sleep_quality": 4 if offset < 28 else 2,
            "fatigue": 2 if offset < 28 else 4,
            "soreness": 2 if offset < 28 else 4,
            "stress": 2 if offset < 28 else 4,
            "readiness": 4 if offset < 28 else 2,
            "comments": None,
        })
    return records


def test_build_coach_context_produces_weekly_and_daily_sections(
    coach_phase: TrainingPhase,
    coach_artifact: LongTermPlanArtifact,
    coach_daily_records: list[dict[str, object]],
) -> None:
    """Coach context should include weekly summaries and a dated daily ledger."""
    # GIVEN a synthetic long-term phase, artifact, and 42 days of training records
    # WHEN building the coach context for the selected planning week
    context = coach_context.build_coach_context(
        daily_records=coach_daily_records,
        phase=coach_phase,
        artifact=coach_artifact,
        week_start=date(2026, 5, 11),
    )

    # THEN the coach context should expose weekly summaries, a daily ledger, and a compact brief
    assert len(context.weekly_summaries) == 6
    assert len(context.daily_ledger) == 14
    assert context.daily_ledger[0].date == "2026-04-29"
    assert context.daily_ledger[0].weekday in {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
    assert "recovery" in context.brief_context.lower() or "load" in context.brief_context.lower()
    assert "FTP Trajectory" not in context.render()
    assert "Recent Training" not in context.render()


def test_user_prompt_uses_deduplicated_sections() -> None:
    """The prompt helper should keep the coach text in explicit sections."""
    # GIVEN structured prompt sections
    prompt = user_prompt(
        constraints="Training Constraints:\n- Max Hours: 10\n- Max Sessions: 5",
        weekly_brief="Weekly Brief:\n- Goal: Peak for gravel race",
        coach_context="Coach Context:\n- 42-day weekly summaries\n- 14-day daily ledger",
        specialist_context="Specialist Context:\n- FTP Trajectory: +8W over the last 6 weeks",
    )

    # WHEN rendering the prompt
    # THEN it should contain the new sections and exclude the old duplicated provider narratives
    assert "Training Constraints:" in prompt
    assert "Weekly Brief:" in prompt
    assert "Coach Context:" in prompt
    assert "Specialist Context:" in prompt
    assert "Recent Training:" not in prompt
    assert "Wellness Metrics:" not in prompt
    assert "Recent Activities:" not in prompt


def test_build_week_note_thresholds() -> None:
    """The weekly note helper should classify the obvious recovery states."""
    # GIVEN representative weekly load and recovery values
    # WHEN the week is soft on sleep
    sleep_note = coach_context._build_week_note(
        total_tss=320.0,
        avg_sleep_score=68.0,
        avg_hrv=55.0,
        avg_resting_hr=49.0,
    )
    # THEN sleep should be the dominant recovery signal
    assert sleep_note == "recovery softened"

    # WHEN the week is productive but HRV is low
    hrv_note = coach_context._build_week_note(
        total_tss=450.0,
        avg_sleep_score=78.0,
        avg_hrv=48.0,
        avg_resting_hr=49.0,
    )
    # THEN the helper should flag fatigue
    assert hrv_note == "fatigue elevated"


def test_signal_for_day_flags_recovery_compromised() -> None:
    """The day-level signal helper should flag low-recovery training days."""
    # GIVEN a hard training day and a weaker recent recovery trend
    records = [
        {"date": date(2026, 5, 1), "training_stress": 40.0, "sleep_score": 82, "hrv": 55.0, "resting_hr": 48},
        {"date": date(2026, 5, 2), "training_stress": 45.0, "sleep_score": 80, "hrv": 54.0, "resting_hr": 48},
        {"date": date(2026, 5, 3), "training_stress": 80.0, "sleep_score": 60, "hrv": 46.0, "resting_hr": 53},
    ]

    # WHEN deriving the daily training signal
    signal = coach_context._signal_for_day(records[-1], records)

    # THEN it should warn about compromised recovery
    assert signal == "recovery_compromised"
