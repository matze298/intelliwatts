"""Remove account credentials and stored API secrets.

Revision ID: 20261028_01
Revises: 20260520_01
Create Date: 2026-10-28 00:00:00.000000

"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence


revision: str = "20261028_01"
down_revision: str | None = "20260520_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop legacy account and encrypted-key storage from the database.

    Raises:
        RuntimeError: If multiple account rows need consolidation first.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "user" in table_names and bind.execute(sa.text("SELECT COUNT(*) FROM user")).scalar_one() > 1:
        msg = "The single-profile app requires one profile row; consolidate existing accounts before upgrading."
        raise RuntimeError(msg)

    if "usersecrets" in table_names:
        op.drop_table("usersecrets")

    if "user" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("user")}
    legacy_columns = {"email", "password_hash"} & columns
    if legacy_columns:
        with op.batch_alter_table("user") as batch_op:
            for column in sorted(legacy_columns):
                batch_op.drop_column(column)


def downgrade() -> None:
    """Refuse to recreate credential storage after its data was discarded.

    Raises:
        RuntimeError: Legacy credentials can only be restored from a backup.
    """
    msg = "Legacy account and API-key data cannot be restored; restore a database backup instead."
    raise RuntimeError(msg)
