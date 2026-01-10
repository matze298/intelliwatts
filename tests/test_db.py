"""Tests for the db module."""

from app.db import init_db


def test_init_db() -> None:
    """Tests the init_db function."""
    # GIVEN a fresh database
    # WHEN the init_db function is called
    init_db()
    # THEN the database tables should be created without errors
