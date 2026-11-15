"""Database configuration and schema initialization tests."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

import pytest
from alembic import command
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, create_engine

import app.db
from app.models import (
    Exercise,
    LongTermPlanArtifact,
    StrengthSession,
    StrengthSet,
    StrengthTemplate,
    TrainingPhase,
    TrainingPlan,
    User,
    WorkoutDelivery,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine import Engine


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
        status="Completed",
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


@pytest.fixture
def isolated_migration_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """Use an isolated test schema and bind the app's migrations to it.

    Yields:
        An engine targeting only the isolated schema.
    """
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
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()



def test_init_db_creates_schema_and_persists_data(isolated_migration_engine: Engine) -> None:
    """Apply the baseline and preserve cycling plus new strength data across connections."""
    # GIVEN an isolated schema in the test Postgres database
    engine = isolated_migration_engine
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


def _cycling_snapshot(engine: Engine) -> dict[str, object]:
    """Capture complete synthetic cycling rows before and after a migration.

    Returns:
        A normalized JSON snapshot of each existing application table.
    """
    with engine.connect() as connection:
        return connection.execute(
            text("""
                SELECT jsonb_build_object(
                    'user', (SELECT jsonb_agg(to_jsonb(u) ORDER BY u.id) FROM "user" u),
                    'trainingphase', (SELECT jsonb_agg(to_jsonb(p) ORDER BY p.id) FROM trainingphase p),
                    'trainingplan', (SELECT jsonb_agg(to_jsonb(p) ORDER BY p.id) FROM trainingplan p),
                    'longtermplanartifact',
                        (SELECT jsonb_agg(to_jsonb(a) ORDER BY a.id) FROM longtermplanartifact a),
                    'workoutdelivery', (SELECT jsonb_agg(to_jsonb(d) ORDER BY d.id) FROM workoutdelivery d)
                )
                """)
        ).scalar_one()


def _seed_cycling_history(engine: Engine) -> uuid.UUID:
    """Create synthetic pre-existing records in all five cycling tables.

    Returns:
        The synthetic profile identifier.
    """
    with Session(engine) as session:
        user = User(weekly_hours=9, available_cycling_days=["Monday", "Wednesday"])
        session.add(user)
        session.flush()
        phase = TrainingPhase(
            user_id=user.id, primary_goal="Synthetic race", start_date=date(2026, 1, 1), end_date=date(2026, 2, 1)
        )
        session.add(phase)
        session.flush()
        plan = TrainingPlan(
            phase_id=phase.id,
            week_start=date(2026, 1, 5),
            raw_content="Synthetic endurance ride",
            workout_data=[{"name": "Endurance"}],
            prompt_history=[{"role": "user", "content": "Synthetic context"}],
        )
        session.add(plan)
        session.flush()
        session.add(LongTermPlanArtifact(phase_id=phase.id, summary_markdown="Synthetic macro plan"))
        session.add(WorkoutDelivery(training_plan_id=plan.id, last_error="Synthetic delivery"))
        user_id = user.id
        session.commit()
        return user_id


def test_strength_migration_preserves_existing_cycling_records(isolated_migration_engine: Engine) -> None:
    """Upgrade and roll back only the strength revision on a populated prior schema."""
    # GIVEN a populated schema at the production predecessor revision
    engine = isolated_migration_engine
    config = app.db._build_alembic_config()
    command.upgrade(config, "20261108_01")
    user_id = _seed_cycling_history(engine)
    original = _cycling_snapshot(engine)
    assert all(original.values())
    original_tables = set(inspect(engine).get_table_names())
    strength_tables = {"exercise", "strengthtemplate", "strengthsession", "strengthset"}

    # WHEN upgrading the existing database
    command.upgrade(config, "20261110_01")

    # THEN existing rows are unchanged and all new tables are empty
    assert set(inspect(engine).get_table_names()) == original_tables | strength_tables
    assert _cycling_snapshot(engine) == original
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM exercise")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM strengthtemplate")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM strengthsession")).scalar_one() == 0
        assert connection.execute(text("SELECT count(*) FROM strengthset")).scalar_one() == 0

    # WHEN persisting synthetic strength data and rolling back only the new revision
    with Session(engine) as session:
        ids = _seed_strength_history(session, user_id)
        session.commit()
    with Session(engine) as session:
        _assert_strength_history(session, ids)
    command.downgrade(config, "20261108_01")

    # THEN the original schema and all cycling rows survive, including after re-upgrade
    assert set(inspect(engine).get_table_names()) == original_tables
    assert _cycling_snapshot(engine) == original
    command.upgrade(config, "20261110_01")
    assert set(inspect(engine).get_table_names()) == original_tables | strength_tables
    assert _cycling_snapshot(engine) == original


@pytest.mark.parametrize("status", ["", "  ", "\t\n"])
def test_strength_database_rejects_blank_status(isolated_migration_engine: Engine, status: str) -> None:
    """Enforce the nonblank status invariant even through a SQLModel table constructor."""
    # GIVEN the migrated database and a synthetic existing profile
    app.db.init_db()
    with Session(isolated_migration_engine) as session:
        user = User()
        session.add(user)
        session.flush()

        # WHEN inserting a session without a meaningful status
        session.add(
            StrengthSession(
                user_id=user.id, session_date=date(2026, 1, 5), workout_type="Workout A", status=status
            )
        )

        # THEN PostgreSQL rejects the row, regardless of constructor validation behavior
        with pytest.raises(IntegrityError, match="ck_strengthsession_status_nonblank"):
            session.flush()
        session.rollback()
