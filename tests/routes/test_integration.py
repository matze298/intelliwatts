"""Integration test for the athlete's journey."""

import asyncio
import uuid
from datetime import date
from types import SimpleNamespace
from typing import TYPE_CHECKING, NamedTuple, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, delete, select
from starlette.requests import Request

from app.config import Settings
from app.db import engine
from app.intervals.parser.activity import ParsedActivity
from app.intervals.parser.power_curve import ParsedPowerCurve, PowerCurvePoint
from app.intervals.parser.wellness import ParsedWellness
from app.main import app
from app.models.plan import LongTermPlanArtifact, TrainingPhase, TrainingPlan, WorkoutDelivery
from app.models.user import User
from app.planning.llm import LLMResponse
from app.routes import api as api_routes
from app.routes import secrets as secrets_routes
from app.routes import web as web_routes
from app.services.long_term_planner import generate_long_term_plan_artifact

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class WeeklyPlannerRouteContext(NamedTuple):
    """Container for isolated planner route test state."""

    app: FastAPI
    engine: Engine
    route_user: User
    settings: Settings
    user_id: uuid.UUID


@pytest.fixture(autouse=True)
def clear_db() -> None:
    """Clears the database before each test."""
    with Session(engine) as session:
        session.exec(delete(LongTermPlanArtifact))
        session.exec(delete(WorkoutDelivery))
        session.exec(delete(TrainingPlan))
        session.exec(delete(TrainingPhase))
        session.exec(delete(User))
        session.commit()


def build_request(app_obj: FastAPI, *, method: str, path: str, body: bytes = b"") -> Request:
    """Build a Starlette request for direct handler tests.

    Returns:
        A request object that can be passed to route handlers directly.
    """
    headers = []
    if body:
        headers = [
            (b"content-type", b"application/x-www-form-urlencoded"),
            (b"content-length", str(len(body)).encode()),
        ]

    async def receive() -> dict[str, object]:
        await asyncio.sleep(0)
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": headers,
        "app": app_obj,
    }
    return Request(scope, receive)


def _build_weekly_planner_route_context(*, email: str) -> WeeklyPlannerRouteContext:
    """Build isolated route-test state for the planner workflow.

    Returns:
        The isolated app, engine, authenticated route user, and settings.
    """
    test_app = FastAPI()
    test_app.include_router(web_routes.router)
    test_app.state.settings = {"settings": SimpleNamespace(LANGUAGE_MODEL="test-model"), "models": ["test-model"]}
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        user = User(email=email, password_hash="hash")  # noqa: S106
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id

    settings = MagicMock(spec=Settings)
    settings.INTERVALS_API_KEY = "test_api_key"
    settings.INTERVALS_ATHLETE_ID = "test_athlete_id"
    settings.CACHE_INTERVALS_HOURS = 0
    settings.ANALYSIS_DAYS = 120
    settings.LANGUAGE_MODEL = "test-model"
    route_user = User(id=user_id, email=email, password_hash="hash")  # noqa: S106
    return WeeklyPlannerRouteContext(
        app=test_app,
        engine=test_engine,
        route_user=route_user,
        settings=settings,
        user_id=user_id,
    )


def _configure_isolated_planner_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    test_engine: Engine,
    registry_mock: MagicMock,
    generate_plan_mock: MagicMock,
) -> None:
    """Point planner dependencies at the isolated engine and mocked services."""
    monkeypatch.setattr("app.routes.web.engine", test_engine)
    monkeypatch.setattr("app.services.plan_loader.engine", test_engine)
    monkeypatch.setattr("app.services.planner.engine", test_engine)
    monkeypatch.setattr("app.services.long_term_planner.engine", test_engine)
    monkeypatch.setattr("app.services.planner.IntervalsClient", MagicMock())
    monkeypatch.setattr("app.services.planner.user_prompt", lambda content: content)
    registry_mock.get_combined_context = AsyncMock(return_value="Registry context")
    generate_plan_mock.return_value = LLMResponse(
        plan="## Weekly Plan\n\n- Monday: Easy Run",
        prompt=[{"role": "user", "content": "test"}],
    )
    mock_analysis = MagicMock()
    mock_analysis.provider_results = {"activity": {}}
    monkeypatch.setattr("app.services.planner._get_analysis", lambda *_args, **_kwargs: mock_analysis)


