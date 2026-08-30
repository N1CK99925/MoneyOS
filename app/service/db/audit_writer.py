"""Audit writer — single shared helper that every checkout event calls.

Append-only: no UPDATE, no DELETE. Every row gets an HMAC-SHA256 signed hash
for tamper evidence.
"""

import hashlib
import hmac
import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from ..settings import settings
from .models import AuditLog


def _compute_hash(row_data: dict) -> str:
    """HMAC-SHA256 of the row payload (excluding signed_hash itself)."""
    canonical = json.dumps(row_data, sort_keys=True, default=str)
    return hmac.new(
        settings.audit_hmac_secret.encode(), canonical.encode(), hashlib.sha256
    ).hexdigest()


def write_audit_row(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    payload: dict | None = None,
    result: str = "success",
    error_reason: str | None = None,
) -> AuditLog:
    """Write one row to the audit log. Returns the created row.

    This is the ONLY way to insert into audit_log. No other code path
    should create rows — that's how you guarantee the append-only property.
    """
    timestamp = datetime.now(UTC).isoformat()
    payload_json = json.dumps(payload, default=str) if payload is not None else None

    row_data = {
        "timestamp": timestamp,
        "actor": actor,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "payload": payload_json,
        "result": result,
        "error_reason": error_reason,
    }
    signed_hash = _compute_hash(row_data)

    row = AuditLog(
        timestamp=timestamp,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload_json,
        result=result,
        error_reason=error_reason,
        signed_hash=signed_hash,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
