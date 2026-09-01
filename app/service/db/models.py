"""SQLAlchemy models — audit_log and checkout_session tables."""

from datetime import UTC, datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .connection import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        String(35), nullable=False, default=lambda: datetime.now(UTC).isoformat()
    )
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CheckoutSession(Base):
    __tablename__ = "checkout_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    razorpay_order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    items: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    total_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ready_for_payment")
    buyer_agent_id: Mapped[str] = mapped_column(String(100), nullable=False, default="anonymous")
    created_at: Mapped[str] = mapped_column(String(35), nullable=False)

    # Approval-flow fields (gated payments). Nullable so pre-existing rows are valid.
    approval_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    approval_deadline: Mapped[str | None] = mapped_column(String(35), nullable=True)
    approval_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
