"""Tests for profile-backed web pages."""

from typing import TYPE_CHECKING

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine
from starlette.requests import Request

from app import profile as profile_module
from app.main import app
from app.routes import dashboard as dashboard_page
from app.routes import settings_page, web
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


def test_dashboard_and_settings_routes_are_registered_once() -> None:
    """Dashboard and Settings retain their exact endpoints in the composed web router."""
    # GIVEN the two extracted page routers.
    dashboard_endpoints = [
        (getattr(route, "path", None), getattr(route, "endpoint", None)) for route in dashboard_page.router.routes
    ]
    settings_endpoints = [
        (getattr(route, "path", None), getattr(route, "endpoint", None)) for route in settings_page.router.routes
    ]

    # THEN both pages are registered once, and web includes both child routers.
    assert dashboard_endpoints == [("/dashboard", web.dashboard)]
    assert settings_endpoints == [("/settings", web.settings)]
    assert len(web.router.routes) == 2
