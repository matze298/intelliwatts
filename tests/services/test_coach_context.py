"""Tests for coach context building and prompt formatting."""

import uuid
from datetime import date, timedelta

from app.models.plan import LongTermPlanArtifact, TrainingPhase
from app.planning.coach_prompt import user_prompt
from app.services.coach_context import build_coach_context


def test_build_coach_context_produces_weekly_and_daily_sections() -> None:
    """Coach context should include weekly summaries and a dated daily ledger."""
    # GIVEN a synthetic long-term phase, artifact, and 42 days of training records
    phase = TrainingPhase(
        user_id=uuid.uuid4(),
        primary_goal="Peak for gravel race",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 6, 30),
        target_date=date(2026, 6, 30),
        status="active",
    )
    artifact = LongTermPlanArtifact(
        phase_id=phase.id,
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
    provider_results = {
        "ftp_trajectory": {"dates": ["2026-04-01", "2026-05-12"], "ftp_values": [250.0, 258.0]},
        "power_curve": {
            "peak_1s": 980,
            "peak_1m": 650,
            "peak_5m": 390,
            "peak_20m": 310,
            "peak_60m": 255,
        },
        "intensity": {"style": "Polarized", "power_ss_pct": 12.5},
        "activity": {"load": {"chronic": 58.0, "acute": 64.0}, "tss_7d": 420.0, "hours_7d": 9.5},
        "wellness": {"avg_hrv": 51.0, "avg_sleep_rating": 76.0},
    }
    daily_records = []
    for offset in range(42):
        record_date = date(2026, 4, 1) + timedelta(days=offset)
        daily_records.append({
            "date": record_date.isoformat(),
            "training_stress": 80.0 if offset % 7 in {1, 3} else 35.0,
            "duration_h": 1.5 if offset % 7 in {1, 3} else 0.75,
            "distance_km": 42.0 if offset % 7 in {1, 3} else 20.0,
            "types": ["Ride"],
            "activity_durations": [1.5 if offset % 7 in {1, 3} else 0.75],
            "activity_tss": [80.0 if offset % 7 in {1, 3} else 35.0],
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

    # WHEN building the coach context for the selected planning week
    context = build_coach_context(
        daily_records=daily_records,
        phase=phase,
        artifact=artifact,
        week_start=date(2026, 5, 11),
        provider_results=provider_results,
    )

    # THEN the coach context should expose weekly summaries, a daily ledger, and a compact brief
    assert len(context.weekly_summaries) == 6
    assert len(context.daily_ledger) == 14
    assert context.daily_ledger[0].date == "2026-04-29"
    assert context.daily_ledger[0].weekday in {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
    assert "recovery" in context.brief_context.lower() or "load" in context.brief_context.lower()
    assert "FTP Trajectory" in context.specialist_context
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
