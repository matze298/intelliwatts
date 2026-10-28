"""Create the initial single-profile schema.

Revision ID: 20261028_02
Revises:
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence


revision: str = "20261028_02"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the application tables."""
    op.create_table(
        "user",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("weekly_hours", sa.Float(), nullable=False),
        sa.Column("weekly_sessions", sa.Integer(), nullable=False),
        sa.Column("developer_mode_enabled", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "trainingphase",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("primary_goal", sa.String(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
    )
    op.create_table(
        "trainingplan",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("phase_id", sa.Uuid(), sa.ForeignKey("trainingphase.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("raw_content", sa.String(), nullable=False),
        sa.Column("workout_data", sa.JSON(), nullable=True),
        sa.Column("prompt_history", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "longtermplanartifact",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("phase_id", sa.Uuid(), sa.ForeignKey("trainingphase.id"), nullable=False),
        sa.Column("structured_data", sa.JSON(), nullable=True),
        sa.Column("summary_markdown", sa.String(), nullable=False),
        sa.Column("prompt_history", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "workoutdelivery",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("training_plan_id", sa.Uuid(), sa.ForeignKey("trainingplan.id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "PUBLISHING", "PUBLISHED", "FAILED", name="workoutdeliverystatus"),
            nullable=False,
        ),
        sa.Column("staged_payload", sa.JSON(), nullable=True),
        sa.Column("published_payload", sa.JSON(), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workoutdelivery_training_plan_id", "workoutdelivery", ["training_plan_id"], unique=True)


def downgrade() -> None:
    """Remove the application tables."""
    op.drop_index("ix_workoutdelivery_training_plan_id", table_name="workoutdelivery")
    op.drop_table("workoutdelivery")
    op.drop_table("longtermplanartifact")
    op.drop_table("trainingplan")
    op.drop_table("trainingphase")
    op.drop_table("user")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="workoutdeliverystatus").drop(op.get_bind(), checkfirst=True)
