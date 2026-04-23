"""Integration test for the athlete's journey."""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from app.intervals.parser.activity import ParsedActivity
from app.intervals.parser.power_curve import ParsedPowerCurve, PowerCurvePoint
from app.intervals.parser.wellness import ParsedWellness
from app.main import app
from app.planning.llm import LLMResponse

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def client() -> Generator[TestClient]:
    """Provides a TestClient for the app.

    Yields:
        A TestClient instance.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_activities() -> list[ParsedActivity]:
    """Provides mocked activities.

    Returns:
        A list of mocked activities.
    """
    return [
        ParsedActivity(
            date="2026-04-01",
            duration_h=0.5,
            training_stress=50.0,
            avg_power=100.0,
            type="Run",
            calories=400,
            avg_hr=120.0,
            max_hr=150.0,
            distance_km=5.0,
            elevation_gain=100.0,
            hr_zone_times=[0, 100, 200, 300, 0, 0, 0],
            power_zone_times=[{"secs": 100}],
            ftp=250,
        )
    ]


@pytest.fixture
def mock_wellness() -> list[ParsedWellness]:
    """Provides mocked wellness data.

    Returns:
        A list of mocked wellness data.
    """
    return [ParsedWellness(date="2026-04-01", hrv=60.0, resting_hr=50)]


@pytest.fixture
def mock_power_curves() -> list[ParsedPowerCurve]:
    """Provides mocked power curves.

    Returns:
        A list of mocked power curves.
    """
    return [
        ParsedPowerCurve(
            id="test",
            points=[PowerCurvePoint(secs=60, watts=300)],
        )
    ]


@pytest.fixture
def mock_llm_response() -> LLMResponse:
    """Provides mocked LLM response.

    Returns:
        A mocked LLM response.
    """
    return LLMResponse(
        plan="## Weekly Plan\n\n- Monday: Easy Run",
        prompt=[{"role": "user", "content": "test"}],
    )


def test_authentication_flow(client: TestClient) -> None:
    """Tests the Register -> Login flow.

    Args:
        client: The test client.
    """
    # GIVEN a fresh app
    email = "journey@example.com"
    password = "password123"  # noqa: S105

    # WHEN registering
    resp = client.post("/register", data={"email": email, "password": password}, follow_redirects=True)
    # THEN it should redirect to login
    assert resp.status_code == 200
    assert "login" in str(resp.url).lower()

    # AND logging in
    resp = client.post("/login", data={"email": email, "password": password}, follow_redirects=True)
    # THEN it should redirect to home and set cookie
    assert resp.status_code == 200
    assert resp.url.path == "/"
    assert "access_token" in client.cookies
