"""Single-password access protection."""

import secrets
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from app import access
from app.main import app

if TYPE_CHECKING:
    import pytest

TEST_PASSWORD = access.get_settings().APP_PASSWORD


def test_access_requires_login_and_rejects_cross_origin() -> None:
    """Protected pages require login and changes require the configured origin."""
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/health").status_code == 200
        assert client.get("/", follow_redirects=False).status_code == 303
        assert client.get("/api/settings").status_code == 401
        assert (
            client.post("/login", data={"password": "wrong"}, headers={"origin": "https://testserver"}).status_code
            == 401
        )
        response = client.post(
            "/login",
            data={"password": TEST_PASSWORD},
            headers={"origin": "https://testserver"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "HttpOnly" in response.headers["set-cookie"]
        assert "Secure" in response.headers["set-cookie"]
        assert client.get("/", follow_redirects=False).status_code == 200
        assert client.post("/api/settings", json={}, headers={"origin": "https://evil.example"}).status_code == 403
        assert (
            client.post("/logout", headers={"origin": "https://testserver"}, follow_redirects=False).status_code == 303
        )
        assert client.get("/", follow_redirects=False).status_code == 303


def test_login_rate_limit_and_cookie_tampering() -> None:
    """Repeated login attempts are limited and fake sessions are rejected."""
    access._FAILURES.clear()
    with TestClient(app, base_url="https://testserver") as client:
        for _ in range(5):
            response = client.post("/login", data={"password": "bad"}, headers={"origin": "https://testserver"})
            assert response.status_code == 401
        response = client.post("/login", data={"password": TEST_PASSWORD}, headers={"origin": "https://testserver"})
        assert response.status_code == 429
        client.cookies.set("intelliwatts_session", "123.invalid")
        assert client.get("/settings", follow_redirects=False).status_code == 303
    access._FAILURES.clear()


def test_session_expires_and_password_rotation_revokes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """An expired session or a password change requires a new login."""
    settings = access.get_settings()
    access._FAILURES.clear()
    with TestClient(app, base_url="https://testserver") as client:
        client.post("/login", data={"password": TEST_PASSWORD}, headers={"origin": "https://testserver"})
        cookie = client.cookies.get("intelliwatts_session")
        assert cookie is not None
        timestamp = int(cookie.split(".")[0])
        monkeypatch.setattr(access.time, "time", lambda: timestamp + access.SESSION_SECONDS + 1)
        assert client.get("/", follow_redirects=False).status_code == 303
        monkeypatch.setattr(access.time, "time", lambda: timestamp)
        monkeypatch.setattr(settings, "APP_PASSWORD", secrets.token_urlsafe(32))
        assert client.get("/", follow_redirects=False).status_code == 303
    access._FAILURES.clear()