def _seed_long_term_phase(
    test_engine: Engine,
    *,
    user_id: uuid.UUID,
    primary_goal: str,
    start_date: date,
    target_date: date,
) -> None:
    """Persist an active phase and current long-term artifact for a route test."""
    with Session(test_engine) as session:
        phase = TrainingPhase(
            user_id=user_id,
            primary_goal=primary_goal,
            start_date=start_date,
            end_date=target_date,
            target_date=target_date,
            status="active",
        )
        session.add(phase)
        session.commit()
        generate_long_term_plan_artifact(session, phase=phase)
        session.commit()


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


@pytest.mark.asyncio
async def test_authentication_flow() -> None:
    """Tests the Register -> Login flow."""
    # GIVEN a fresh app
    email = "auth_journey@example.com"
    password = "password123"  # noqa: S105

    # WHEN registering
    resp = await web_routes.register_post(
        build_request(app, method="POST", path="/register", body=f"email={email}&password={password}".encode())
    )

    # THEN it should redirect to login
    assert resp.status_code == 303
    assert resp.headers["location"] == "/login"

    # AND logging in
    resp = await web_routes.login_post(
        build_request(app, method="POST", path="/login", body=f"email={email}&password={password}".encode())
    )

    # THEN it should redirect to home and set cookie
    assert resp.status_code == 303
    assert resp.headers["location"] == "/"
    assert "access_token" in resp.headers["set-cookie"]


