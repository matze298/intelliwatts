"""Tests for long-term planner lifecycle, artifacts, and web flow."""

import asyncio
import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select
from starlette.requests import Request

from app.models.plan import LongTermPlanArtifact, SQLModel, TrainingPhase
from app.models.user import User
from app.routes import web
from app.services.long_term_planner import (
    derive_weekly_brief,
    generate_long_term_plan_artifact,
    generate_long_term_plan_for_user,
    get_current_long_term_plan_artifact,
    replace_active_phase,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


def build_request(app: FastAPI, *, method: str, path: str, body: bytes = b"") -> Request:
    """Build a Starlette request for direct route testing.

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
        "app": app,
    }
    return Request(scope, receive)


@pytest.fixture
def session() -> Generator[Session]:
    """Provides a clean in-memory database session.

    Yields:
        A database session.
    """
    engine: Engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_app() -> FastAPI:
    """Provides a minimal app for exercising the web router.

    Returns:
        A FastAPI app configured with the web router.
    """
    test_app = FastAPI()
    test_app.include_router(web.router)
    test_app.state.settings = {"settings": SimpleNamespace(LANGUAGE_MODEL="test-model"), "models": ["test-model"]}
    return test_app


@pytest.fixture
def planner_test_engine() -> Engine:
    """Provides an isolated in-memory engine for planner route tests.

    Returns:
        An in-memory SQLite engine with shared connections enabled.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def planner_user(planner_test_engine: Engine) -> User:
    """Provides a persisted user for planner route tests.

    Returns:
        A stored user instance.
    """
    with Session(planner_test_engine) as session:
        user = User(email="planner@example.com", password_hash="hash")  # noqa: S106
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def patch_planner_engines(monkeypatch: pytest.MonkeyPatch, planner_test_engine: Engine) -> None:
    """Points planner route dependencies at the isolated test engine."""
    monkeypatch.setattr("app.routes.web.engine", planner_test_engine)
    monkeypatch.setattr("app.services.plan_loader.engine", planner_test_engine)


def test_replace_active_phase_archives_previous_phase(session: Session) -> None:
    """Replacing the active phase should archive the old one and create a new active phase."""
    # GIVEN an existing active phase
    user_id = uuid.uuid4()
    current_phase = TrainingPhase(
        user_id=user_id,
        primary_goal="Build FTP",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 1),
        target_date=date(2026, 5, 1),
        status="active",
    )
    session.add(current_phase)
    session.commit()

    # WHEN replacing the active phase with a new goal
    new_phase = replace_active_phase(
        session,
        user_id=user_id,
        primary_goal="Peak for hill climb",
        target_date=date(2026, 7, 15),
        start_date=date(2026, 5, 15),
    )

    # THEN the previous phase should be archived
    archived_phase = session.get(TrainingPhase, current_phase.id)
    assert archived_phase is not None
    assert archived_phase.status == "archived"

    # AND a new active phase should exist with the requested goal and target date
    assert new_phase.status == "active"
    assert new_phase.primary_goal == "Peak for hill climb"
    assert new_phase.start_date == date(2026, 5, 15)
    assert new_phase.end_date == date(2026, 7, 15)
    assert new_phase.target_date == date(2026, 7, 15)

    phases = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user_id)).all()
    assert len(phases) == 2


def test_replace_active_phase_archives_all_currently_active_phases(session: Session) -> None:
    """Replacing the active phase should archive every active phase for the user."""
    # GIVEN multiple active phases already exist for the same user
    user_id = uuid.uuid4()
    first_active = TrainingPhase(
        user_id=user_id,
        primary_goal="Build FTP",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 5, 1),
        target_date=date(2026, 5, 1),
        status="active",
    )
    second_active = TrainingPhase(
        user_id=user_id,
        primary_goal="Climb better",
        start_date=date(2026, 4, 10),
        end_date=date(2026, 6, 1),
        target_date=date(2026, 6, 1),
        status="active",
    )
    session.add(first_active)
    session.add(second_active)
    session.commit()

    # WHEN replacing the active phase
    new_phase = replace_active_phase(
        session,
        user_id=user_id,
        primary_goal="Peak for hill climb",
        target_date=date(2026, 7, 15),
        start_date=date(2026, 5, 15),
    )
    session.commit()

    # THEN every previous active phase should be archived and only the new one stay active
    phases = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user_id)).all()
    archived = [phase for phase in phases if phase.status == "archived"]
    active = [phase for phase in phases if phase.status == "active"]

    assert len(phases) == 3
    assert len(archived) == 2
    assert {phase.id for phase in archived} == {first_active.id, second_active.id}
    assert len(active) == 1
    assert active[0].id == new_phase.id


