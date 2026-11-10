"""Database configuration and schema initialization tests."""

from datetime import date
from uuid import uuid4

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


def test_init_db_creates_schema_and_persists_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Apply the baseline and preserve a profile and plan across connections."""
    # GIVEN an isolated schema in the test Postgres database
    admin = create_engine(app.db.DATABASE_URL)
    schema = f"test_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = make_url(app.db.DATABASE_URL).update_query_dict({"options": f"-csearch_path={schema}"})
    database_url = url.render_as_string(hide_password=False)
    engine = create_engine(database_url)
    monkeypatch.setattr(app.db, "DATABASE_URL", database_url)
    monkeypatch.setattr(app.db, "engine", engine)

    try:
        # WHEN startup applies the migrations twice and saves a profile and plan
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
            exercise = Exercise(user_id=user.id, source_id="EX-SYNTHETIC", name="Synthetic squat")
            session.add(exercise)
            session.flush()
            template = StrengthTemplate(
                user_id=user.id,
                name="Workout A",
                variant="Standard",
                version="1",
                definition=[{"slot": 1, "exercise_id": str(exercise.id)}],
            )
            session.add(template)
            session.flush()
            strength_session = StrengthSession(
                user_id=user.id,
                template_id=template.id,
                source_id="SESSION-SYNTHETIC",
                session_date=date(2026, 1, 6),
                workout_type="Workout A",
                template_version="1",
                source_data={"source": "synthetic"},
            )
            session.add(strength_session)
            session.flush()
            strength_set = StrengthSet(
                session_id=strength_session.id,
                exercise_id=exercise.id,
                source_id="SET-SYNTHETIC",
                set_number=1,
                side="Left",
                reps=8,
                source_data={"Raw Reps": "8"},
            )
            session.add(strength_set)
            session.commit()
            user_id, plan_id, strength_session_id, strength_set_id = (
                user.id, plan.id, strength_session.id, strength_set.id
            )
        engine.dispose()

        # THEN a new connection sees the current schema and saved data
        assert {
            "user", "trainingphase", "trainingplan", "longtermplanartifact", "workoutdelivery",
            "exercise", "strengthtemplate", "strengthsession", "strengthset",
        } <= set(inspect(engine).get_table_names())
        with Session(engine) as session:
            saved_user = session.get(User, user_id)
            saved_plan = session.get(TrainingPlan, plan_id)
            saved_strength_session = session.get(StrengthSession, strength_session_id)
            saved_strength_set = session.get(StrengthSet, strength_set_id)
            assert saved_user is not None
            assert saved_plan is not None
            assert saved_strength_session is not None
            assert saved_strength_set is not None
            assert saved_user.weekly_hours == 9
            assert saved_plan.workout_data == [{"name": "Endurance"}]
            assert saved_strength_session.template_version == "1"
            assert saved_strength_session.source_data == {"source": "synthetic"}
            assert saved_strength_set.side == "Left"
            assert saved_strength_set.load_kg is None
            assert saved_strength_set.source_data == {"Raw Reps": "8"}
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
