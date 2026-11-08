"""Tests for the user model."""

import uuid

from app.models.user import User


def test_user_settings_defaults() -> None:
    """User settings should default to app-safe values."""
    # GIVEN a brand new user model
    user = User(id=uuid.uuid4())

    # WHEN the user settings are inspected
    # THEN the persisted preferences should default to a disabled developer mode
    assert user.developer_mode_enabled is False
    assert user.preferred_language_model is None
    assert user.available_cycling_days == [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
