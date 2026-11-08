"""Persist last used planning model and available cycling days.

Revision ID: 20261108_01
Revises: 20261103_01
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "20261108_01"
down_revision: str | None = "20261103_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_WEEKDAYS = '["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]'


def upgrade() -> None:
    """Backfill existing profiles with all cycling days available."""
    op.add_column("user", sa.Column("preferred_language_model", sa.Text(), nullable=True))
    op.add_column(
        "user",
        sa.Column("available_cycling_days", sa.JSON(), nullable=False, server_default=sa.text(f"'{DEFAULT_WEEKDAYS}'")),
    )
    op.alter_column("user", "available_cycling_days", server_default=None)


def downgrade() -> None:
    """Remove persisted planner preferences."""
    op.drop_column("user", "available_cycling_days")
    op.drop_column("user", "preferred_language_model")
