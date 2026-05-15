"""Add long-term goal planning.

Revision ID: 20260515_01
Revises: 7543c1e4540b
Create Date: 2026-05-15 00:00:00.000000

"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import sqlite

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "20260515_01"
down_revision: str | None = "7543c1e4540b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("trainingphase", sa.Column("target_date", sa.Date(), nullable=True))
    op.execute("UPDATE trainingphase SET target_date = end_date WHERE target_date IS NULL")
    with op.batch_alter_table("trainingphase") as batch_op:
        batch_op.alter_column("target_date", existing_type=sa.Date(), nullable=False)
    op.create_table(
        "longtermplanartifact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("phase_id", sa.Uuid(), nullable=False),
        sa.Column("structured_data", sqlite.JSON(), nullable=False),
        sa.Column("summary_markdown", sa.String(), nullable=False),
        sa.Column("prompt_history", sqlite.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["phase_id"], ["trainingphase.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("longtermplanartifact")
    op.drop_column("trainingphase", "target_date")
