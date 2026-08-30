"""Razorpay webhook receiver — handles payment.captured, payment.failed, and related events."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db, write_audit_row
from ..db.models import CheckoutSession as CheckoutSessionRow
from ..settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook HMAC-SHA256 signature."""
    if not settings.razorpay_webhook_secret:
        # In dev mode without webhook secret, skip verification
        return True
    expected = hmac.new(settings.razorpay_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _update_session_status(db: Session, order_id: str, status: str) -> None:
    """Update checkout session status by Razorpay order ID."""
    row = db.query(CheckoutSessionRow).filter_by(razorpay_order_id=order_id).first()
    if row:
        row.status = status
        db.commit()
    else:
        logger.warning("No checkout session found for order %s", order_id)


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    db: Session = Depends(get_db),
):
    """Receive Razorpay webhook events. Log to audit and update session status."""
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

    # Determine result and update session on failures
    result = "success"
    error_reason = None

    # Razorpay nests entity data under payload.<entity>.entity
    payment_entity = payload.get("payment", {}).get("entity", {}) or {}
    order_entity = payload.get("order", {}).get("entity", {}) or {}
    order_id = payment_entity.get("order_id") or order_entity.get("id")

    if event_type == "payment.failed":
        result = "failure"
        error_reason = payment_entity.get("error_description") or "Payment failed"
        if order_id:
            _update_session_status(db, order_id, "failed")
    elif event_type == "payment.captured":
        result = "success"
        if order_id:
            _update_session_status(db, order_id, "completed")
    elif event_type == "order.paid":
        result = "success"
        if order_id:
            _update_session_status(db, order_id, "completed")
    elif event_type in ("order.failed", "order.cancelled", "order.expired"):
        result = "failure"
        error_reason = f"Order event: {event_type}"
        if order_id:
            _update_session_status(db, order_id, "failed")

    write_audit_row(
        db,
        actor="razorpay_webhook",
        action=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        result=result,
        error_reason=error_reason,
    )

    return {"status": "ok"}
