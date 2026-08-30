"""GET /audit — viewer endpoint for the demo dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..db.models import AuditLog

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def get_audit_log(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return recent audit log rows, newest first."""
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "actor": r.actor,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "payload": r.payload,
            "result": r.result,
            "error_reason": r.error_reason,
            "signed_hash": r.signed_hash,
        }
        for r in rows
    ]
