"""Tests for long-term planner lifecycle and web flow."""

import asyncio
import uuid
from datetime import date
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select
from starlette.requests import Request

from app.models.plan import SQLModel, TrainingPhase
from app.models.user import User
from app.routes import web
from app.services.long_term_planner import replace_active_phase

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine


def build_test_app() -> FastAPI:
    """Build a minimal app for exercising the web router.

    Returns:
        A FastAPI app configured with the web router.
    """
    test_app = FastAPI()
    test_app.include_router(web.router)
    test_app.state.settings = {"settings": SimpleNamespace(LANGUAGE_MODEL="test-model"), "models": ["test-model"]}
    return test_app


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

    new_phase = replace_active_phase(
        session,
        user_id=user_id,
        primary_goal="Peak for hill climb",
        target_date=date(2026, 7, 15),
        start_date=date(2026, 5, 15),
    )
    session.commit()

    phases = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user_id)).all()
    archived = [phase for phase in phases if phase.status == "archived"]
    active = [phase for phase in phases if phase.status == "active"]

    assert len(phases) == 3
    assert len(archived) == 2
    assert {phase.id for phase in archived} == {first_active.id, second_active.id}
    assert len(active) == 1
    assert active[0].id == new_phase.id


def test_home_page_renders_long_term_goal_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The planner page should render long-term goal inputs above weekly controls."""
    # GIVEN an authenticated user and isolated in-memory database
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        user = User(email="planner@example.com", password_hash="hash")  # noqa: S106
        session.add(user)
        session.commit()
        session.refresh(user)

    monkeypatch.setattr("app.routes.web.engine", test_engine)
    monkeypatch.setattr("app.services.plan_loader.engine", test_engine)
    monkeypatch.setattr(
        "app.routes.web.load_user_plan",
        lambda _user: SimpleNamespace(
            plan_html=None,
            prompt=None,
        ),
    )

    # WHEN loading the home page
    response = web.home(build_request(build_test_app(), method="GET", path="/"), user)

    # THEN the long-term fields should be present before the weekly controls
    body = bytes(response.body).decode()
    assert response.status_code == 200
    assert 'action="/long-term-plan"' in body
    assert 'name="primary_goal"' in body
    assert 'name="target_date"' in body
    assert "required" in body
    assert body.index('name="primary_goal"') < body.index('name="max_hours"')


@pytest.mark.asyncio
async def test_long_term_plan_post_redirects_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Posting the long-term plan form should persist the phase and redirect to home."""
    # GIVEN an authenticated user and isolated in-memory database
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        user = User(email="planner-post@example.com", password_hash="hash")  # noqa: S106
        session.add(user)
        session.commit()
        session.refresh(user)

    monkeypatch.setattr("app.routes.web.engine", test_engine)
    monkeypatch.setattr("app.services.plan_loader.engine", test_engine)

    # WHEN submitting a new long-term goal
    body = b"primary_goal=Peak+for+gravel+race&target_date=2026-09-20"
    response = await web.long_term_plan(
        build_request(build_test_app(), method="POST", path="/long-term-plan", body=body),
        user,
    )

    # THEN it should redirect instead of rendering directly
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # AND the active phase should be stored for the user
    with Session(test_engine) as session:
        phase = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user.id)).one()

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
async def test_long_term_plan_post_validates_bad_input(
    monkeypatch: pytest.MonkeyPatch,
    form_body: bytes,
    error_message: str,
) -> None:
    """Invalid long-term form input should re-render the page instead of raising."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        user = User(email="planner-invalid@example.com", password_hash="hash")  # noqa: S106
        session.add(user)
        session.commit()
        session.refresh(user)

    monkeypatch.setattr("app.routes.web.engine", test_engine)
    monkeypatch.setattr("app.services.plan_loader.engine", test_engine)
    monkeypatch.setattr("app.routes.web._today", lambda: date(2026, 5, 15))

    response = await web.long_term_plan(
        build_request(build_test_app(), method="POST", path="/long-term-plan", body=form_body),
        user,
    )

    body_text = bytes(response.body).decode()
    assert response.status_code == 200
    assert error_message in body_text

    with Session(test_engine) as session:
        phases = session.exec(select(TrainingPhase).where(TrainingPhase.user_id == user.id)).all()

    assert phases == []
