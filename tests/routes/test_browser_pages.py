"""Browser-level page loading tests for core web flows."""

from __future__ import annotations

import json
import math
import os
import socket
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, NamedTuple, cast

import pytest
import uvicorn
from playwright.sync_api import Page, expect, sync_playwright
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import db
from app import profile as profile_module
from app.config import get_settings
from app.main import app
from app.models.user import User
from app.routes import api as api_routes
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


class VisualIntervalsClient(FixtureIntervalsClient):
    """An extended, deterministic 42-day sample used only for visual screenshots."""

    def activities(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
        """Create varied sample sessions, without calling an external API."""
        samples = super().activities()
        start = date(2026, 9, 26)
        activities: list[dict[str, object]] = []
        for index in range(42):
            weekday = index % 7
            if weekday not in (0, 2, 4, 5):
                continue
            week = index // 7
            if weekday in (0, 4):
                kind = "Ride"
                duration = 5400 if weekday == 0 else 5580
                stress = 65 + (week % 3) * 9 + (8 if weekday == 4 else 0)
            elif weekday == 2:
                kind, duration, stress = "Soccer", 7920, 68 + (week % 3) * 7
            elif week % 2 == 0:
                kind, duration, stress = "Hike", 5760, 24
            else:
                kind, duration, stress = "WeightTraining", 2340, 27

            entry = dict(samples[index % len(samples)])
            entry["start_date_local"] = f"{(start + timedelta(days=index)).isoformat()}T07:30:00"
            entry["type"] = kind
            entry["moving_time"] = duration
            entry["icu_training_load"] = stress
            entry["icu_average_watts"] = 170 + week * 5 if kind == "Ride" else None
            entry["icu_ftp"] = 255 if kind == "Ride" else None
            entry["icu_distance"] = round(duration * 8.1) if kind == "Ride" else 8200 if kind == "Hike" else None
            entry["icu_hr_zone_times"] = [int(duration * fraction) for fraction in (0.08, 0.31, 0.36, 0.2, 0.05, 0, 0)]
            entry["icu_zone_times"] = [{"secs": int(duration * fraction)} for fraction in (0.12, 0.27, 0.38, 0.17, 0.06)]
            activities.append(entry)
        return activities

    def wellness(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
        """Return a full-length, varied but reproducible wellness sample."""
        start = date(2026, 9, 26)
        values: list[dict[str, object]] = []
        for index in range(42):
            values.append({
                "id": (start + timedelta(days=index)).isoformat(),
                "hrv": round(57 + 6 * math.sin(index * .47) + 3 * math.cos(index * .93), 1),
                "restingHR": round(51 + 2.8 * math.cos(index * .37) - 1.3 * math.sin(index * .78), 1),
                "sleepScore": max(0, min(100, round(82 + 8 * math.sin(index * .4) + 4 * math.cos(index * .73)))),
                "sleepQuality": 4,
                "fatigue": 2,
                "soreness": 2,
                "stress": 2,
                "readiness": 7,
            })
        return values


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _clear_login_failures() -> None:
    profile = profile_module.get_profile()
    with Session(db.engine) as session:
        user = session.get(User, profile.id)
        assert user is not None
        user.login_failure_timestamps = []
        session.add(user)
        session.commit()


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
        profile_module,
        api_routes,
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
    _clear_login_failures()

    port = _free_port()
    monkeypatch.setattr(get_settings(), "APP_ORIGIN", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(get_settings(), "SESSION_COOKIE_SECURE", False)
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
        _clear_login_failures()


def test_core_pages_load_through_browser_transitions(browser_server: BrowserServer) -> None:
    """Core pages should load in a browser across navigation and JS transitions."""
    # GIVEN a running app with isolated storage and fixture-backed external API responses.

    # WHEN a browser moves through planner, dashboard, and settings transitions.
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.route(
            "https://cdn.jsdelivr.net/**",
            lambda route: route.fulfill(status=200, body="", content_type="application/javascript"),
        )

        page.goto(f"{browser_server.base_url}/", wait_until="domcontentloaded")
        page.get_by_label("Master password").fill(get_settings().APP_PASSWORD)
        page.get_by_role("button", name="Sign in").click()
        expect(page.get_by_role("heading", name="Goal & planning horizon")).to_be_visible()
        _save_long_term_goal(page, browser_server.base_url)
        _load_dashboard_and_change_range(page, browser_server.base_url)
        page.goto(f"{browser_server.base_url}/analysis?days=42", wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Supporting detail", exact=True)).to_be_visible()
        expect(page.get_by_role("link", name="Analysis")).to_have_attribute("aria-current", "page")
        _load_settings_and_save_preferences(page, browser_server.base_url)

        # THEN each page should reach its expected stable state without browser-level failures.
        browser.close()


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
    expect(page.get_by_role("heading", name="Build your next strong season.")).to_be_visible()
    expect(page.get_by_text("Analysis window", exact=True)).to_be_visible()

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
    expect(page.locator("#daysValue")).to_have_text("14 days")


def _load_settings_and_save_preferences(page: Page, base_url: str) -> None:
    page.goto(f"{base_url}/settings", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Settings")).to_be_visible()
    page.get_by_label("Enable developer mode").check()
    page.get_by_role("button", name="Save Preferences").click()
    expect(page.get_by_text("LLM prompt")).to_be_visible()


@pytest.mark.skipif(
    os.getenv("INTELLIWATTS_CAPTURE_SCREENSHOTS") != "1",
    reason="Explicitly opt in to refreshing screenshot fixtures.",
)
def test_capture_ui_reference_screenshots(
    browser_server: BrowserServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Capture the actual Planner, Dashboard, and Analysis at desktop/mobile sizes."""
    # GIVEN the running FastAPI app with anonymized 42-day demonstration data.
    monkeypatch.setattr(web_routes, "IntervalsClient", VisualIntervalsClient)
    monkeypatch.setattr(web_routes, "_today", lambda: date(2026, 11, 6))
    screenshot_dir = Path("docs/screenshots")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            device_scale_factor=1,
            locale="de-DE",
        )
        page = context.new_page()
        page.goto(f"{browser_server.base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("Master password").fill(get_settings().APP_PASSWORD)
        page.get_by_role("button", name="Sign in").click()
        expect(page.get_by_role("heading", name="Goal & planning horizon")).to_be_visible()

        # WHEN rendering all three pages with both large and narrow viewports.
        for width, height, suffix in ((1440, 960, "desktop"), (390, 844, "mobile")):
            page.set_viewport_size({"width": width, "height": height})
            for route, screen in (
                ("/", "planner"),
                ("/dashboard?days=42", "dashboard"),
                ("/analysis?days=42", "analysis"),
            ):
                page.goto(f"{browser_server.base_url}{route}", wait_until="domcontentloaded")
                if screen == "planner":
                    page.get_by_label("Primary goal:").fill(
                        "Slowly build FTP & endurance during soccer season"
                    )
                    page.get_by_label("Target date:").fill("2026-12-07")
                    page.get_by_label("Weekly max hours").fill("2")
                    page.get_by_label("Weekly max sessions").fill("1")
                    expect(page.locator(".planner-long-term summary")).to_be_visible()
                    if width == 390:
                        assert page.locator("#max_hours").bounding_box()["width"] >= 230
                else:
                    page.wait_for_function(
                        "() => typeof window.IWCharts !== 'undefined' && typeof window.Chart !== 'undefined'",
                        timeout=15000,
                    )
                    chart_id = "#pmcChart" if screen == "dashboard" else "#typeChart"
                    page.locator(chart_id).wait_for()
                    page.wait_for_function(
                        "(id) => Boolean(Chart.getChart(document.querySelector(id)))",
                        arg=chart_id,
                    )
                    assert page.evaluate("IWCharts.weekLabel('28.09', false)") != "Date unavailable"
                    expect(page.get_by_text("NaN", exact=True)).to_have_count(0)
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(400)
                page.screenshot(
                    path=str(screenshot_dir / f"ui-{screen}-{suffix}.png"),
                    full_page=True,
                    animations="disabled",
                )
                # THEN every page fits the viewport without cropping controls or charts.
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (
                    f"{screen} overflows at {width}px"
                )
        browser.close()
