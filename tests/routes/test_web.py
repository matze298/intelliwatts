"""Tests for profile-backed web pages."""

from typing import TYPE_CHECKING

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine
from starlette.requests import Request

from app import profile as profile_module
from app.main import app
from app.routes import web
from app.services import long_term_planner, plan_loader

if TYPE_CHECKING:
    import pytest


def test_planner_and_settings_render_without_login(monkeypatch: pytest.MonkeyPatch) -> None:
    """The profile can use planner and settings without a session."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    for module in (profile_module, web, plan_loader, long_term_planner):
        monkeypatch.setattr(module, "engine", engine)
    profile = profile_module.get_profile()
    request = Request({"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": [], "app": app})
    response = web.home(request, profile)
    assert response.status_code == 200
    assert b"Weekly planning limits" in response.body
    assert b"/login" not in response.body
    assert web.settings(request, profile).status_code == 200
