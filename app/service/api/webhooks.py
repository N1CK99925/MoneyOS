"""Razorpay webhook receiver — handles payment.captured and related events."""

from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db, write_audit_row
from ..settings import settings

router = APIRouter(tags=["webhooks"])


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook HMAC-SHA256 signature."""
    if not settings.razorpay_webhook_secret:
        # In dev mode without webhook secret, skip verification
        return True
    expected = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Receive Razorpay webhook events. Append-only audit log entry."""
    body = await request.body()

    if not _verify_webhook_signature(body, x_razorpay_signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event = json.loads(body)
    event_type = event.get("event", "unknown")
    payload = event.get("payload", {})

    # Extract key IDs from nested payload
    entity_id = None
    entity_type = None
    if "payment" in payload:
        entity_id = payload["payment"].get("id")
        entity_type = "payment"
    elif "order" in payload:
        entity_id = payload["order"].get("id")
        entity_type = "order"
    elif "refund" in payload:
        entity_id = payload["refund"].get("id")
        entity_type = "refund"

    write_audit_row(
        db,
        actor="razorpay_webhook",
        action=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        result="success",
    )

    return {"status": "ok"}
