"""Persist prompt overrides and login failure timestamps.

Revision ID: 20261103_01
Revises: 20261028_02
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence


revision: str = "20261103_01"
down_revision: str | None = "20261028_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add persistent prompt overrides and shared login throttling state."""
    op.add_column("user", sa.Column("system_prompt_override", sa.Text(), nullable=True))
    op.add_column("user", sa.Column("user_prompt_override", sa.Text(), nullable=True))
    op.add_column(
        "user",
        sa.Column("login_failure_timestamps", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.alter_column("user", "login_failure_timestamps", server_default=None)


def downgrade() -> None:
    """Remove prompt overrides and shared login throttling state."""
    op.drop_column("user", "login_failure_timestamps")
    op.drop_column("user", "user_prompt_override")
    op.drop_column("user", "system_prompt_override")
