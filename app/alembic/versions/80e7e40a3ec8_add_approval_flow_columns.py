"""add_approval_flow_columns

Adds approval-flow fields to checkout_session for gated payments:
approval_token, approval_deadline, approval_url.

Revision ID: 80e7e40a3ec8
Revises: 8532e0a43b0e
Create Date: 2026-09-01 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "80e7e40a3ec8"
down_revision: str | Sequence[str] | None = "8532e0a43b0e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add approval-flow columns to checkout_session."""
    op.add_column("checkout_session", sa.Column("approval_token", sa.String(length=64), nullable=True))
    op.add_column("checkout_session", sa.Column("approval_deadline", sa.String(length=35), nullable=True))
    op.add_column("checkout_session", sa.Column("approval_url", sa.String(length=500), nullable=True))
    op.create_index("ix_checkout_session_approval_token", "checkout_session", ["approval_token"])


def downgrade() -> None:
    """Drop approval-flow columns."""
    op.drop_index("ix_checkout_session_approval_token", table_name="checkout_session")
    op.drop_column("checkout_session", "approval_url")
    op.drop_column("checkout_session", "approval_deadline")
    op.drop_column("checkout_session", "approval_token")
