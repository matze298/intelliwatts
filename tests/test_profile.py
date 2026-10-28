"""Tests for the persistent profile."""

from typing import TYPE_CHECKING

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import profile as profile_module

if TYPE_CHECKING:
    import pytest


def test_profile_is_created_once_and_retains_preferences(monkeypatch: pytest.MonkeyPatch) -> None:
    """Subsequent requests reuse the profile and its stored preferences."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    monkeypatch.setattr(profile_module, "engine", engine)
    first = profile_module.get_profile()
    with Session(engine) as session:
        stored = session.get(type(first), first.id)
        assert stored is not None
        stored.weekly_hours = 5
        session.add(stored)
        session.commit()
    second = profile_module.get_profile()
    assert second.id == first.id
    assert second.weekly_hours == 5
