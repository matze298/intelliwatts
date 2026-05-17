"""Add workout delivery staging for weekly plans.

Revision ID: 20260517_01
Revises: 20260515_01
Create Date: 2026-05-17 00:00:00.000000

"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import sqlite

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "20260517_01"
down_revision: str | None = "20260515_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())
    if "workoutdelivery" not in table_names:
        op.create_table(
            "workoutdelivery",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("training_plan_id", sa.Uuid(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("staged_payload", sqlite.JSON(), nullable=False),
            sa.Column("published_payload", sqlite.JSON(), nullable=False),
            sa.Column("last_error", sa.String(), nullable=True),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["training_plan_id"], ["trainingplan.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("training_plan_id"),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("workoutdelivery")