def test_generate_long_term_artifact_for_phase(session: Session) -> None:
    """Generating a long-term artifact should persist a deterministic summary for the phase."""
    # GIVEN an active phase with a long-term goal
    user_id = uuid.uuid4()
    phase = TrainingPhase(
        user_id=user_id,
        primary_goal="Peak for alpine gran fondo",
        start_date=date(2026, 5, 15),
        end_date=date(2026, 8, 15),
        target_date=date(2026, 8, 15),
        status="active",
    )
    session.add(phase)
    session.commit()

    # WHEN generating the long-term artifact
    artifact = generate_long_term_plan_artifact(session, phase=phase)

    # THEN the artifact should be persisted with the expected structured fields
    assert artifact.phase_id == phase.id
    assert artifact.summary_markdown.startswith("# Long-term plan")
    assert "Peak for alpine gran fondo" in artifact.summary_markdown
    assert artifact.structured_data["goal"] == "Peak for alpine gran fondo"
    assert artifact.structured_data["target_date"] == "2026-08-15"
    assert len(artifact.structured_data["blocks"]) >= 1
    assert artifact.prompt_history[0]["role"] == "system"

    stored = session.exec(select(LongTermPlanArtifact).where(LongTermPlanArtifact.phase_id == phase.id)).all()
    assert len(stored) == 1
    assert stored[0].id == artifact.id


def test_generate_long_term_artifact_for_short_phase_keeps_block_lengths_consistent(session: Session) -> None:
    """Short phases should not allocate more block weeks than the phase contains."""
    # GIVEN a 14-day phase
    phase = TrainingPhase(
        user_id=uuid.uuid4(),
        primary_goal="Peak for weekend race",
        start_date=date(2026, 5, 15),
        end_date=date(2026, 5, 29),
        target_date=date(2026, 5, 29),
        status="active",
    )
    session.add(phase)
    session.commit()

    # WHEN generating the long-term artifact
    artifact = generate_long_term_plan_artifact(session, phase=phase)

    # THEN the block weeks should match the phase duration exactly
    assert artifact.structured_data["duration_weeks"] == 2
    blocks = artifact.structured_data["blocks"]
    assert [block["name"] for block in blocks] == ["Build", "Peak"]
    assert sum(block["weeks"] for block in blocks) == 2


def test_derive_weekly_brief_uses_current_macro_block(session: Session) -> None:
    """Weekly brief derivation should surface the current macro block and goal context."""
    # GIVEN an active phase with a persisted long-term artifact
    phase = TrainingPhase(
        user_id=uuid.uuid4(),
        primary_goal="Peak for alpine gran fondo",
        start_date=date(2026, 5, 5),
        end_date=date(2026, 8, 15),
        target_date=date(2026, 8, 15),
        status="active",
    )
    session.add(phase)
    session.commit()
    artifact = generate_long_term_plan_artifact(session, phase=phase)

    # WHEN deriving the weekly brief partway through the phase
    brief = derive_weekly_brief(
        phase=phase,
        artifact=artifact,
        analysis_context="Registry context",
        week_start=date(2026, 6, 16),
    )

    # THEN it should include the goal, current block, and analysis context
    assert "Goal: Peak for alpine gran fondo" in brief
    assert "Current Block: Build" in brief
    assert "Goal-specific workload" in brief
    assert "Registry context" in brief


def test_regeneration_preserves_history_and_surfaces_latest_artifact(session: Session) -> None:
    """Regeneration should keep prior artifacts and pick the most recent one as current."""
    # GIVEN an active phase with one existing artifact
    user_id = uuid.uuid4()
    phase = TrainingPhase(
        user_id=user_id,
        primary_goal="Peak for alpine gran fondo",
        start_date=date(2026, 5, 15),
        end_date=date(2026, 8, 15),
        target_date=date(2026, 8, 15),
        status="active",
    )
    session.add(phase)
    session.commit()

    first = generate_long_term_plan_artifact(session, phase=phase)
    first.created_at = datetime(2026, 5, 15, 8, 0, tzinfo=UTC)
    first.updated_at = datetime(2026, 5, 15, 8, 0, tzinfo=UTC)
    session.add(first)
    session.commit()

    # WHEN regenerating the long-term artifact
    second = generate_long_term_plan_artifact(session, phase=phase)

    # THEN history should be preserved and the latest artifact should be current
    artifacts = session.exec(select(LongTermPlanArtifact).where(LongTermPlanArtifact.phase_id == phase.id)).all()
    current = get_current_long_term_plan_artifact(session, phase_id=phase.id)

    assert len(artifacts) == 2
    assert {artifact.id for artifact in artifacts} == {first.id, second.id}
    assert current is not None
    assert current.id == second.id
    assert current.created_at > first.created_at


