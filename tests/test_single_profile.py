"""Tests for the unauthenticated single-profile app."""

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.requests import Request

from app import profile as profile_module
from app.config import LanguageModel
from app.main import app
from app.planning import llm
from app.routes import web
from app.services import long_term_planner, plan_loader

if TYPE_CHECKING:
    import pytest


def test_account_routes_are_removed() -> None:
    """Account endpoints are absent from the app."""
    paths = set(app.openapi()["paths"])
    assert not paths.intersection({"/login", "/register", "/logout", "/auth/login", "/auth/register"})


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


def test_model_uses_configured_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model calls use the installation's configured key without a user secret row."""
    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(OPENAI_API_KEY="configured-key"))
    call_gpt = MagicMock(return_value=llm.LLMResponse(plan="plan", prompt=[]))
    monkeypatch.setattr(llm, "call_gpt", call_gpt)
    result = llm.generate_plan(LanguageModel.GPT_5_MINI, [{"role": "user", "content": "plan"}])
    assert result.plan == "plan"
    assert call_gpt.call_args.kwargs["api_key"] == "configured-key"