@patch("app.routes.web.IntervalsClient")
@patch("app.routes.web.parse_activities")
@patch("app.routes.web.parse_wellness_list")
@patch("app.routes.web.compute_analysis")
def test_dashboard_flow(  # noqa: PLR0913, PLR0917
    mock_compute: MagicMock,
    mock_parse_w: MagicMock,
    mock_parse_a: MagicMock,
    mock_client_class: MagicMock,  # noqa: ARG001
    mock_activities: list[ParsedActivity],
    mock_wellness: list[ParsedWellness],
) -> None:
    """Tests the Dashboard rendering with mocks.

    Args:
        mock_compute: Mock for compute_analysis.
        mock_parse_w: Mock for parse_wellness_list.
        mock_parse_a: Mock for parse_activities.
        mock_client_class: Mock for IntervalsClient class.
        mock_activities: Mocked activities.
        mock_wellness: Mocked wellness data.
    """
    # GIVEN an authenticated user
    user = User(id=uuid.uuid4(), email="dashboard_journey@example.com", password_hash="hash")  # noqa: S106

    mock_parse_a.return_value = mock_activities
    mock_parse_w.return_value = mock_wellness

    # Setup mock analysis object with both dict and attribute access for the template
    mock_analysis = MagicMock()
    widgets = [
        {
            "name": "activity",
            "title": "Recent Training",
            "value": "100 TSS",
            "trend": "1.0 hours",
            "trend_positive": True,
        },
        {
            "name": "wellness",
            "title": "Wellness Trends",
            "custom_template": "widgets/wellness_chart.html",
            "data": {
                "dates": ["2026-04-01"],
                "hrv": [60.0],
                "hrv_7d": [60.0],
                "resting_hr": [50.0],
                "resting_hr_7d": [50.0],
                "avg_hrv": 60.0,
                "avg_resting_hr": 50.0,
                "hrv_trend": "stable",
            },
        },
        {
            "name": "intensity",
            "title": "Intensity Distribution",
            "value": "85.7%",
            "trend": "Polarized",
            "trend_positive": True,
            "custom_template": "widgets/intensity_chart.html",
            "data": {
                "hr_zones": [25.0, 60.0, 5.0, 10.0, 0.0, 0.0, 0.0],
                "power_zones": [],
                "power_ss": 0.0,
                "style": "Highly Polarized",
                "polarized_score": 85.0,
            },
        },
        {
            "name": "power_curve",
            "title": "Critical Power Heatmap",
            "custom_template": "widgets/power_curve_chart.html",
            "data": {
                "recent_90d": [{"secs": 1, "watts": 1000}],
                "season": [{"secs": 1, "watts": 1100}],
                "all_time": [{"secs": 1, "watts": 1200}],
                "peak_20m": 250,
            },
        },
        {
            "name": "weekly_volume",
            "title": "Weekly Volume",
            "custom_template": "widgets/weekly_volume_chart.html",
            "data": {
                "weeks": ["2026-03-30", "2026-04-06"],
                "duration_by_type": {"Ride": [2.0, 3.0]},
                "tss_by_type": {"Ride": [100.0, 150.0]},
            },
        },
        {
            "name": "activity_history",
            "title": "Recent Activity History",
            "custom_template": "widgets/activity_history.html",
            "data": {
                "activities": [
                    {
                        "date": "2026-04-01",
                        "type": "Run",
                        "duration_h": 0.5,
                        "training_stress": 50.0,
                        "distance_km": 5.0,
                        "avg_power": 100.0,
                        "avg_hr": 120.0,
                        "max_hr": 150.0,
                        "elevation_gain": 100.0,
                        "ftp": 250.0,
                    }
                ]
            },
        },
    ]
    mock_analysis.widgets = widgets
    mock_analysis.to_dict.return_value = {
        "provider_results": {},
        "widgets": widgets,
    }
    mock_compute.return_value = mock_analysis

    # WHEN visiting the dashboard
    settings = MagicMock(spec=Settings)
    settings.INTERVALS_API_KEY = "test_api_key"
    settings.INTERVALS_ATHLETE_ID = "test_athlete_id"
    settings.CACHE_INTERVALS_HOURS = 0
    settings.ANALYSIS_DAYS = 120
    settings.DASHBOARD_DAYS = 42
    resp = web_routes.dashboard(build_request(app, method="GET", path="/dashboard"), user, settings)

    # THEN it should render successfully and contain widget info
    assert resp.status_code == 200
    body_text = bytes(resp.body).decode()
    assert "Performance Center" in body_text
    assert "Recent Training" in body_text
    assert "Wellness Trends" in body_text
    assert "100 TSS" in body_text
    assert "Training Intensity" in body_text
    assert "Highly Polarized" in body_text
    assert "Critical Power Heatmap" in body_text
    assert "Weekly Volume" in body_text
    assert "Recent Activity History" in body_text


@patch("app.routes.web.IntervalsClient")
@patch("app.routes.web.parse_activities")
@patch("app.routes.web.parse_wellness_list")
@patch("app.routes.web.compute_analysis")
def test_dashboard_flow_passes_days_filter(  # noqa: PLR0913, PLR0917
    mock_compute: MagicMock,
    mock_parse_w: MagicMock,
    mock_parse_a: MagicMock,
    mock_client_class: MagicMock,  # noqa: ARG001
    mock_activities: list[ParsedActivity],
    mock_wellness: list[ParsedWellness],
) -> None:
    """Tests that the dashboard forwards the slider days window to analysis."""
    # GIVEN an authenticated user and mocked analysis inputs
    user = User(id=uuid.uuid4(), email="dashboard_days@example.com", password_hash="hash")  # noqa: S106

    mock_parse_a.return_value = mock_activities
    mock_parse_w.return_value = mock_wellness
    mock_analysis = MagicMock()
    mock_analysis.widgets = []
    mock_analysis.to_dict.return_value = {
        "provider_results": {},
        "widgets": [],
    }
    mock_compute.return_value = mock_analysis

    # WHEN requesting the dashboard with a specific days value
    settings = MagicMock(spec=Settings)
    settings.INTERVALS_API_KEY = "test_api_key"
    settings.INTERVALS_ATHLETE_ID = "test_athlete_id"
    settings.CACHE_INTERVALS_HOURS = 0
    settings.ANALYSIS_DAYS = 120
    settings.DASHBOARD_DAYS = 42
    resp = web_routes.dashboard(build_request(app, method="GET", path="/dashboard"), user, settings, days=21)

    # THEN the selected days window is forwarded to compute_analysis
    assert resp.status_code == 200
    mock_compute.assert_called_once()
    assert mock_compute.call_args.kwargs["display_days"] == 21


