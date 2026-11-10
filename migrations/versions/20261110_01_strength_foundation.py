"""Create the minimal native strength tables without importing athlete data.

Revision ID: 20261110_01
Revises: 20261108_01
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "20261110_01"
down_revision: str | None = "20261108_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add empty, athlete-owned strength tables; preserve existing cycling tables."""
    op.create_table(
        "exercise",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("primary_metric", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("user_id", "source_id", name="uq_exercise_user_source"),
    )
    op.create_index("ix_exercise_user_id", "exercise", ["user_id"])

    op.create_table(
        "strengthtemplate",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("variant", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "name", "variant", "version", name="uq_strengthtemplate_version"),
    )
    op.create_index("ix_strengthtemplate_user_id", "strengthtemplate", ["user_id"])

    op.create_table(
        "strengthsession",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("template_id", sa.Uuid(), sa.ForeignKey("strengthtemplate.id"), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("workout_type", sa.String(), nullable=False),
        sa.Column("variant", sa.String(), nullable=True),
        sa.Column("template_version", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("session_rpe", sa.Float(), nullable=True),
        sa.Column("readiness", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_data", sa.JSON(), nullable=True),
        sa.UniqueConstraint("user_id", "source_id", name="uq_strengthsession_user_source"),
    )
    op.create_index("ix_strengthsession_user_id", "strengthsession", ["user_id"])

    op.create_table(
        "strengthset",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("strengthsession.id"), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), sa.ForeignKey("exercise.id"), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(), nullable=True),
        sa.Column("reps", sa.Float(), nullable=True),
        sa.Column("load_kg", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("distance_m", sa.Float(), nullable=True),
        sa.Column("rir", sa.Float(), nullable=True),
        sa.Column("band_id", sa.String(), nullable=True),
        sa.Column("band_setup", sa.String(), nullable=True),
        sa.Column("variation_setup", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_data", sa.JSON(), nullable=True),
        sa.UniqueConstraint("source_id", name="uq_strengthset_source"),
    )
    op.create_index("ix_strengthset_session_id", "strengthset", ["session_id"])


def downgrade() -> None:
    """Remove only the new strength tables, leaving legacy cycling data intact."""
    op.drop_index("ix_strengthset_session_id", table_name="strengthset")
    op.drop_table("strengthset")
    op.drop_index("ix_strengthsession_user_id", table_name="strengthsession")
    op.drop_table("strengthsession")
    op.drop_index("ix_strengthtemplate_user_id", table_name="strengthtemplate")
    op.drop_table("strengthtemplate")
    op.drop_index("ix_exercise_user_id", table_name="exercise")
    op.drop_table("exercise")
