"""Integration test for the athlete's journey."""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

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


@patch("app.routes.web.IntervalsClient")
@patch("app.routes.web.parse_activities")
@patch("app.routes.web.parse_wellness_list")
@patch("app.routes.web.parse_power_curves")
@patch("app.routes.web.compute_analysis")
def test_dashboard_flow(  # noqa: PLR0913, PLR0917
    mock_compute: MagicMock,
    mock_parse_pc: MagicMock,
    mock_parse_w: MagicMock,
    mock_parse_a: MagicMock,
    mock_client_class: MagicMock,  # noqa: ARG001
    client: TestClient,
    mock_activities: list[ParsedActivity],
    mock_wellness: list[ParsedWellness],
    mock_power_curves: list[ParsedPowerCurve],
) -> None:
    """Tests the Dashboard rendering with mocks.

    Args:
        mock_compute: Mock for compute_analysis.
        mock_parse_pc: Mock for parse_power_curves.
        mock_parse_w: Mock for parse_wellness_list.
        mock_parse_a: Mock for parse_activities.
        mock_client_class: Mock for IntervalsClient class.
        client: The test client.
        mock_activities: Mocked activities.
        mock_wellness: Mocked wellness data.
        mock_power_curves: Mocked power curves.
    """
    # GIVEN an authenticated user
    email = "journey@example.com"
    password = "password123"  # noqa: S105
    client.post("/login", data={"email": email, "password": password})

    mock_parse_a.return_value = mock_activities
    mock_parse_w.return_value = mock_wellness
    mock_parse_pc.return_value = mock_power_curves
    mock_compute.return_value.to_dict.return_value = {
        "daily_series": [],
        "weekly_series": [],
        "summary": {
            "total_duration_h": 5.0,
            "total_distance_km": 100.0,
            "total_elevation_gain": 1000.0,
            "total_calories": 2500.0,
            "total_training_stress": 300.0,
            "activity_count": 3,
        },
        "hr_intensity_distribution": [0.0] * 7,
        "power_intensity_distribution": [0.0] * 7,
        "activity_type_distribution": {"Ride": 3},
        "widgets": [],
    }

    # WHEN visiting the dashboard
    resp = client.get("/dashboard")

    # THEN it should render successfully
    assert resp.status_code == 200
    assert "Dashboard" in resp.text
