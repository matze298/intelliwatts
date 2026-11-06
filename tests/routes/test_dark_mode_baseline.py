"""One-off visual baseline capture from the merged application using Playwright.

This file is temporary agent tooling, not a Gatekeeper screenshot test.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path
from typing import override

from playwright.sync_api import sync_playwright

from app.config import get_settings
from app.routes import web as web_routes
from tests.routes.test_browser_pages import BrowserServer, FixtureIntervalsClient, browser_server  # noqa: F401


class SampleIntervalsClient(FixtureIntervalsClient):
    """Deterministic activity data for browser visual review."""

    @override
    def activities(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
        """Return synthetic activity data.

        Returns:
            Forty-two days of synthetic workouts.
        """
        samples = super().activities()
        start = date(2026, 9, 26)
        data: list[dict[str, object]] = []
        for index in range(42):
            weekday = index % 7
            if weekday not in {0, 2, 4, 5}:
                continue
            week = index // 7
            if weekday in {0, 4}:
                kind, duration, stress = "Ride", 5400, 65 + (week % 3) * 9
            elif weekday == 2:
                kind, duration, stress = "Soccer", 7920, 75
            elif week % 2 == 0:
                kind, duration, stress = "Hike", 5760, 24
            else:
                kind, duration, stress = "WeightTraining", 2340, 27
            entry = dict(samples[index % len(samples)])
            entry["start_date_local"] = f"{(start + timedelta(days=index)).isoformat()}T07:30:00"
            entry["type"] = kind
            entry["moving_time"] = duration
            entry["icu_training_load"] = stress
            entry["icu_average_watts"] = 180 + week * 5 if kind == "Ride" else None
            entry["icu_ftp"] = 255 if kind == "Ride" else None
            entry["icu_distance"] = round(duration * 8.1) if kind == "Ride" else 8200 if kind == "Hike" else None
            entry["icu_hr_zone_times"] = [int(duration * fraction) for fraction in (0.08, 0.31, 0.36, 0.2, 0.05, 0, 0)]
            entry["icu_zone_times"] = [
                {"secs": int(duration * fraction)} for fraction in (0.12, 0.27, 0.38, 0.17, 0.06)
            ]
            data.append(entry)
        return data

    @override
    def wellness(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
        """Return synthetic daily wellness metrics.

        Returns:
            Forty-two daily wellness samples.
        """
        start = date(2026, 9, 26)
        return [
            {
                "id": (start + timedelta(days=index)).isoformat(),
                "hrv": round(57 + 6 * math.sin(index * 0.47) + 3 * math.cos(index * 0.93), 1),
                "restingHR": round(51 + 2.8 * math.cos(index * 0.37) - 1.3 * math.sin(index * 0.78), 1),
                "sleepScore": max(0, min(100, round(82 + 8 * math.sin(index * 0.4) + 4 * math.cos(index * 0.73)))),
                "sleepQuality": 4,
                "fatigue": 2,
                "soreness": 2,
                "stress": 2,
                "readiness": 7,
            }
            for index in range(42)
        ]


def test_capture_baseline(browser_server: BrowserServer, monkeypatch: object) -> None:
    """Capture actual Planner and Dashboard before dark-mode changes."""
    # GIVEN the app running the code on main with synthetic fixture data.
    from pytest import MonkeyPatch

    assert isinstance(monkeypatch, MonkeyPatch)
    monkeypatch.setattr(web_routes, "IntervalsClient", SampleIntervalsClient)
    monkeypatch.setattr(web_routes, "_today", lambda: date(2026, 11, 6))
    output = Path("docs/screenshots")
    output.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 960}, device_scale_factor=1)
        page = context.new_page()
        page.goto(f"{browser_server.base_url}/login", wait_until="domcontentloaded")
        page.get_by_label("Master password").fill(get_settings().APP_PASSWORD)
        page.get_by_role("button", name="Sign in").click()
        page.get_by_role("heading", name="Goal & planning horizon").wait_for()
        # WHEN capturing the current design at desktop and mobile widths.
        for width, height, suffix in ((1440, 960, "desktop"), (390, 844, "mobile")):
            page.set_viewport_size({"width": width, "height": height})
            for name, route in (("dashboard", "/dashboard?days=42"), ("planner", "/")):
                page.goto(f"{browser_server.base_url}{route}", wait_until="domcontentloaded")
                if name == "dashboard":
                    page.locator("#pmcChart").wait_for()
                    page.wait_for_function(
                        "() => typeof Chart !== 'undefined' && Boolean(Chart.getChart(document.querySelector('#pmcChart')))",
                        timeout=15000,
                    )
                page.evaluate("document.fonts.ready")
                page.evaluate("window.scrollTo(0,0)")
                page.screenshot(
                    path=str(output / f"dark-mode-baseline-{name}-{suffix}.png"),
                    full_page=True,
                    animations="disabled",
                )
                # THEN the page should fit the viewport.
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
        browser.close()
