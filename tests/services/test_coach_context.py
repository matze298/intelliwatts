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


def test_personal_recovery_baseline_detects_relative_changes_not_absolute_values() -> None:
    """Recovery comparisons use personal observations, not an absolute HRV/RHR threshold."""
    baseline = [
        coach_context.CoachDailyRecord(
            date=date(2026, 4, 1) + timedelta(days=index),
            training_stress=30,
            duration_h=1,
            activity_type="Ride",
            sleep_score=88,
            hrv=38,
            resting_hr=61,
        )
        for index in range(28)
    ]
    recent = [
        coach_context.CoachDailyRecord(
            date=date(2026, 4, 29) + timedelta(days=index),
            training_stress=40,
            duration_h=1,
            activity_type="Ride",
            sleep_score=66,
            hrv=30,
            resting_hr=69,
        )
        for index in range(7)
    ]
    summary = coach_context._recovery_comparison(baseline, recent)
    assert "hrv 30.0 vs baseline 38.0" in summary
    assert "resting_hr 69.0 vs baseline 61.0" in summary
    assert "sleep_score 66.0 vs baseline 88.0" in summary
    assert "multiple trends warrant attention" in summary
    assert coach_context._signal_for_day(recent[-1], baseline + recent) == "recovery_watch"


def test_recovery_baseline_respects_missing_data() -> None:
    """No baseline should produce no numerical inference or false warning."""
    incomplete = [
        coach_context.CoachDailyRecord(
            date=date(2026, 5, 1) + timedelta(days=index),
            training_stress=20,
            duration_h=0.5,
            activity_type="Ride",
            sleep_score=None,
            hrv=None,
            resting_hr=None,
        )
        for index in range(7)
    ]
    text = coach_context._recovery_comparison([], incomplete)
    assert "insufficient baseline" in text
    assert "multiple trends warrant attention" not in text
    assert coach_context._signal_for_day(incomplete[-1], incomplete) == "training_logged"


def test_cross_sport_context_counts_multiple_sports_on_same_day(
    coach_phase: TrainingPhase,
    coach_artifact: LongTermPlanArtifact,
) -> None:
    """The coach sees both cycling and non-cycling work, not only the first sport."""
    records: list[dict[str, object]] = []
    for index in range(42):
        kinds = ["Ride", "Soccer"] if index in {37, 40} else ["Ride"]
        records.append({
            "date": (date(2026, 4, 1) + timedelta(days=index)).isoformat(),
            "duration_h": 1.5 if len(kinds) > 1 else 0.75,
            "training_stress": 90 if len(kinds) > 1 else 35,
            "types": kinds,
            "hrv": 55,
            "resting_hr": 49,
            "sleep_score": 80,
        })
    context = coach_context.build_coach_context(
        daily_records=records,
        phase=coach_phase,
        artifact=coach_artifact,
        week_start=date(2026, 5, 11),
    )
    assert "Soccer (2d)" in context.brief_context
    assert any("Ride + Soccer" in day.activity_type for day in context.daily_ledger)
    assert "400 TSS" not in context.render()
