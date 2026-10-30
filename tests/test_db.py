"""Database configuration and schema initialization tests."""

from datetime import date
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine

import app.db
from app.models import TrainingPhase, TrainingPlan, User


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
    monkeypatch.setattr(app.db, "MIGRATION_DATABASE_URL", database_url)
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
            session.commit()
            user_id, plan_id = user.id, plan.id
        engine.dispose()

        # THEN a new connection sees the current schema and saved data
        assert {"user", "trainingphase", "trainingplan", "longtermplanartifact", "workoutdelivery"} <= set(
            inspect(engine).get_table_names()
        )
        with Session(engine) as session:
            saved_user = session.get(User, user_id)
            saved_plan = session.get(TrainingPlan, plan_id)
            assert saved_user is not None
            assert saved_plan is not None
            assert saved_user.weekly_hours == 9
            assert saved_plan.workout_data == [{"name": "Endurance"}]
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20261028_02"
        command.downgrade(app.db._build_alembic_config(), "base")
        assert "user" not in inspect(engine).get_table_names()
        app.db.init_db()
        assert "user" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