@pytest.mark.asyncio
async def test_long_term_goal_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests the long-term goal flow through the planner handler."""
    # GIVEN an authenticated user and a stable planner start date
    test_app = FastAPI()
    test_app.include_router(web_routes.router)
    test_app.state.settings = {"settings": SimpleNamespace(LANGUAGE_MODEL="test-model"), "models": ["test-model"]}
    email = "long_term_goal@example.com"
    user = User(id=uuid.uuid4(), email=email, password_hash="hash")  # noqa: S106
    monkeypatch.setattr("app.routes.web._today", lambda: date(2026, 5, 15))

    class FakeRequest:
        def __init__(self, app: FastAPI) -> None:
            self.app = app

        async def form(self) -> dict[str, str]:  # noqa: PLR6301
            return {"primary_goal": "Peak for gravel race", "target_date": "2026-09-20"}

    # WHEN saving a long-term goal through the planner form
    resp = await web_routes.long_term_plan(cast("Request", FakeRequest(test_app)), user)

    # THEN the handler should redirect and persist the saved values
    assert resp.status_code == 303

    with Session(engine) as session:
        phase = session.exec(
            select(TrainingPhase).where(TrainingPhase.user_id == user.id, TrainingPhase.status == "active")
        ).one()

    assert phase.primary_goal == "Peak for gravel race"
    assert phase.target_date.isoformat() == "2026-09-20"
    assert phase.status == "active"


@pytest.mark.asyncio
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.registry")
async def test_weekly_generation_uses_saved_long_term_goal(
    mock_registry: MagicMock,
    mock_generate_plan: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The weekly planner route should inject the saved long-term goal into the LLM prompt."""
    # GIVEN an authenticated user with a saved long-term goal and isolated planner state
    context = _build_weekly_planner_route_context(email="weekly_long_term@example.com")
    _seed_long_term_phase(
        context.engine,
        user_id=context.user_id,
        primary_goal="Peak for gravel race",
        start_date=date(2026, 5, 16),
        target_date=date(2026, 9, 20),
    )
    _configure_isolated_planner_dependencies(
        monkeypatch,
        test_engine=context.engine,
        registry_mock=mock_registry,
        generate_plan_mock=mock_generate_plan,
    )

    # WHEN generating the weekly plan through the real web route
    resp = await web_routes.generate(
        build_request(
            context.app,
            method="POST",
            path="/generate",
            body=b"max_hours=10&max_sessions=5&week_start=2026-06-01",
        ),
        context.route_user,
        context.settings,
    )

    # THEN the generated LLM prompt should include the saved long-term goal and weekly brief
    assert resp.status_code == 200
    prompt_body = mock_generate_plan.call_args.kwargs["messages"][1]["content"]
    assert "Weekly Brief:" in prompt_body
    assert "Goal: Peak for gravel race" in prompt_body
    assert "Current Block:" in prompt_body
    assert "Week Of: 2026-06-01" in prompt_body


