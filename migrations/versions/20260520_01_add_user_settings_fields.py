"""Add user settings fields.

Revision ID: 20260520_01
Revises: 20260517_01
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence


# revision identifiers, used by Alembic.
revision: str = "20260520_01"
down_revision: str | None = "20260517_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_columns = {column["name"] for column in inspector.get_columns("user")}

    if "developer_mode_enabled" not in user_columns:
        op.add_column(
            "user",
            sa.Column("developer_mode_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "developer_mode_enabled")
