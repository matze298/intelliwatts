"""Browser-level page loading tests for core web flows."""

from __future__ import annotations

import json
import socket
import threading
import time
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, NamedTuple, cast

import pytest
import uvicorn
from playwright.sync_api import Page, expect, sync_playwright
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

from app import db
from app.auth import auth as auth_module
from app.config import get_settings
from app.main import app
from app.routes import api as api_routes
from app.routes import auth as auth_routes
from app.routes import settings as settings_routes
from app.routes import web as web_routes
from app.services import long_term_planner, plan_loader
from app.services.planner import orchestrator

if TYPE_CHECKING:
    from collections.abc import Iterator

_FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "intervals"


class BrowserServer(NamedTuple):
    """Running browser-test server details."""

    base_url: str
    server: uvicorn.Server
    thread: threading.Thread


def _load_json_fixture(name: str) -> object:
    with (_FIXTURE_DIR / name).open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


class FixtureIntervalsClient:
    """Intervals client backed by anonymized checked-in fixtures."""

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        """Load anonymized fixture payloads."""
        self._activities = cast("list[dict[str, object]]", _load_json_fixture("activities.json"))
        self._wellness = cast("list[dict[str, object]]", _load_json_fixture("wellness.json"))
        self._power_curves = cast("dict[str, object]", _load_json_fixture("power_curves.json"))

    def activities(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
        """Return anonymized activity fixtures."""
        return self._activities

    def wellness(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
        """Return anonymized wellness fixtures."""
        return self._wellness

    def power_curves(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        """Return anonymized power-curve fixtures."""
        return self._power_curves


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def browser_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[BrowserServer]:
    """Run the real FastAPI app with isolated DB and fixture-backed external APIs.

    Yields:
        The running browser-test server details.

    Raises:
        RuntimeError: If the in-process Uvicorn server does not start.
    """
    database_url = f"sqlite:///{tmp_path / 'browser-flow.db'}"
    test_engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    settings = SimpleNamespace(
        INTERVALS_API_KEY="test_api_key",
        INTERVALS_ATHLETE_ID="test_athlete_id",
        OPENAI_API_KEY=None,
        GEMINI_API_KEY="test_gemini_api_key",
        CACHE_INTERVALS_HOURS=0,
        ANALYSIS_DAYS=30,
        DASHBOARD_DAYS=42,
        LANGUAGE_MODEL="test-model",
        SYSTEM_PROMPT="system prompt",
        USER_PROMPT="user prompt",
    )

    for module in (
        db,
        auth_module,
        api_routes,
        auth_routes,
        settings_routes,
        web_routes,
        long_term_planner,
        plan_loader,
        orchestrator,
    ):
        monkeypatch.setattr(module, "engine", test_engine, raising=False)
    monkeypatch.setattr(web_routes, "IntervalsClient", FixtureIntervalsClient)
    monkeypatch.setattr(web_routes, "_today", lambda: date(2026, 4, 1))
    app.dependency_overrides[get_settings] = lambda: settings
    app.state.settings = {"settings": settings, "models": ["test-model"]}

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        msg = "Browser test server did not start."
        raise RuntimeError(msg)

    try:
        yield BrowserServer(
            base_url=f"http://127.0.0.1:{port}",
            server=server,
            thread=thread,
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        app.dependency_overrides.clear()


def test_core_pages_load_through_browser_transitions(browser_server: BrowserServer) -> None:
    """Core pages should load in a browser across navigation and JS transitions."""
    # GIVEN a running app with isolated storage and fixture-backed external API responses.
    unique_email = f"browser-flow-{uuid.uuid4()}@example.com"
    password = "correct horse battery staple"  # noqa: S105

    # WHEN a browser moves through registration, login, planner, dashboard, and settings transitions.
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.route(
            "https://cdn.jsdelivr.net/**",
            lambda route: route.fulfill(status=200, body="", content_type="application/javascript"),
        )

        _register_user(page, browser_server.base_url, unique_email, password)
        _login_user(page, browser_server.base_url, unique_email, password)
        _save_long_term_goal(page, browser_server.base_url)
        _load_dashboard_and_change_range(page, browser_server.base_url)
        _load_settings_and_store_secrets(page, browser_server.base_url)

        # THEN each page should reach its expected stable state without browser-level failures.
        browser.close()


def _register_user(page: Page, base_url: str, email: str, password: str) -> None:
    # GIVEN an unauthenticated visitor on the registration page.
    page.goto(f"{base_url}/register", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Register")).to_be_visible()

    # WHEN the visitor submits a new account.
    page.get_by_label("Email:").fill(email)
    page.get_by_label("Password:").fill(password)
    page.get_by_role("button", name="Register").click()

    # THEN the browser should transition to the login page.
    page.wait_for_url(f"{base_url}/login")
    expect(page.get_by_role("heading", name="Login")).to_be_visible()


def _login_user(page: Page, base_url: str, email: str, password: str) -> None:
    # GIVEN a registered user on the login page.
    page.get_by_label("Email:").fill(email)
    page.get_by_label("Password:").fill(password)

    # WHEN the user submits valid credentials.
    page.get_by_role("button", name="Login").click()

    # THEN the browser should transition to the authenticated planner page.
    page.wait_for_url(f"{base_url}/")
    expect(page.get_by_role("heading", name="AI Training Plan")).to_be_visible()
    expect(page.get_by_role("heading", name="Goal & planning horizon")).to_be_visible()


def _save_long_term_goal(page: Page, base_url: str) -> None:
    # GIVEN an authenticated user on the planner page.
    page.get_by_label("Primary goal:").fill("Peak for anonymized gran fondo")
    page.get_by_label("Target date:").fill("2026-09-20")

    # WHEN the user saves a long-term planning goal.
    page.get_by_role("button", name="Save Long-term Goal").click()

    # THEN the planner should reload with the long-term plan surface available.
    page.wait_for_url(f"{base_url}/")
    expect(page.locator("summary", has_text="Long-term plan")).to_be_visible()
    expect(page.get_by_text("Weekly Training Plan")).to_be_visible()


def _load_dashboard_and_change_range(page: Page, base_url: str) -> None:
    # GIVEN fixture-backed activity, wellness, and power-curve data.
    page.goto(f"{base_url}/dashboard", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Performance Center")).to_be_visible()
    expect(page.get_by_text("Analysis Lookback")).to_be_visible()

    # WHEN the browser changes the dashboard analysis range slider.
    page.locator("#daysSlider").evaluate(
        """slider => {
            slider.value = "14";
            slider.dispatchEvent(new Event("input", { bubbles: true }));
            slider.dispatchEvent(new Event("change", { bubbles: true }));
        }"""
    )

    # THEN the dashboard should transition to the selected range URL and update its label.
    page.wait_for_url(f"{base_url}/dashboard?days=14")
    expect(page.locator("#daysValue")).to_have_text("14 Days")


def _load_settings_and_store_secrets(page: Page, base_url: str) -> None:
    # GIVEN an authenticated user on the settings page.
    page.goto(f"{base_url}/settings", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Settings & Account")).to_be_visible()

    # WHEN the user stores account secrets through the AJAX settings form.
    page.get_by_label("intervals.icu Athlete ID").fill("fixture-athlete")
    page.get_by_label("intervals.icu API Key").fill("fixture-intervals-key")
    page.get_by_label("Gemini API Key").fill("fixture-gemini-key")
    page.get_by_role("button", name="Store Secrets").click()

    # THEN the page should show the successful client-side transition state.
    expect(page.locator("#secretsMessage")).to_have_text("Secrets stored successfully.")
