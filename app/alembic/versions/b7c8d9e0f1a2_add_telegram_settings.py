"""add_telegram_settings

Adds runtime system_settings rows for Telegram bot configuration so the bot
token and chat IDs can be configured from the Settings UI (DB-backed, matching
the spend-policy pattern) instead of only via env vars.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-09-02

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TELEGRAM_SEEDS = [
    (
        "telegram_bot_token",
        "",
        "Telegram bot token from @BotFather (e.g. 123456:ABC-DEF...). Leave blank to disable.",
    ),
    (
        "telegram_merchant_chat_id",
        "",
        "Merchant Telegram chat ID where Approve/Deny buttons are delivered.",
    ),
    (
        "telegram_customer_chat_id",
        "",
        "Customer Telegram chat ID for payment links. Blank defaults to the merchant chat ID.",
    ),
]


def upgrade() -> None:
    updated_at = "2026-09-02T00:00:00+00:00"
    for key, value, description in _TELEGRAM_SEEDS:
        op.execute(
            sa.text(
                "INSERT INTO system_settings (key, value, description, updated_at) "
                "VALUES (:key, :value, :description, :updated_at) "
                "ON CONFLICT (key) DO NOTHING"
            ).bindparams(
                key=key,
                value=value,
                description=description,
                updated_at=updated_at,
            )
        )


def downgrade() -> None:
    for key, _, _ in _TELEGRAM_SEEDS:
        op.execute(sa.text("DELETE FROM system_settings WHERE key = :key").bindparams(key=key))