@pytest.mark.asyncio
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.registry")
async def test_weekly_generation_rejects_invalid_selected_week(
    mock_registry: MagicMock,
    mock_generate_plan: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The weekly planner route should reject a malformed selected planning week."""
    # GIVEN an authenticated user with a saved long-term goal and isolated planner state
    context = _build_weekly_planner_route_context(email="weekly_invalid_week@example.com")
    _seed_long_term_phase(
        context.engine,
        user_id=context.user_id,
        primary_goal="Peak for gravel race",
        start_date=date(2026, 5, 16),
        target_date=date(2026, 9, 20),
    )
    _configure_isolated_planner_dependencies(
        monkeypatch,
        test_engine=context.engine,
        registry_mock=mock_registry,
        generate_plan_mock=mock_generate_plan,
    )

    # WHEN generating the weekly plan with an invalid week value
    resp = await web_routes.generate(
        build_request(
            context.app,
            method="POST",
            path="/generate",
            body=b"max_hours=10&max_sessions=5&week_start=bad-date",
        ),
        context.route_user,
        context.settings,
    )

    # THEN the page should render a validation error without calling the LLM
    body_text = bytes(resp.body).decode()
    assert resp.status_code == 200
    assert "Selected planning week must be part of the active long-term plan." in body_text
    mock_generate_plan.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.planner.generate_plan")
@patch("app.services.planner.registry")
async def test_long_term_weekly_workflow_keeps_macro_artifact_stable(
    mock_registry: MagicMock,
    mock_generate_plan: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Creating a goal, generating a week, and updating it should not mutate macro state."""
    # GIVEN an isolated planner stack and authenticated route user
    context = _build_weekly_planner_route_context(email="workflow_long_term@example.com")
    user_id = context.user_id
    _configure_isolated_planner_dependencies(
        monkeypatch,
        test_engine=context.engine,
        registry_mock=mock_registry,
        generate_plan_mock=mock_generate_plan,
    )
    monkeypatch.setattr("app.routes.web._today", lambda: date(2026, 5, 16))
    mock_generate_plan.side_effect = [
        LLMResponse(
            plan="## Weekly Plan\n\n- Tuesday: Threshold work",
            prompt=[{"role": "user", "content": "weekly"}],
        ),
        LLMResponse(
            plan="## Weekly Plan\n\n- Tuesday: Easier endurance work",
            prompt=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "weekly"},
                {"role": "user", "content": "Make Tuesday easier"},
                {"role": "assistant", "content": "updated"},
            ],
        ),
    ]

    # WHEN creating a long-term goal through the planner route
    goal_response = await web_routes.long_term_plan(
        build_request(
            context.app,
            method="POST",
            path="/long-term-plan",
            body=b"primary_goal=Peak+for+gravel+race&target_date=2026-09-20",
        ),
        context.route_user,
    )

    # THEN the goal save should redirect and create a single current artifact
    assert goal_response.status_code == 303
    with Session(context.engine) as session:
        phase = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user_id)).one()
        artifacts = session.exec(select(LongTermPlanArtifact).where(LongTermPlanArtifact.phase_id == phase.id)).all()
    assert len(artifacts) == 1
    artifact_id = artifacts[0].id

    # WHEN generating a weekly plan and then updating it tactically
    generate_response = await web_routes.generate(
        build_request(context.app, method="POST", path="/generate", body=b"max_hours=10&max_sessions=5"),
        context.route_user,
        context.settings,
    )
    update_response = await web_routes.update(
        build_request(
            context.app,
            method="POST",
            path="/update",
            body=b"feedback=Make+Tuesday+easier&week_start=2026-05-18",
        ),
        context.route_user,
        context.settings,
    )

    # THEN both weekly routes should succeed and preserve the macro artifact
    assert generate_response.status_code == 200
    assert update_response.status_code == 200
    with Session(context.engine) as session:
        phase = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user_id)).one()
        artifacts = session.exec(select(LongTermPlanArtifact).where(LongTermPlanArtifact.phase_id == phase.id)).all()
        plans = session.exec(select(TrainingPlan).where(TrainingPlan.phase_id == phase.id)).all()

    assert len(artifacts) == 1
    assert artifacts[0].id == artifact_id
    assert len(plans) == 1


