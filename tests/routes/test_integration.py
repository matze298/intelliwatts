"""Integration test for the athlete's journey."""

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.db import engine
from app.intervals.parser.activity import ParsedActivity
from app.intervals.parser.power_curve import ParsedPowerCurve, PowerCurvePoint
from app.intervals.parser.wellness import ParsedWellness
from app.main import app
from app.models.user import User
from app.planning.llm import LLMResponse

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def clear_db() -> None:
    """Clears the database before each test."""
    with Session(engine) as session:
        session.exec(delete(User))
        session.commit()


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
    email = "auth_journey@example.com"
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
    email = "dashboard_journey@example.com"
    password = "password123"  # noqa: S105
    client.post("/register", data={"email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})

    mock_parse_a.return_value = mock_activities
    mock_parse_w.return_value = mock_wellness
    mock_parse_pc.return_value = mock_power_curves
    mock_compute.return_value.to_dict.return_value = {
        "provider_results": {},
        "widgets": [
            {
                "name": "test_widget",
                "title": "Test Title",
                "value": "123",
                "trend": "Up",
                "trend_positive": True,
            }
        ],
    }

    # WHEN visiting the dashboard
    resp = client.get("/dashboard")

    # THEN it should render successfully and contain widget info
    assert resp.status_code == 200
    assert "Dashboard" in resp.text
    assert "Test Title" in resp.text
    assert "123" in resp.text


@patch("app.services.planner.generate_plan")
@patch("app.services.planner.IntervalsClient")
def test_planning_flow(
    mock_client_class: MagicMock,  # noqa: ARG001
    mock_gen_plan: MagicMock,
    client: TestClient,
    mock_llm_response: LLMResponse,
) -> None:
    """Tests the Planning flow (Web and API) with mocks.

    Args:
        mock_client_class: Mock for IntervalsClient class.
        mock_gen_plan: Mock for generate_plan.
        client: The test client.
        mock_llm_response: Mocked LLM response.
    """
    # GIVEN an authenticated user
    email = "planning_journey@example.com"
    password = "password123"  # noqa: S105
    client.post("/register", data={"email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})
    mock_gen_plan.return_value = mock_llm_response

    # WHEN generating a plan via WEB
    resp = client.post("/generate", data={"max_hours": "10", "max_sessions": "5"}, follow_redirects=True)
    # THEN it should render successfully
    assert resp.status_code == 200
    assert "Weekly Plan" in resp.text

    # AND generating via API
    resp = client.post("/api/generate-plan")
    # THEN it should return JSON
    assert resp.status_code == 200
    assert "plan" in resp.json()


def test_secrets_flow(client: TestClient) -> None:
    """Tests the Secrets storage flow.

    Args:
        client: The test client.
    """
    # GIVEN an authenticated user
    email = "secrets_journey@example.com"
    password = "password123"  # noqa: S105
    client.post("/register", data={"email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})

    # WHEN storing secrets
    resp = client.post(
        "/secrets/store",
        params={
            "athlete_id": "123",
            "intervals_api_key": "abc",
            "openai_api_key": "sk-123",
        },
    )

    # THEN it should be successful
    assert resp.status_code == 200
    assert resp.json() == {"stored": True}
