"""Tests for the user model."""

import uuid

from app.models.user import User


def test_user_settings_defaults() -> None:
    """User settings should default to app-safe values."""
    # GIVEN a brand new user model
    user = User(id=uuid.uuid4(), email="user@example.com", password_hash="hash")  # noqa: S106

    # WHEN the user settings are inspected
    # THEN the persisted preferences should default to a disabled developer mode
    assert user.developer_mode_enabled is False
