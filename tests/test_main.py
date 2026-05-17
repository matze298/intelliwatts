"""Tests the app integration."""

from unittest.mock import MagicMock, patch

import pytest

from app.main import app, health_check, lifespan


def test_health_check() -> None:
    """Tests the health check endpoint."""
    # GIVEN a FastAPI app
    # WHEN the health handler is called
    response = health_check()

    # THEN the response payload should report the service status
    assert response == {"status": "ok"}


@patch("app.main.bootstrap_dev_user")
@pytest.mark.asyncio
async def test_lifespan(mock_bootstrap_dev_user: MagicMock) -> None:
    """Tests the app lifespan."""
    # GIVEN a FastAPI app
    # WHEN the app is started
    async with lifespan(app):
        pass

    # THEN the bootstrap_dev_user function is called
    mock_bootstrap_dev_user.assert_called_once()


def test_app_state() -> None:
    """Tests that the app state is correctly configured."""
    # GIVEN a FastAPI app
    # WHEN checking app state
    # THEN the app state contains the expected settings
    assert "settings" in app.state.settings
    assert "models" in app.state.settings
