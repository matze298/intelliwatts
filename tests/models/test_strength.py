"""Strength foundation contract tests using synthetic, non-athlete data."""

import uuid
from datetime import date

from app.models.strength import Exercise, StrengthSession, StrengthSet, StrengthTemplate


def test_strength_templates_have_explicit_versions_and_ordered_slots() -> None:
    """Changing a plan requires a new version rather than rewriting an old workout."""
    # GIVEN an athlete, an exercise, and a structured template
    user_id = uuid.uuid4()
    exercise = Exercise(
        user_id=user_id,
        source_id="EX-TEST-SQUAT",
        name="Example squat",
        source_data={"Movement Pattern": "Squat", "Supports Band": False},
    )
    definition = [{"slot": 1, "exercise_id": str(exercise.id), "sets_min": 3, "reps_max": 8}]

    # WHEN a versioned workout template is created
    template = StrengthTemplate(
        user_id=user_id,
        name="Workout A",
        variant="Standard",
        version="1",
        definition=definition,
    )

    # THEN the authored order and exact version are retained
    assert exercise.source_data == {"Movement Pattern": "Squat", "Supports Band": False}
    assert template.definition == definition
    assert template.version == "1"
    assert template.user_id == user_id
    assert template.active is True


def test_strength_session_is_performed_work_not_a_planned_workout() -> None:
    """Historical logs can preserve the version used and the original row."""
    # GIVEN an athlete and a completed training session
    user_id = uuid.uuid4()
    original = {"Session ID": "SYNTHETIC-1", "Source Key": None}
    session = StrengthSession(
        user_id=user_id,
        source_id="SYNTHETIC-1",
        session_date=date(2026, 1, 1),
        workout_type="Workout A",
        template_version="1",
        status="Completed",
        source_data=original,
    )

    # WHEN the session is inspected
    # THEN its performed state is independent of a cycling TrainingPlan
    assert session.template_id is None
    assert session.template_version == "1"
    assert session.source_data == original
    assert session.session_rpe is None


def test_strength_sets_keep_missing_metrics_and_unilateral_sides() -> None:
    """Absent measurements must not silently become zero, even for bodyweight work."""
    # GIVEN a synthetic session and exercise
    session_id = uuid.uuid4()
    exercise_id = uuid.uuid4()

    # WHEN two historical sets are constructed
    left = StrengthSet(
        session_id=session_id,
        exercise_id=exercise_id,
        set_number=1,
        side="Left",
        reps=8,
        source_id="LEFT-1",
        source_data={"Raw Reps": "8"},
    )
    right = StrengthSet(
        session_id=session_id,
        exercise_id=exercise_id,
        set_number=1,
        side="Right",
        reps=7,
        load_kg=0.0,
    )

    # THEN missing load/RIR remains null while an explicitly recorded zero stays zero
    assert left.load_kg is None
    assert left.rir is None
    assert left.side == "Left"
    assert left.source_data == {"Raw Reps": "8"}
    assert right.load_kg == 0.0
    assert right.side == "Right"
