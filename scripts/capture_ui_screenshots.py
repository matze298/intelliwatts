"""Capture IntelliWatts UI screenshots manually from a running local app.

This tool is independent of pytest and GitHub Actions. Captures can contain personal
training and wellness information: output stays in a gitignored local directory.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import Page, sync_playwright

_DEFAULT_BASE_URL = "http://127.0.0.1:8000"
_DEFAULT_OUTPUT = Path("artifacts/ui-screenshots")
_VIEWPORTS = (("desktop", 1440, 960), ("mobile", 390, 844))
_PAGES = (("planner", "/"), ("dashboard", "/dashboard?days={days}"))
_LOGGER = logging.getLogger(__name__)


def _arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        The parsed screenshot settings.
    """
    parser = argparse.ArgumentParser(description="Capture local Planner and Dashboard screenshots with Playwright.")
    parser.add_argument("--base-url", default=_DEFAULT_BASE_URL, help="Local IntelliWatts app URL.")
    parser.add_argument("--output-dir", type=Path, default=_DEFAULT_OUTPUT, help="Private local screenshot directory.")
    parser.add_argument("--days", type=int, default=42, choices=range(7, 91), metavar="7-90")
    parser.add_argument("--theme", choices=("system", "light", "dark"), default="system", help="Browser appearance for the captures.")
    parser.add_argument(
        "--password-env",
        default="INTELLIWATTS_SCREENSHOT_PASSWORD",
        help="Name of the environment variable containing the app sign-in password.",
    )
    return parser.parse_args()


def _login(page: Page, base_url: str, password: str) -> None:
    """Authenticate with the locally running app.

    Args:
        page: Browser page.
        base_url: Local application URL.
        password: Local app password.
    """
    page.goto(urljoin(base_url, "/login"), wait_until="domcontentloaded")
    page.get_by_label("Master password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.get_by_role("heading", name="Goal & planning horizon").wait_for(timeout=15000)


def _capture(page: Page, url: str, output: Path, *, check_charts: bool) -> None:
    """Take one screenshot and verify the page fits its viewport.

    Args:
        page: Browser page.
        url: Full app URL.
        output: Destination PNG.
        check_charts: Require an initialized performance chart.

    Raises:
        RuntimeError: If the viewport has horizontal overflow.
    """
    page.goto(url, wait_until="domcontentloaded")
    if check_charts:
        page.locator("#pmcChart").wait_for(timeout=15000)
        page.wait_for_function(
            "() => typeof Chart !== 'undefined' && Boolean(Chart.getChart(document.querySelector('#pmcChart')))",
            timeout=15000,
        )
    page.evaluate("document.fonts.ready")
    page.evaluate("window.scrollTo(0, 0)")
    if not page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"):
        msg = f"Horizontal overflow at {page.viewport_size}: {url}"
        raise RuntimeError(msg)
    page.screenshot(path=str(output), full_page=True, animations="disabled")


def main() -> int:
    """Capture desktop and mobile views without modifying application data.

    Returns:
        Process exit status.

    Raises:
        SystemExit: If the screenshot password environment variable is missing.
    """
    args = _arguments()
    password = os.environ.get(args.password_env)
    if not password:
        msg = f"Set {args.password_env} in the environment before running the capture script."
        raise SystemExit(msg)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 960}, device_scale_factor=1)
            page = context.new_page()
            _login(page, args.base_url, password)
            page.evaluate("(theme) => IWTheme.set(theme)", args.theme)
            for label, width, height in _VIEWPORTS:
                page.set_viewport_size({"width": width, "height": height})
                for name, route in _PAGES:
                    variant = f"-{args.theme}" if args.theme != "system" else ""
                    output = args.output_dir / f"ui-{name}-{label}{variant}.png"
                    _capture(
                        page,
                        urljoin(args.base_url, route.format(days=args.days)),
                        output,
                        check_charts=name == "dashboard",
                    )
                    _LOGGER.info("Saved %s", output)
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