@pytest.mark.asyncio
@patch("app.routes.api.generate_long_term_plan_for_user")
async def test_long_term_plan_api_flow(mock_generate_long_term: MagicMock) -> None:
    """Tests long-term plan creation and regeneration via API."""
    # GIVEN a mocked long-term planner service
    mock_generate_long_term.side_effect = [
        {"artifact_id": "artifact-1", "summary": "# Long-term plan\n\nFirst version"},
        {"artifact_id": "artifact-2", "summary": "# Long-term plan\n\nSecond version"},
    ]

    user = User(id=uuid.uuid4(), email="longterm_api@example.com", password_hash="hash")  # noqa: S106

    # WHEN creating and then regenerating a long-term plan via the API handlers
    create_resp = await api_routes.create_long_term_plan_api(user)
    regenerate_resp = await api_routes.regenerate_long_term_plan_api(user)

    # THEN each handler should return the corresponding artifact payload
    assert create_resp["artifact_id"] == "artifact-1"
    assert "First version" in create_resp["summary"]
    assert regenerate_resp["artifact_id"] == "artifact-2"
    assert "Second version" in regenerate_resp["summary"]


@pytest.mark.asyncio
async def test_long_term_plan_api_creates_default_phase_for_fresh_user(monkeypatch: pytest.MonkeyPatch) -> None:
    """The long-term API should create a default phase instead of failing for a fresh user."""
    # GIVEN a fresh authenticated user without an active phase
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        user = User(email="longterm-fresh@example.com", password_hash="hash")  # noqa: S106
        session.add(user)
        session.commit()
        session.refresh(user)

    monkeypatch.setattr("app.services.long_term_planner.engine", test_engine)
    monkeypatch.setattr("app.services.planner.engine", test_engine)

    # WHEN the long-term API is called directly
    response = await api_routes.create_long_term_plan_api(user)

    # THEN it should create a default active phase and return an artifact payload
    assert "artifact_id" in response
    with Session(test_engine) as session:
        phase = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user.id)).one()

    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP (Default)"


def test_home_page_renders_current_long_term_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """The home page should show the current long-term summary for the authenticated user."""
    # GIVEN an authenticated user with a current long-term summary to render
    test_app = FastAPI()
    test_app.include_router(web_routes.router)
    test_app.state.settings = {"settings": SimpleNamespace(LANGUAGE_MODEL="test-model"), "models": ["test-model"]}

    user = User(id=uuid.uuid4(), email="planner_summary@example.com", password_hash="hash")  # noqa: S106

    monkeypatch.setattr("app.routes.web.engine", engine)
    monkeypatch.setattr("app.routes.web._get_active_phase", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "app.routes.web.load_user_plan",
        lambda _user: SimpleNamespace(
            plan_html=None,
            long_term_summary_html="<h1>Long-term plan</h1><p>Current macro focus.</p>",
            prompt=None,
            delivery_status=None,
            delivery_last_error=None,
        ),
    )

    # WHEN the home page is rendered
    resp = web_routes.home(build_request(test_app, method="GET", path="/"), user)

    # THEN the current long-term summary should be present in the response body
    assert resp.status_code == 200
    body = bytes(resp.body).decode()
    assert "Long-term plan" in body
    assert "Current macro focus." in body


def test_secrets_flow() -> None:
    """Tests the Secrets storage flow."""
    # GIVEN an authenticated user
    user = User(id=uuid.uuid4(), email="secrets_journey@example.com", password_hash="hash")  # noqa: S106

    # WHEN storing secrets
    resp = secrets_routes.store(
        secrets_routes.StoreSecretsRequest(
            athlete_id="123",
            intervals_api_key="abc",
            openai_api_key="sk-123",
        ),
        user,
    )

    # THEN it should be successful
    assert resp == {"stored": True}
