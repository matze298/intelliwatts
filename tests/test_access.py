"""Single-password access protection."""

import secrets
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import access, db
from app.main import app
from app.models.user import User
from app.profile import get_profile

if TYPE_CHECKING:
    import pytest

TEST_PASSWORD = access.get_settings().APP_PASSWORD


def _clear_login_failures() -> None:
    profile = get_profile()
    with Session(db.engine) as session:
        user = session.get(User, profile.id)
        assert user is not None
        user.login_failure_timestamps = []
        session.add(user)
        session.commit()


def test_successful_logins_do_not_consume_failure_limit() -> None:
    """Repeated successful sign-ins do not block subsequent sign-ins."""
    # GIVEN a cleared login limiter
    _clear_login_failures()
    with TestClient(app, base_url="https://testserver") as client:
        # WHEN signing in more often than the failure limit
        responses = [
            client.post(
                "/login",
                data={"password": TEST_PASSWORD},
                headers={"origin": "https://testserver"},
                follow_redirects=False,
            )
            for _ in range(access.MAX_LOGIN_ATTEMPTS + 1)
        ]
        # THEN every sign-in succeeds
        assert all(response.status_code == 303 for response in responses)
    _clear_login_failures()


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
    _clear_login_failures()
    with TestClient(app, base_url="https://testserver") as client:
        for _ in range(5):
            response = client.post("/login", data={"password": "bad"}, headers={"origin": "https://testserver"})
            assert response.status_code == 401
        response = client.post("/login", data={"password": TEST_PASSWORD}, headers={"origin": "https://testserver"})
        assert response.status_code == 429
        client.cookies.set("intelliwatts_session", "123.invalid")
        assert client.get("/settings", follow_redirects=False).status_code == 303
    _clear_login_failures()


def test_session_expires_and_password_rotation_revokes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """An expired session or a password change requires a new login."""
    settings = access.get_settings()
    _clear_login_failures()
    with TestClient(app, base_url="https://testserver") as client:
        client.post("/login", data={"password": TEST_PASSWORD}, headers={"origin": "https://testserver"})
        cookie = client.cookies.get("intelliwatts_session")
        assert cookie is not None
        timestamp = int(cookie.split(".")[0])
        monkeypatch.setattr(access, "_time", lambda: timestamp + access.SESSION_SECONDS + 1)
        assert client.get("/", follow_redirects=False).status_code == 303
        monkeypatch.setattr(access, "_time", lambda: timestamp)
        monkeypatch.setattr(settings, "APP_PASSWORD", secrets.token_urlsafe(32))
        assert client.get("/", follow_redirects=False).status_code == 303
    _clear_login_failures()
