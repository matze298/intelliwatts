"""Database configuration and schema initialization tests."""

import uuid
from datetime import date

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine

import app.db
from app.models import Exercise, StrengthSession, StrengthSet, StrengthTemplate, TrainingPhase, TrainingPlan, User


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("postgres://user:pass@localhost/db", "postgresql+psycopg://user:pass@localhost/db"),
        ("postgresql://user:pass@localhost/db", "postgresql+psycopg://user:pass@localhost/db"),
        ("postgresql+psycopg://user:pass@localhost/db", "postgresql+psycopg://user:pass@localhost/db"),
    ],
)
def test_normalize_database_url(url: str, expected: str) -> None:
    """Use psycopg for standard Postgres URLs."""
    # GIVEN a configured database URL
    # WHEN the URL is normalized
    result = app.db.normalize_database_url(url)
    # THEN SQLAlchemy uses the appropriate driver
    assert result == expected


def test_reject_non_postgres_database_url() -> None:
    """A local SQLite URL cannot silently disable persistence."""
    # GIVEN a non-Postgres URL
    # WHEN selecting a database
    # THEN the configuration is rejected
    with pytest.raises(ValueError, match="PostgreSQL"):
        app.db.normalize_database_url("sqlite:///./intervals.db")


def _seed_strength_history(db_session: Session, user_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Persist a synthetic historical strength session for migration tests.

    Returns:
        Session and performed-set identifiers.
    """
    exercise = Exercise(user_id=user_id, source_id="EX-SYNTHETIC", name="Synthetic squat")
    db_session.add(exercise)
    db_session.flush()

    template = StrengthTemplate(
        user_id=user_id,
        name="Workout A",
        variant="Standard",
        version="1",
        definition=[{"slot": 1, "exercise_id": str(exercise.id)}],
    )
    db_session.add(template)
    db_session.flush()

    performed = StrengthSession(
        user_id=user_id,
        template_id=template.id,
        source_id="SESSION-SYNTHETIC",
        session_date=date(2026, 1, 6),
        workout_type="Workout A",
        template_version="1",
        source_data={"source": "synthetic"},
    )
    db_session.add(performed)
    db_session.flush()

    performed_set = StrengthSet(
        session_id=performed.id,
        exercise_id=exercise.id,
        source_id="SET-SYNTHETIC",
        set_number=1,
        side="Left",
        reps=8,
        source_data={"Raw Reps": "8"},
    )
    db_session.add(performed_set)
    db_session.flush()
    return performed.id, performed_set.id


def _assert_strength_history(db_session: Session, ids: tuple[uuid.UUID, uuid.UUID]) -> None:
    """Verify migrated strength data without exposing or fabricating metrics."""
    performed = db_session.get(StrengthSession, ids[0])
    performed_set = db_session.get(StrengthSet, ids[1])
    assert performed is not None
    assert performed_set is not None
    assert performed.template_version == "1"
    assert performed.source_data == {"source": "synthetic"}
    assert performed_set.side == "Left"
    assert performed_set.load_kg is None
    assert performed_set.source_data == {"Raw Reps": "8"}


def test_init_db_creates_schema_and_persists_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Apply the baseline and preserve cycling plus new strength data across connections."""
    # GIVEN an isolated schema in the test Postgres database
    admin = create_engine(app.db.DATABASE_URL)
    schema = f"test_{uuid.uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(app.db.DATABASE_URL).update_query_dict({"options": f"-csearch_path={schema}"})
    database_url = url.render_as_string(hide_password=False)
    engine = create_engine(database_url)
    monkeypatch.setattr(app.db, "DATABASE_URL", database_url)
    monkeypatch.setattr(app.db, "engine", engine)

    try:
        # WHEN startup applies the migrations twice and saves a profile and plans
        app.db.init_db()
        app.db.init_db()
        with Session(engine) as session:
            user = User(weekly_hours=9)
            session.add(user)
            session.flush()
            phase = TrainingPhase(
                user_id=user.id, primary_goal="Race", start_date=date(2026, 1, 1), end_date=date(2026, 2, 1)
            )
            session.add(phase)
            session.flush()
            plan = TrainingPlan(
                phase_id=phase.id, week_start=date(2026, 1, 5), raw_content="Ride", workout_data=[{"name": "Endurance"}]
            )
            session.add(plan)
            strength_ids = _seed_strength_history(session, user.id)
            session.commit()
            user_id, plan_id = user.id, plan.id
        engine.dispose()

        # THEN a new connection sees current cycling and strength schema/data
        assert {
            "user",
            "trainingphase",
            "trainingplan",
            "longtermplanartifact",
            "workoutdelivery",
            "exercise",
            "strengthtemplate",
            "strengthsession",
            "strengthset",
        } <= set(inspect(engine).get_table_names())
        with Session(engine) as session:
            saved_user = session.get(User, user_id)
            saved_plan = session.get(TrainingPlan, plan_id)
            assert saved_user is not None
            assert saved_plan is not None
            assert saved_user.weekly_hours == 9
            assert saved_plan.workout_data == [{"name": "Endurance"}]
            _assert_strength_history(session, strength_ids)

        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20261110_01"
        command.downgrade(app.db._build_alembic_config(), "base")
        assert "user" not in inspect(engine).get_table_names()
        assert "strengthsession" not in inspect(engine).get_table_names()
        app.db.init_db()
        assert "user" in inspect(engine).get_table_names()
        assert "strengthsession" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
