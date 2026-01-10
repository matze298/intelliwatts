"""Tests the app integration."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    """Tests the health check endpoint."""
    # GIVEN a FastAPI app
    with TestClient(app) as client:
        # WHEN the /health endpoint is called
        response = client.get("/health")
        # THEN the response is 200 OK
        expected_status = 200
        assert response.status_code == expected_status
        assert response.json() == {"status": "ok"}


@patch("app.main.bootstrap_dev_user")
def test_lifespan(mock_bootstrap_dev_user: MagicMock) -> None:
    """Tests the app lifespan."""
    # GIVEN a FastAPI app
    # WHEN the app is started
    with TestClient(app):
        pass

    # THEN the bootstrap_dev_user function is called
    mock_bootstrap_dev_user.assert_called_once()


def test_app_state() -> None:
    """Tests that the app state is correctly configured."""
    # GIVEN a FastAPI app
    # WHEN the app is started
    with TestClient(app):
        # THEN the app state contains the expected settings
        assert "settings" in app.state.settings
        assert "models" in app.state.settings
