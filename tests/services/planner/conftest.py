"""Shared fixtures for planner service tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, create_engine

from app.models.plan import SQLModel

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


@pytest.fixture
def session() -> Generator[Session]:
    """Provide a clean in-memory database session for planner tests.

    Yields:
        A fresh SQLModel session backed by an in-memory SQLite database.
    """
    engine: Engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
