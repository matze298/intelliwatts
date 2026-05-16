"""Lifecycle helpers for long-term training phases."""

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import desc
from sqlmodel import Session, select

from app.db import engine
from app.models.plan import LongTermPlanArtifact, TrainingPhase
from app.services.planner import get_or_create_active_phase

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.sql.elements import ColumnElement

    from app.models.user import User


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


def _build_long_term_artifact_content(phase: TrainingPhase) -> tuple[dict[str, object], str, list[dict[str, str]]]:
    """Create deterministic long-term planning content for a phase.

    Returns:
        A structured summary payload, rendered markdown, and prompt history.
    """
    total_days = max((phase.target_date - phase.start_date).days, 1)
    total_weeks = max((total_days + 6) // 7, 1)
    blocks = _allocate_long_term_blocks(total_weeks)

    structured_data: dict[str, object] = {
        "goal": phase.primary_goal,
        "start_date": phase.start_date.isoformat(),
        "target_date": phase.target_date.isoformat(),
        "duration_weeks": total_weeks,
        "blocks": blocks,
    }
    block_lines = "\n".join(
        f"- {block['name']}: {block['weeks']} week(s) focused on {block['focus']}" for block in blocks
    )
    summary_markdown = (
        "# Long-term plan\n\n"
        f"Goal: {phase.primary_goal}\n\n"
        f"Target date: {phase.target_date.isoformat()}\n\n"
        "## Blocks\n\n"
        f"{block_lines}\n"
    )
    prompt_history = [
        {"role": "system", "content": "Generate a deterministic long-term training summary."},
        {
            "role": "user",
            "content": f"Create a long-term outline for goal '{phase.primary_goal}' ending on {phase.target_date.isoformat()}.",
        },
    ]
    return structured_data, summary_markdown, prompt_history


def generate_long_term_plan_artifact(session: Session, *, phase: TrainingPhase) -> LongTermPlanArtifact:
    """Create and persist a new long-term artifact for a training phase.

    Returns:
        The persisted long-term artifact.
    """
    structured_data, summary_markdown, prompt_history = _build_long_term_artifact_content(phase)
    artifact = LongTermPlanArtifact(
        phase_id=phase.id,
        structured_data=structured_data,
        summary_markdown=summary_markdown,
        prompt_history=prompt_history,
    )
    session.add(artifact)
    session.flush()
    session.refresh(artifact)
    return artifact


def get_current_long_term_plan_artifact(session: Session, *, phase_id: UUID) -> LongTermPlanArtifact | None:
    """Return the most recent long-term artifact for a phase."""
    statement = (
        select(LongTermPlanArtifact)
        .where(LongTermPlanArtifact.phase_id == phase_id)
        .order_by(desc(cast("ColumnElement[datetime]", LongTermPlanArtifact.created_at)))
        .order_by(desc(cast("ColumnElement[datetime]", LongTermPlanArtifact.updated_at)))
    )
    return session.exec(statement).first()


def generate_long_term_plan_for_user(user: User) -> dict[str, str]:
    """Generate and persist a long-term artifact for the user's active phase.

    Returns:
        A compact response describing the generated artifact.

    """
    with Session(engine) as session:
        phase = get_or_create_active_phase(session, user.id)
        artifact = generate_long_term_plan_artifact(session, phase=phase)
        session.commit()
        session.refresh(artifact)

    return {"artifact_id": str(artifact.id), "summary": artifact.summary_markdown}


def _allocate_long_term_blocks(total_weeks: int) -> list[dict[str, object]]:
    """Allocate macro blocks without exceeding the phase duration.

    Returns:
        A list of block dictionaries whose week totals match ``total_weeks``.
    """
    two_week_phase = 2
    if total_weeks <= 1:
        return [{"name": "Peak", "focus": "Freshness and specificity", "weeks": 1}]
    if total_weeks == two_week_phase:
        return [
            {"name": "Build", "focus": "Goal-specific workload", "weeks": 1},
            {"name": "Peak", "focus": "Freshness and specificity", "weeks": 1},
        ]

    base_weeks = max(total_weeks // 3, 1)
    build_weeks = max(total_weeks // 3, 1)
    peak_weeks = total_weeks - base_weeks - build_weeks
    return [
        {"name": "Base", "focus": "Aerobic durability", "weeks": base_weeks},
        {"name": "Build", "focus": "Goal-specific workload", "weeks": build_weeks},
        {"name": "Peak", "focus": "Freshness and specificity", "weeks": peak_weeks},
    ]
