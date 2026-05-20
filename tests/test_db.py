"""Tests for the db module."""

import sqlite3

from sqlmodel import create_engine

import app.db
from app.db import init_db


def build_half_migrated_db(db_path) -> str:  # noqa: ANN001
    """Create a sqlite database in the half-migrated state seen in production.

    Returns:
        The SQLAlchemy database URL for the created sqlite file.
    """
    database_url = f"sqlite:///{db_path}"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE user (
                id CHAR(32) PRIMARY KEY NOT NULL,
                email VARCHAR NOT NULL,
                password_hash VARCHAR NOT NULL,
                weekly_hours FLOAT NOT NULL DEFAULT 8.0,
                weekly_sessions INTEGER NOT NULL DEFAULT 4
            );
            CREATE TABLE usersecrets (
                id CHAR(32) PRIMARY KEY NOT NULL,
                user_id CHAR(32) NOT NULL,
                intervals_athlete_id VARCHAR NOT NULL,
                intervals_api_key BLOB NOT NULL,
                openai_api_key BLOB,
                gemini_api_key BLOB,
                FOREIGN KEY(user_id) REFERENCES user(id)
            );
            CREATE TABLE trainingphase (
                id CHAR(32) PRIMARY KEY NOT NULL,
                user_id CHAR(32) NOT NULL,
                primary_goal VARCHAR NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                status VARCHAR NOT NULL,
                FOREIGN KEY(user_id) REFERENCES user(id)
            );
            CREATE TABLE trainingplan (
                id CHAR(32) PRIMARY KEY NOT NULL,
                phase_id CHAR(32) NOT NULL,
                week_start DATE NOT NULL,
                raw_content VARCHAR NOT NULL,
                workout_data JSON NOT NULL,
                prompt_history JSON NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(phase_id) REFERENCES trainingphase(id)
            );
            CREATE TABLE longtermplanartifact (
                id CHAR(32) PRIMARY KEY NOT NULL,
                phase_id CHAR(32) NOT NULL,
                structured_data JSON NOT NULL,
                summary_markdown VARCHAR NOT NULL,
                prompt_history JSON NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY(phase_id) REFERENCES trainingphase(id)
            );
            CREATE TABLE alembic_version (
                version_num VARCHAR(32) NOT NULL
            );
            INSERT INTO alembic_version(version_num) VALUES ('7543c1e4540b');
            INSERT INTO user(id, email, password_hash, weekly_hours, weekly_sessions)
            VALUES ('11111111111111111111111111111111', 'user@example.com', 'hash', 8.0, 4);
            INSERT INTO trainingphase(id, user_id, primary_goal, start_date, end_date, status)
            VALUES (
                '22222222222222222222222222222222',
                '11111111111111111111111111111111',
                'Peak for gravel race',
                '2026-05-15',
                '2026-09-20',
                'active'
            );
            """
        )
        connection.commit()
    return database_url


def test_init_db() -> None:
    """Tests the init_db function."""
    # GIVEN a fresh database
    # WHEN the init_db function is called
    init_db()
    # THEN the database tables should be created without errors


def test_init_db_upgrades_half_migrated_sqlite_schema(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    """init_db should repair a sqlite database missing the latest user settings columns."""
    # GIVEN a sqlite database stuck between revisions
    db_path = tmp_path / "half_migrated.db"
    database_url = build_half_migrated_db(db_path)
    engine = create_engine(database_url)

    monkeypatch.setattr(app.db, "DATABASE_URL", database_url)
    monkeypatch.setattr(app.db, "engine", engine)

    # WHEN init_db runs at startup
    init_db()

    # THEN the developer-mode column should be added and the migration version should advance
    with sqlite3.connect(db_path) as connection:
        columns = connection.execute("PRAGMA table_info(user)").fetchall()
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()

    assert any(column[1] == "developer_mode_enabled" for column in columns)
    assert version == ("20260520_01",)
