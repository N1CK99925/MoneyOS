"""add_system_settings_table

Adds system_settings table for runtime-configurable settings
(e.g., spend policy max per transaction).

Revision ID: a1b2c3d4e5f6
Revises: 80e7e40a3ec8
Create Date: 2026-09-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "80e7e40a3ec8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(length=100), unique=True, nullable=False, index=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("updated_at", sa.String(length=35), nullable=False),
    )

    # Seed the default spend policy value
    op.execute(
        "INSERT INTO system_settings (key, value, description, updated_at) "
        "VALUES ('spend_policy_max_per_transaction_paise', '60000', "
        "'Max per-transaction spend in paise. 0 disables the check.', "
        "'2026-09-02T00:00:00+00:00')"
    )


def downgrade() -> None:
    op.drop_table("system_settings")
