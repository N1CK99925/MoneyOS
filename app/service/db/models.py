"""SQLAlchemy models — audit_log table definition."""

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
