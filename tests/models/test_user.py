"""Tests for the user model."""

import uuid

from app.models.user import User


def test_user_settings_defaults() -> None:
    """User settings should default to app-safe values."""
    # GIVEN a brand new user model
    user = User(id=uuid.uuid4(), email="user@example.com", password_hash="hash")  # noqa: S106

    # WHEN the user settings are inspected
    # THEN the persisted preferences should default to disabled/empty values
    assert user.developer_mode_enabled is False
    assert user.system_prompt_override is None
    assert user.user_prompt_override is None


def test_user_prompt_resolution_uses_app_defaults_when_overrides_are_empty() -> None:
    """Prompt helpers should fall back to the app defaults when no override is set."""
    # GIVEN a user without prompt overrides
    user = User(id=uuid.uuid4(), email="user@example.com", password_hash="hash")  # noqa: S106

    # WHEN the effective prompts are resolved
    system_prompt = user.effective_system_prompt()
    user_prompt = user.effective_user_prompt()

    # THEN the app defaults should be returned
    assert "You are an evidence-based cycling coach." in system_prompt
    assert "TASK:" in user_prompt


def test_user_prompt_resolution_prefers_overrides() -> None:
    """Prompt helpers should use user overrides when provided."""
    # GIVEN a user with custom prompt overrides
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="hash",  # noqa: S106
        system_prompt_override="custom system",
        user_prompt_override="custom user",
    )

    # WHEN the effective prompts are resolved
    system_prompt = user.effective_system_prompt()
    user_prompt = user.effective_user_prompt()

    # THEN the custom overrides should be returned
    assert system_prompt == "custom system"
    assert user_prompt == "custom user"