def test_generate_long_term_plan_for_user_creates_default_phase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generating a long-term plan should create the default phase when none exists."""
    # GIVEN a persisted user without any active phase
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        user = User(email="longterm-default@example.com", password_hash="hash")  # noqa: S106
        session.add(user)
        session.commit()
        session.refresh(user)

    monkeypatch.setattr("app.services.long_term_planner.engine", test_engine)
    monkeypatch.setattr("app.services.planner.engine", test_engine)

    # WHEN generating the long-term plan
    result = generate_long_term_plan_for_user(user)

    # THEN a default active phase and linked artifact should be created
    assert "artifact_id" in result
    with Session(test_engine) as session:
        phase = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user.id)).one()
        artifact = session.exec(select(LongTermPlanArtifact).where(LongTermPlanArtifact.phase_id == phase.id)).one()

    assert phase.status == "active"
    assert phase.primary_goal == "Build FTP (Default)"
    assert artifact.summary_markdown == result["summary"]


def test_home_page_renders_long_term_goal_inputs_and_current_summary(
    patch_planner_engines: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
    planner_user: User,
    test_app: FastAPI,
) -> None:
    """The planner page should render long-term goal inputs and the current long-term summary."""
    # GIVEN an authenticated user and isolated planner dependencies
    monkeypatch.setattr(
        "app.routes.web.load_user_plan",
        lambda _user: SimpleNamespace(
            plan_html=None,
            long_term_summary_html="<h1>Long-term plan</h1><p>Current macro focus.</p>",
            prompt=None,
        ),
    )

    # WHEN loading the home page
    response = web.home(build_request(test_app, method="GET", path="/"), planner_user)

    # THEN the long-term controls and current summary should be present
    body = bytes(response.body).decode()
    assert response.status_code == 200
    assert 'action="/long-term-plan"' in body
    assert 'name="primary_goal"' in body
    assert 'name="target_date"' in body
    assert "required" in body
    assert "Long-term plan" in body
    assert "Current macro focus." in body
    assert body.index('name="primary_goal"') < body.index('name="max_hours"')


@pytest.mark.asyncio
async def test_long_term_plan_post_redirects_after_success(
    patch_planner_engines: None,  # noqa: ARG001
    planner_test_engine: Engine,
    planner_user: User,
    test_app: FastAPI,
) -> None:
    """Posting the long-term plan form should persist the phase and redirect to home."""
    # WHEN submitting a new long-term goal
    body = b"primary_goal=Peak+for+gravel+race&target_date=2026-09-20"
    response = await web.long_term_plan(
        build_request(test_app, method="POST", path="/long-term-plan", body=body),
        planner_user,
    )

    # THEN it should redirect instead of rendering directly
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # AND the active phase should be stored for the user
    with Session(planner_test_engine) as session:
        phase = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == planner_user.id)).one()

    assert phase.primary_goal == "Peak for gravel race"
    assert phase.target_date == date(2026, 9, 20)
    assert phase.status == "active"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("form_body", "error_message"),
    [
        (b"primary_goal=&target_date=2026-09-20", "Primary goal is required."),
        (b"primary_goal=Peak+for+race&target_date=", "Target date is required."),
        (b"primary_goal=Peak+for+race&target_date=bad-date", "Target date must be a valid date."),
        (b"primary_goal=Peak+for+race&target_date=2026-05-14", "Target date cannot be in the past."),
        (b"primary_goal=Peak+for+race&target_date=2026-05-15", "Target date must be after the start date."),
    ],
)
async def test_long_term_plan_post_validates_bad_input(  # noqa: PLR0913, PLR0917
    patch_planner_engines: None,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
    planner_test_engine: Engine,
    planner_user: User,
    test_app: FastAPI,
    form_body: bytes,
    error_message: str,
) -> None:
    """Invalid long-term form input should re-render the page instead of raising."""
    # GIVEN an authenticated user, isolated planner dependencies, and invalid form input
    monkeypatch.setattr("app.routes.web._today", lambda: date(2026, 5, 15))

    # WHEN submitting the invalid long-term goal form
    response = await web.long_term_plan(
        build_request(test_app, method="POST", path="/long-term-plan", body=form_body),
        planner_user,
    )

    # THEN the page should re-render with the validation error and no phase should persist
    body_text = bytes(response.body).decode()
    assert response.status_code == 200
    assert error_message in body_text

    with Session(planner_test_engine) as session:
        phases = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == planner_user.id)).all()

    assert phases == []
