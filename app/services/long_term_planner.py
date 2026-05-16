"""Lifecycle helpers for long-term training phases."""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from app.models.plan import TrainingPhase

if TYPE_CHECKING:
    from uuid import UUID


def replace_active_phase(
    session: Session,
    *,
    user_id: UUID,
    primary_goal: str,
    target_date: date,
    start_date: date | None = None,
) -> TrainingPhase:
    """Archive the current active phase and create a new active phase.

    Returns:
        The newly created active phase.
    """
    active_phases = session.exec(
        select(TrainingPhase).where(TrainingPhase.user_id == user_id, TrainingPhase.status == "active")
    ).all()
    for active_phase in active_phases:
        active_phase.status = "archived"
        session.add(active_phase)

    phase_start_date = start_date or datetime.now(UTC).date()
    phase = TrainingPhase(
        user_id=user_id,
        primary_goal=primary_goal,
        start_date=phase_start_date,
        end_date=target_date,
        target_date=target_date,
        status="active",
    )
    session.add(phase)
    session.flush()
    session.refresh(phase)
    return phase
